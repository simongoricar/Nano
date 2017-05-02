# coding=utf-8
import configparser
# redis is a conditional import
import time
import logging
import copy
import os
import importlib
# yaml is now a conditional import
# json is a conditional import too
from discord import Member, User
from .utils import threaded, Singleton, get_decision, decode, decode_auto

__author__ = "DefaltSimon"

# Server handler for Nano

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

par = configparser.ConfigParser()
par.read("settings.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

MAX_INPUT_LENGTH = 800

server_defaults = {
    "name": "",
    "owner": "",
    "filterwords": False,
    "filterspam": False,
    "filterinvite": False,
    "sleeping": False,
    "welcomemsg": "Welcome to :server, :user!",
    "kickmsg": "**:user** has been kicked.",
    "banmsg": "**:user** has been banned.",
    "leavemsg": "**:user** has left the server :cry:",
    "blacklisted": [],
    "muted": [],
    "customcmds": {},
    "admins": [],
    "logchannel": None,
    "prefix": str(parser.get("Servers", "defaultprefix")),
    "selfrole": None,
}

# Utility for input validation


def validate_input(fn):
    def wrapper(self, *args, **kwargs):
        for arg in args:
            if len(str(arg)) > MAX_INPUT_LENGTH:
                return False

        for k, v in kwargs.items():
            if (len(str(k)) > MAX_INPUT_LENGTH) or (len(str(v)) > MAX_INPUT_LENGTH):
                return False

        # If no filters need to be applied, do everything normally
        return fn(self, *args, **kwargs)

    return wrapper

# ServerHandler is a singleton, --> only one instance
# imported from utils


class ServerHandler:
    def __init__(self):
        pass

    @staticmethod
    def get_redis_credentials():
        setup_type = 1 if par.get("Redis", "setup") == "openshift" else 2

        if setup_type == 1:
            redis_ip = os.environ["OPENSHIFT_REDIS_HOST"]
            redis_port = os.environ["OPENSHIFT_REDIS_PORT"]
            redis_pass = os.environ["REDIS_PASSWORD"]

        else:
            redis_ip = par.get("Redis", "ip")
            redis_port = par.get("Redis", "port")
            redis_pass = par.get("Redis", "password")

            # Fallback to defaults
            if not redis_ip:
                redis_ip = "localhost"
            if not redis_port:
                redis_port = 6379
            if not redis_pass:
                redis_pass = None

        return redis_ip, redis_port, redis_pass

    @classmethod
    def get_handler(cls, legacy=False):
        # Factory method
        if legacy:
            return LegacyServerHandler()
        else:
            redis_ip, redis_port, redis_pass = cls.get_redis_credentials()
            return RedisServerHandler(redis_ip, redis_port, redis_pass)

    # Permission checker
    def has_role(self, user, server, role_name):
        if not isinstance(user, Member):
            return False

        for role in user.roles:
            if role.name == role_name:
                return True

        return False

    def can_use_restricted_commands(self, user, server):
        bo = self.is_bot_owner(user.id)
        so = self.is_server_owner(user.id, server)
        ia = self.is_admin(user, server)

        return bo or so or ia

    @staticmethod
    def is_bot_owner(uid):
        return str(uid) == str(par.get("Settings", "ownerid"))

    @staticmethod
    def is_server_owner(uid, server):
        return str(uid) == str(server.owner.id)

    def is_admin(self, user, server):
        return self.has_role(user, server, "Nano Admin")

    def is_mod(self, user, server):
        return self.has_role(user, server, "Nano Mod") or self.is_bot_owner(user.id) or self.is_server_owner(user.id, server)


# Everything regarding RedisServerHandler below
# Careful when converting data, this was changed (see converter.py for implementation)
WORDFILTER_SETTING = "wordfilter"
SPAMFILTER_SETTING = "spamfilter"
INVITEFILTER_SETTING = "invitefilter"

mod_settings_map = {
    "word filter": WORDFILTER_SETTING,
    "filter words": WORDFILTER_SETTING,
    "wordfilter": WORDFILTER_SETTING,

    "spam filter": SPAMFILTER_SETTING,
    "filter spam": SPAMFILTER_SETTING,
    "spamfilter": SPAMFILTER_SETTING,

    "invite filter": INVITEFILTER_SETTING,
    "filterinvite": INVITEFILTER_SETTING,
    "filterinvites": INVITEFILTER_SETTING,
}

# IMPORTANT
# The format for saving server data is => server:id_here
# For commands => commands:id_here
# For mutes => mutes:id_here
# For blacklist => blacklist:id_here


class RedisServerHandler(ServerHandler, metaclass=Singleton):
    __slots__ = ("_redis", "redis")

    def __init__(self, redis_ip, redis_port, redis_password):
        super().__init__()

        self._redis = importlib.import_module("redis")
        self.redis = self._redis.StrictRedis(host=redis_ip, port=redis_port, password=redis_password)

        try:
            self.redis.ping()
        except self._redis.ConnectionError:
            log.critical("Could not connect to Redis db!")
            return

        log.info("Connected to Redis database")

    def bg_save(self):
        return bool(self.redis.bgsave() == b"OK")

    def server_setup(self, server, **_):
        # These are server defaults
        s_data = dict(server_defaults).copy()
        s_data["owner"] = server.owner.id
        s_data["name"] = server.name

        sid = "server:{}".format(server.id)
        # cid = "commands:{}".format(server.id)
        # mid = "mutes:{}".format(server.id)
        # bid = "blacklist:{}".format(server.id)

        self.redis.hmset(sid, s_data)
        # commands:id, mutes:id and blacklist:id are created automatically when needed

        log.info("New server: {}".format(server.name))

    def server_exists(self, server_id):
        return bool(decode(self.redis.exists("server:{}".format(server_id))))

    def check_serv(self, server):
        # shortcut for checking sever existence
        if not self.server_exists(server.id):
            self.server_setup(server)

    def get_server_data(self, server):
        # Special: HGETALL returns a dict with binary keys and values!
        base = decode(self.redis.hgetall("server:{}".format(server.id)))
        cmd_list = self.get_custom_commands(server)
        bl = self.get_blacklist(server)
        mutes = self.get_mute_list(server)

        data = decode(base)
        data["commands"] = cmd_list
        data["blacklist"] = bl
        data["mutes"] = mutes

        return data

    def get_var(self, server_id, key):
        # If value is in json, it will be a json-encoded string and not parsed
        return decode(self.redis.hget("server:{}".format(server_id), key))

    @validate_input
    def update_var(self, server_id, key, value):
        self.redis.hset("server:{}".format(server_id), key, value)

    @validate_input
    def update_moderation_settings(self, server, key, value):
        if not mod_settings_map.get(key):
            return False

        return decode(self.redis.hset("server:{}".format(server.id), mod_settings_map.get(key), value))

    def check_server_vars(self, server):
        serv = "server:{}".format(server.id)

        if decode(self.redis.hget(serv, "owner")) != str(server.owner.id):
            self.redis.hset(serv, "owner", server.owner.id)

        if decode(self.redis.hget(serv, "name")) != str(server.name):
            self.redis.hset(serv, "name", server.name)

    def delete_server_by_list(self, current_servers):
        servers = ["server:{}".format(name) for name in current_servers]

        server_list = [decode_auto(a) for a in self.redis.scan(0, match="server:*")[1]]

        for server in servers:
            try:
                server_list.remove(server)
            except ValueError:
                pass

        if server_list:
            for rem_serv in server_list:
                self.delete_server(rem_serv)

            log.info("Removed {} old servers.".format(len(server_list)))

    def delete_server(self, server_id):
        self.redis.delete("commands:{}".format(server_id))
        self.redis.delete("blacklist:{}".format(server_id))
        self.redis.delete("mutes:{}".format(server_id))

        return self.redis.delete("server:{}".format(server_id))

    @validate_input
    def set_command(self, server, trigger, response):
        serv = "commands:{}".format(server.id)

        if len(trigger) > 80:
            return False

        self.redis.hset(serv, trigger, response)
        return True

    def remove_command(self, server, trigger):
        serv = "commands:{}".format(server.id)

        if decode(self.redis.hget(serv, trigger)):
            self.redis.hdel(serv, trigger)
            return True

        else:
            return False

    def get_custom_commands(self, server):
        cmds = decode(self.redis.hgetall("commands:{}".format(server.id)))
        return cmds

    @validate_input
    def add_channel_blacklist(self, server, channel_id):
        serv = "blacklist:{}".format(server.id)
        return bool(self.redis.sadd(serv, channel_id))

    @validate_input
    def remove_channel_blacklist(self, server, channel_id):
        serv = "blacklist:{}".format(server.id)
        return bool(self.redis.srem(serv, channel_id))

    def is_blacklisted(self, server, channel_id):
        serv = "blacklist:{}".format(server.id)
        return bool(self.redis.sismember(serv, channel_id))

    def get_blacklist(self, server):
        serv = "blacklist:{}".format(server.id)
        return list(decode(self.redis.smembers(serv)))

    def get_prefix(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), "prefix"))

    @validate_input
    def change_prefix(self, server, prefix):
        self.check_serv(server)

        self.redis.hset("server:{}".format(server.id), "prefix", prefix)

    def has_spam_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), SPAMFILTER_SETTING)) is True

    def has_word_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), WORDFILTER_SETTING)) is True

    def has_invite_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), INVITEFILTER_SETTING)) is True

    def get_log_channel(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), "logchannel"))

    def has_logging(self, server):
        # Deprecated, but still here
        return bool(self.get_log_channel(server.id))

    def is_sleeping(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), "sleeping"))

    @validate_input
    def set_sleeping(self, server, var):
        self.redis.hset("server:{}".format(server.id), "sleeping", bool(var))

    @validate_input
    def mute(self, server, user_id):
        serv = "mutes:{}".format(server.id)
        return bool(self.redis.sadd(serv, user_id))

    @validate_input
    def unmute(self, member):
        serv = "mutes:{}".format(member.server.id)
        return bool(self.redis.srem(serv, member.id))

    def is_muted(self, server, user_id):
        serv = "mutes:{}".format(server.id, user_id)
        return bool(self.redis.sismember(serv, user_id))

    def get_mute_list(self, server):
        serv = "mutes:{}".format(server.id)
        return list(decode(self.redis.smembers(serv)))

    @validate_input
    def remove_server(self, server_id):
        # Not used
        s = bool(self.redis.delete("server:{}".format(server_id)))
        c = bool(self.redis.delete("commands:{}".format(server_id)))
        m = bool(self.redis.delete("mutes:{}".format(server_id)))
        b = bool(self.redis.delete("blacklist:{}".format(server_id)))

        return s and c and m and b

    def get_selfrole(self, server_id):
        return decode(self.redis.hget("server:{}".format(server_id), "selfrole"))

    def set_selfrole(self, server_id, role_name):
        role = str(role_name)
        return self.redis.hset("server:{}".format(server_id), "selfrole", role)

    # Special debug methods
    def db_info(self, section=None):
        return decode_auto(self.redis.info(section=section))

    def db_size(self):
        return int(self.redis.dbsize())

    # Plugin storage system
    def get_plugin_data_manager(self, namespace, *args, **kwargs):
        return RedisPluginDataManager(self._redis, namespace, *args, **kwargs)


