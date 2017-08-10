# coding=utf-8
import configparser
import redis
import logging
import os
from discord import Member, Guild
from .utils import Singleton, decode, bin2bool

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
    "logchannel": None,
    "prefix": str(parser.get("Servers", "defaultprefix")),
    "dchan": None,
    "lang": "en",
}

# Decorator utility for input validation


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

# RedisServerHandler is a singleton, --> only one instance
# Singleton imported from utils


class ServerHandler:
    @staticmethod
    def get_redis_credentials() -> tuple:
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
    def get_handler(cls, legacy: bool = False) -> "RedisServerHandler":
        # Factory method
        if legacy:
            raise NotImplementedError
        else:
            redis_ip, redis_port, redis_pass = cls.get_redis_credentials()
            return RedisServerHandler(redis_ip, redis_port, redis_pass)

    # Permission checker
    @staticmethod
    def has_role(member: Member, role_name: str):
        if not isinstance(member, Member):
            raise TypeError("expected Member, got {}".format(type(member).__name__))

        for role in member.roles:
            if role.name == role_name:
                return True

        return False

    def can_use_admin_commands(self, member: Member, server: Guild):
        bo = self.is_bot_owner(member.id)
        so = self.is_server_owner(member.id, server)
        ia = self.is_admin(member)

        return bo or so or ia

    @staticmethod
    def is_bot_owner(uid: int):
        return uid == int(par.get("Settings", "ownerid"))

    @staticmethod
    def is_server_owner(user_id: int, server: Guild):
        return user_id == server.owner.id

    def is_admin(self, member: Member):
        return self.has_role(member, "Nano Admin")

    def is_mod(self, member: Member, server: Guild):
        # Changed in 3.7
        # Having Nano Admin allows access to Nano Mod commands as well
        bo = self.is_bot_owner(member.id)
        so = self.is_server_owner(member.id, server)
        im = self.has_role(member, "Nano Mod")
        ia = self.has_role(member, "Nano Admin")

        return bo or so or ia or im


# Everything regarding RedisServerHandler below
# Careful when converting data, this was changed (see converter.py for implementation)
WORDFILTER_SETTING = "wordfilter"
SPAMFILTER_SETTING = "spamfilter"
INVITEFILTER_SETTING = "invitefilter"

mod_settings_map = {
    "word filter": WORDFILTER_SETTING,
    "filter words": WORDFILTER_SETTING,
    "filterwords": WORDFILTER_SETTING,
    "wordfilter": WORDFILTER_SETTING,

    "spam filter": SPAMFILTER_SETTING,
    "filter spam": SPAMFILTER_SETTING,
    "spamfilter": SPAMFILTER_SETTING,
    "filterspam": SPAMFILTER_SETTING,

    "invite filter": INVITEFILTER_SETTING,
    "filterinvite": INVITEFILTER_SETTING,
    "invitefilter": INVITEFILTER_SETTING,
}

# IMPORTANT
# The format for saving server data is => server:id_here
# For commands => commands:id_here
# For mutes => mutes:id_here
# For blacklist => blacklist:id_here
# For selfroles => sr:


class RedisServerHandler(ServerHandler, metaclass=Singleton):
    __slots__ = ("_redis", "redis", "pool")

    def __init__(self, redis_ip, redis_port, redis_password):
        super().__init__()

        self.pool = redis.ConnectionPool(host=redis_ip, port=redis_port, password=redis_password, db=0)
        log.info("Redis ConnectionPool created")

        self.redis = redis.StrictRedis(connection_pool=self.pool)

        try:
            self.redis.ping()
        except redis.ConnectionError:
            log.critical("Could not connect to Redis db!")
            raise RuntimeError

        log.info("Connected to Redis database")

    def bg_save(self):
        return bool(self.redis.bgsave() == b"OK")

    def server_setup(self, server: Guild):
        # These are server defaults
        s_data = server_defaults.copy()
        s_data["owner"] = server.owner.id
        s_data["name"] = server.name

        sid = "server:{}".format(server.id)

        self.redis.hmset(sid, s_data)
        # commands:id, mutes:id, blacklist:id and sr:id are created automatically when needed

        log.info("New server: {}".format(server.name))

    def reset_server(self, server: Guild):
        sid = "server:{}".format(server.id)
        self.redis.delete(sid)
        self.redis.hmset(sid, server_defaults.copy())

        log.info("Guild reset: {}".format(server.name))

    def server_exists(self, server_id: int) -> bool:
        return bool(decode(self.redis.exists("server:{}".format(server_id))))

    def check_server(self, server: Guild):
        # shortcut for checking sever existence
        if not self.server_exists(server.id):
            self.server_setup(server)

    def get_server_data(self, server) -> dict:
        # NOTE: HGETALL returns a dict with binary keys and values!
        base = decode(self.redis.hgetall("server:{}".format(server.id)))
        cmd_list = self.get_custom_commands(server)
        bl = self.get_blacklists(server)
        mutes = self.get_mute_list(server)

        data = decode(base)
        data["commands"] = cmd_list
        data["blacklist"] = bl
        data["mutes"] = mutes

        return data

    def get_var(self, server_id: int, key: str):
        # If value is in json, it will be a json-encoded string and not parsed
        return decode(self.redis.hget("server:{}".format(server_id), key))

    @validate_input
    def update_var(self, server_id: int, key: str, value: str) -> bool:
        return bin2bool(self.redis.hset("server:{}".format(server_id), key, value))

    @validate_input
    def update_moderation_settings(self, server_id: int, key: str, value: bool) -> bool:
        if not mod_settings_map.get(key):
            raise TypeError("invalid moderation setting")

        return bin2bool(self.redis.hset("server:{}".format(server_id), mod_settings_map.get(key), value))

    def check_server_vars(self, server: Guild):
        try:
            serv_ns = "server:{}".format(server.id)

            if decode(self.redis.hget(serv_ns, "owner")) != str(server.owner.id):
                self.redis.hset(serv_ns, "owner", server.owner.id)

            if decode(self.redis.hget(serv_ns, "name")) != str(server.name):
                self.redis.hset(serv_ns, "name", server.name)
        except AttributeError:
            pass

    def check_old_servers(self, current_servers: list):
        servers = ["server:" + str(s_id) for s_id in current_servers]
        redis_servers = [decode(a) for a in self.redis.scan_iter(match="server:*")]

        # Filter only removed servers
        removed_servers = set(redis_servers) - set(servers)

        # Delete every old server
        for rem_serv in removed_servers:
            self.delete_server(rem_serv.strip("server:"))

        log.info("Removed {} old servers.".format(len(removed_servers)))

    def delete_server(self, server_id: int):
        self.redis.delete("commands:{}".format(server_id))
        self.redis.delete("blacklist:{}".format(server_id))
        self.redis.delete("mutes:{}".format(server_id))
        self.redis.delete("server:{}".format(server_id))
        self.redis.delete("sr:{}".format(server_id))

        log.info("Deleted server: {}".format(server_id))

    @validate_input
    def set_command(self, server: Guild, trigger: str, response: str) -> bool:
        if len(trigger) > 80:
            return False

        return self.redis.hset("commands:{}".format(server.id), trigger, response)

    def remove_command(self, server: Guild, trigger: str) -> bool:
        serv = "commands:{}".format(server.id)

        return bin2bool(self.redis.hdel(serv, trigger))

    def get_custom_commands(self, server_id: int) -> dict:
        return decode(self.redis.hgetall("commands:{}".format(server_id)))

    def get_command_amount(self, server_id: int) -> int:
        return decode(self.redis.hlen("commands:{}".format(server_id)))

    def custom_command_exists(self, server_id: int, trigger: str):
        return self.redis.hexists("commands:{}".format(server_id), trigger)

    @validate_input
    def add_channel_blacklist(self, server_id: int, channel_id: int):
        serv = "blacklist:{}".format(server_id)
        return bool(self.redis.sadd(serv, channel_id))

    @validate_input
    def remove_channel_blacklist(self, server_id: int, channel_id: int):
        serv = "blacklist:{}".format(server_id)
        return bool(self.redis.srem(serv, channel_id))

    def is_blacklisted(self, server_id, channel_id):
        serv = "blacklist:{}".format(server_id)
        return self.redis.sismember(serv, channel_id)

    def get_blacklists(self, server_id):
        serv = "blacklist:{}".format(server_id)
        return list(decode(self.redis.smembers(serv)) or [])

    def get_prefix(self, server: Guild):
        return decode(self.redis.hget("server:{}".format(server.id), "prefix"))

    @validate_input
    def change_prefix(self, server, prefix):
        self.redis.hset("server:{}".format(server.id), "prefix", prefix)

    def has_spam_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), SPAMFILTER_SETTING)) is True

    def has_word_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), WORDFILTER_SETTING)) is True

    def has_invite_filter(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), INVITEFILTER_SETTING)) is True

    def get_log_channel(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), "logchannel"))

    def is_sleeping(self, server_id):
        return decode(self.redis.hget("server:{}".format(server_id), "sleeping"))

    @validate_input
    def set_sleeping(self, server, bool_var):
        self.redis.hset("server:{}".format(server.id), "sleeping", bool_var)

    @validate_input
    def mute(self, server, user_id):
        serv = "mutes:{}".format(server.id)
        return bool(self.redis.sadd(serv, user_id))

    @validate_input
    def unmute(self, member_id, server_id):
        serv = "mutes:{}".format(server_id)
        return bool(self.redis.srem(serv, member_id))

    def is_muted(self, server, user_id):
        serv = "mutes:{}".format(server.id, user_id)
        return bool(self.redis.sismember(serv, user_id))

    def get_mute_list(self, server):
        serv = "mutes:{}".format(server.id)
        return list(decode(self.redis.smembers(serv)) or [])

    def get_defaultchannel(self, server):
        return decode(self.redis.hget("server:{}".format(server.id), "dchan"))

    def set_defaultchannel(self, server, channel_id):
        self.redis.hset("server:{}".format(server.id), "dchan", channel_id)

    def set_lang(self, server_id, language):
        self.redis.hset("server:{}".format(server_id), "lang", language)

    def get_lang(self, server_id):
        return decode(self.redis.hget("server:{}".format(server_id), "lang"))

    def get_selfroles(self, server_id):
        return decode(self.redis.smembers("sr:{}".format(server_id)))

    def add_selfrole(self, server_id, role_name):
        return bin2bool(self.redis.sadd("sr:{}".format(server_id), role_name))

    def remove_selfrole(self, server_id, role_name):
        return bin2bool(self.redis.srem("sr:{}".format(server_id), role_name))

    def is_selfrole(self, server_id, role_name):
        return bin2bool(self.redis.sismember("sr:{}".format(server_id), role_name))

    # Special debug methods
    def db_info(self, section=None):
        return decode(self.redis.info(section=section))

    def db_size(self):
        return int(self.redis.dbsize())

    # Plugin storage system
    def get_plugin_data_manager(self, namespace, *args, **kwargs):
        return RedisPluginDataManager(self.pool, namespace, *args, **kwargs)