class RedisPluginDataManager:
    def __init__(self, _redis, namespace, *_, **__):
        self.namespace = str(namespace)

        redis_ip, redis_port, redis_password = RedisServerHandler.get_redis_credentials()
        self.redis = _redis.StrictRedis(host=redis_ip, port=redis_port, password=redis_password)

        log.info("Plugin registered for redis data:{}".format(self.namespace))

    def _build_hash(self, name):
        # Returns a hash name formatted with the namespace
        return "{}:{}".format(self.namespace, name)

    def set(self, key, val):
        return decode(self.redis.set(self._build_hash(key), val))

    def get(self, key):
        return decode(self.redis.get(self._build_hash(key)))

    def hget(self, name, field):
        return decode(self.redis.hget(self._build_hash(name), field))

    def hgetall(self, name):
        return decode(self.redis.hgetall(self._build_hash(name)))

    def hdel(self, name, field):
        return decode(self.redis.hdel(self._build_hash(name), field))

    def hmset(self, name, payload):
        return decode(self.redis.hmset(self._build_hash(name), payload))

    def hset(self, name, field, value):
        return decode(self.redis.hset(self._build_hash(name), field, value))

    def exists(self, name):
        return bool(decode(self.redis.exists(self._build_hash(name))))

    def delete(self, name):
        return bool(decode(self.redis.delete(self._build_hash(name))))

    def scan_iter(self, match, use_namespace=True):
        match = self._build_hash(match) if use_namespace else match
        return [a for a in self.redis.scan_iter(match)]

    def lpush(self, key, value):
        return decode(self.redis.lpush(self._build_hash(key), value))

    def lrange(self, key, from_key=0, to_key=-1):
        return decode(self.redis.lrange(self._build_hash(key), from_key, to_key))

    def lrem(self, key, value, count=1):
        return decode(self.redis.lrem(key, count, value))

    def lpop(self, key, index):
        return decode(self.redis.lpop(key, index))