class RedisPluginDataManager:
    def __init__(self, pool, namespace, *_, **__):
        self.namespace = str(namespace)
        self.redis = redis.StrictRedis(connection_pool=pool)

        log.info("New plugin namespace registered: {}".format(self.namespace))

    def _make_key(self, name):
        # Returns a hash name formatted with the namespace
        return "{}:{}".format(self.namespace, name)

    def set(self, key, val):
        return decode(self.redis.set(self._make_key(key), val))

    def get(self, key):
        return decode(self.redis.get(self._make_key(key)))

    def hget(self, name, field):
        return decode(self.redis.hget(self._make_key(name), field))

    def hgetall(self, name):
        return decode(self.redis.hgetall(self._make_key(name)))

    def hdel(self, name, field):
        return decode(self.redis.hdel(self._make_key(name), field))

    def hmset(self, name, payload):
        return decode(self.redis.hmset(self._make_key(name), payload))

    def hset(self, name, field, value):
        return decode(self.redis.hset(self._make_key(name), field, value))

    def hexists(self, name, field):
        return self.redis.hexists(name, field)

    def exists(self, name):
        return bool(decode(self.redis.exists(self._make_key(name))))

    def delete(self, name):
        return bool(decode(self.redis.delete(self._make_key(name))))

    def scan_iter(self, match, use_namespace=True):
        match = self._make_key(match) if use_namespace else match
        return [a for a in self.redis.scan_iter(match)]

    def lpush(self, key, value):
        return decode(self.redis.lpush(self._make_key(key), value))

    def lrange(self, key, from_key=0, to_key=-1):
        return decode(self.redis.lrange(self._make_key(key), from_key, to_key))

    def lrem(self, key, value, count=1):
        return decode(self.redis.lrem(key, count, value))

    def lpop(self, key, index):
        return decode(self.redis.lpop(key, index))