# DEPRECATED, only for self-hosting the bot


class LegacyServerHandler(ServerHandler, metaclass=Singleton):
    def __init__(self):
        super().__init__()

        self.file = "data/servers.yml"
        self.yaml = importlib.import_module("yaml")

        # Loads the file into memory
        with open(self.file, "r") as file:
            self.cached_file = self.yaml.load(file)

        # Used for thread-safe file writing
        self.thread_lock = False

        log.info("Enabled")

    # Used to queue the file writes
    def lock(self):
        self.thread_lock = True

    def wait_until_release(self):
        while self.thread_lock is True:
            time.sleep(0.05)

    def release_lock(self):
        self.thread_lock = False

    # Here begins the class with all its real methods
    def server_setup(self, server, wait=False):
        data = self.cached_file

        # These are server defaults
        s_data = dict(server_defaults)

        s_data["owner"] = server.owner.id
        s_data["name"] = server.name

        self.cached_file[server.id] = s_data

        log.info("New server: {}".format(server.name))

        if wait:
            self.queue_write(data)
        else:
            self._queue_write(data)

    def server_exists(self, server):
        return self.cached_file.get(server.id)

    @threaded
    def queue_write(self, data):
        self._queue_write(data)

    def _queue_write(self, data):
        self.cached_file = copy.deepcopy(data)
        self.wait_until_release()

        self.lock()
        log.info("Write queued")

        with open(self.file, "w") as file:
            file.write(self.yaml.dumps(data, default_flow_style=False))  # Makes it readable
        self.release_lock()

    def reload(self):
        self.wait_until_release()

        self.lock()
        with open(self.file, "r") as file:
            self.cached_file = self.yaml.load(file)
        self.release_lock()

        log.info("Reloaded servers.yml")

    def _queue_modification(self, thing, *args, **kwargs):
        # Not used anymore, kept as "private"
        self.wait_until_release()
        self.lock()

        thing(*args, **kwargs)

        self.release_lock()

    def get_data(self):
        return self.cached_file

    def get_server_data(self, server_id):
        return self.cached_file.get(server_id)

    @validate_input
    def update_moderation_settings(self, server, key, value):
        data = self.cached_file

        # Check server existence
        if server.id not in data:
            self.server_setup(server)

        # Detects the type of the setting
        if get_decision(key, "word filter", "filter words", "wordfilter"):
            data[server.id]["filterwords"] = value
            self.queue_write(data)

        elif get_decision(key, "spam filter", "spamfilter", "filter spam"):
            data[server.id]["filterspam"] = value
            self.queue_write(data)

        elif get_decision(key, "filterinvite", "filterinvites", "invite removal", "invite filter", "invitefilter"):
            data[server.id]["filterinvite"] = value
            self.queue_write(data)

        return bool(value)

    @validate_input
    def update_var(self, sid, key, value):
        data = self.cached_file

        data[sid][key] = value
        self.queue_write(data)

    def check_server_vars(self, server):
        data = self.cached_file
        modified = False

        # Checks for settings that are not what they should be
        srv = data.get(server.id)

        if str(srv.get("owner")) != str(server.owner.id):
            data[server.id]["owner"] = server.owner.id

        if str(srv.get("name")) != str(server.name):
            data[server.id]["name"] = server.name

        if modified:
            self.queue_write(data)

    def delete_old_servers(self, current_servers):
        data = self.cached_file
        modified = False

        # Iterate through servers and remove them if they are not in the current_servers list
        for server in list(data.keys()):
            if server not in current_servers:
                data.pop(server)
                modified = True

        if modified:
            self.queue_write(data)

    @validate_input
    def set_command(self, server, trigger, response):
        try:
            data = self.cached_file

            data[server.id]["customcmds"][trigger] = response

            self.queue_write(data)

        except UnicodeEncodeError:
            pass

    def remove_command(self, server, trigger):
        data = self.cached_file

        ok = False

        try:
            del data[server.id]["customcmds"][trigger]

            ok = True
        except KeyError:
            # Discord ignores spaces, so >cmd remove something  will not work, here we check for these commands
            try:
                cmd = [a for a in data[server.id]["customcmds"] if str(a).startswith(trigger)][0]
                del data[server.id]["customcmds"][cmd]

                ok = True
            except IndexError:
                pass

        self.queue_write(data)
        return ok

    @validate_input
    def add_channel_blacklist(self, server, channel_id):
        data = self.cached_file

        data[server.id]["blacklisted"].append(str(channel_id))
        self.queue_write(data)

    def remove_channel_blacklist(self, server, channel_id):
        data = self.cached_file

        try:
            data[server.id]["blacklisted"].remove(str(channel_id))
            self.queue_write(data)

            return True
        except ValueError:
            return False

    def is_blacklisted(self, server, channel):
        if channel.is_private:
            return False

        try:
            data = self.cached_file
            return channel.id in data[server.id]["blacklisted"]

        except KeyError:
            return False

    @validate_input
    def add_admin(self, server, user):
        data = self.cached_file

        # Ignore if user is already in admins
        if user.id in data[server.id]["admins"]:
            return

        data[server.id]["admins"].append(str(user.id))

        self.queue_write(data)

    def remove_admin(self, server, user):
        data = self.cached_file

        if type(user) is int:
            user_id = int(user)
        elif isinstance(user, (Member, User)):
            user_id = int(user.id)
        else:
            return

        try:
            data[server.id]["admins"].remove(user_id)
        except ValueError:
            return  # Ignore if the admin did not exist

        self.queue_write(data)

    def get_prefix(self, server):
        data = self.cached_file

        return data.get(server.id).get("prefix")

    @validate_input
    def change_prefix(self, server, prefix):
        data = self.cached_file

        # Check server existence
        if server.id not in data:
            self.server_setup(server)

        data[server.id]["prefix"] = prefix

        self.queue_write(data)

    def has_spam_filter(self, server):
        data = self.cached_file

        return bool(data[server.id]["filterspam"])

    def has_word_filter(self, server):
        data = self.cached_file

        return bool(data[server.id]["filterwords"])

    def has_invite_filter(self, server):
        data = self.cached_file

        return bool(data[server.id]["filterinvite"])

    def get_custom_commands(self, server):
        data = self.cached_file

        return data[server.id]["customcmds"]

    def get_admins(self, server):
        data = self.cached_file

        return data[server.id]["admins"]

    def get_log_channel(self, server):
        data = self.cached_file

        return data[server.id]["logchannel"]

    def is_sleeping(self, server):
        data = self.cached_file

        return bool(data[server.id]["sleeping"])

    @validate_input
    def set_sleeping(self, server, var):
        data = self.cached_file

        data[server.id]["sleeping"] = var
        self.queue_write(data)

    def has_logging(self, server):
        if server is None:
            return True
        data = self.cached_file

        return bool(data[server.id]["logchannel"])

    @validate_input
    def mute(self, user):
        assert isinstance(user, Member)

        data = self.cached_file

        if user.id not in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].append(user.id)
            self.queue_write(data)

    def is_muted(self, user, server):
        # user if actually supposed to be a an instance of discord.Member (not User, because it doesn't have server property)
        data = self.cached_file

        return bool(user.id in data[server.id]["muted"])

    def unmute(self, user):
        assert isinstance(user, Member)

        data = self.cached_file

        if user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"] = [u for u in data[user.server.id]["muted"] if user.id not in u]
            self.queue_write(data)

    def get_mute_list(self, server):
        data = self.cached_file

        return data[server.id]["muted"]

    @validate_input
    def update_name(self, sid, name):
        data = self.cached_file

        data[sid]["name"] = name
        self.queue_write(data)

    @validate_input
    def update_owner(self, sid, name):
        data = self.cached_file

        data[sid]["owner"] = name
        self.queue_write(data)

    def get_var(self, sid, var):
        data = self.cached_file

        return data.get(sid).get(var)

    def remove_server(self, server):
        data = self.cached_file

        data.pop(server.id)

        log.info("Removed {} from servers.yml".format(server.name))

    # CHECKS
    def has_role(self, user, server, role_name):
        try:
            is_admin = bool(user.id in self.cached_file.get(server.id).get("admins"))
        except TypeError:
            is_admin = False

        if not is_admin:
            for role in user.roles:
                if role.name == role_name:
                    return True

        return is_admin

    # MAIN check
    def can_use_restricted_commands(self, user, server):
        bo = self.is_bot_owner(user.id)
        so = self.is_server_owner(user.id, server)
        ia = self.is_admin(user, server)

        return bo or so or ia

    @staticmethod
    def is_bot_owner(uid):
        return str(uid) == str(par.get("Settings", "ownerid"))

    @staticmethod
    def is_server_owner(uid, server):
        return str(uid) == str(server.owner.id)

    def is_admin(self, user, server):
        return self.has_role(user, server, "Nano Admin")

    def is_mod(self, user, server):
        return self.has_role(user, server, "Nano Mod") or self.is_bot_owner(user.id) or self.is_server_owner(user.id, server)
