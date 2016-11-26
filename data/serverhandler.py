# coding=utf-8
import configparser
import time
import logging
import copy
from yaml import load, dump

from .utils import threaded, Singleton, get_decision

__author__ = "DefaltSimon"

# Server handler for Nano

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

par = configparser.ConfigParser()
par.read("settings.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

server_nondepend_defaults = {
    "filterwords": False,
    "filterspam": False,
    "filterinvite": False,
    "welcomemsg": "Welcome to :server, :user!",
    "kickmsg": ":user has been kicked.",
    "banmsg": ":user has been banned.",
    "leavemsg": "**:user** has left the server :cry:",
    "blacklisted": [],
    "disabled": [],
    "muted": [],
    "customcmds": {},
    "admins": [],
    "logchannel": "logs",
    "sleeping": 0,
    # "onban": 0, //removed
    # "sayhi": 0, //changed
    "prefix": parser.get("Servers", "defaultprefix")
}

# ServerHandler is a singleton, so it can have only one instance


class ServerHandler(metaclass=Singleton):  # Singleton is imported from utils
    def __init__(self):
        self.file = "data/servers.yml"

        # Loads the file into memory
        with open(self.file, "r") as file:
            self.cached_file = load(file)

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
    def server_setup(self, server):
        data = self.cached_file

        # These are server defaults
        default_prefix = str(parser.get("Servers", "defaultprefix"))

        self.cached_file[server.id] = {"name": server.name,
                                       "owner": server.owner.name,
                                       "filterwords": False,
                                       "filterspam": False,
                                       "filterinvite": False,
                                       "sleeping": False,
                                       "welcomemsg": ":user, Welcome to :server!",
                                       "kickmsg": "**:user** has been kicked.",
                                       "banmsg": "**:user** has been banned.",
                                       "leavemsg": "**:user** has left the server :cry:",
                                       "blacklisted": [],
                                       "muted": [],
                                       "customcmds": {},
                                       "admins": [],
                                       "logchannel": "logs",
                                       "prefix": default_prefix}

        log.info("New server: {}".format(server.name))

        self.queue_write(data)

    def server_exists(self, server):
        return server.id in self.cached_file

    @threaded
    def queue_write(self, data):
        self.cached_file = copy.deepcopy(data)
        self.wait_until_release()

        self.lock()
        log.info("Write queued")

        with open(self.file, "w") as file:
            file.write(dump(data, default_flow_style=False))  # Makes it readable
        self.release_lock()

    def reload(self):
        self.wait_until_release()

        self.lock()
        with open(self.file, "r") as file:
            self.cached_file = load(file)
        self.release_lock()

        log.info("Reloaded servers.yml")

    def _queue_modification(self, thing, *args, **kwargs):
        # Not used anymore, kept as "private"
        self.wait_until_release()
        self.lock()

        thing(*args, **kwargs)

        self.release_lock()

    def get_all_data(self):
        return self.cached_file

    def get_server_data(self, server_id):
        return self.cached_file.get(server_id)

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

    def update_var(self, sid, key, value):
        data = self.cached_file

        data[sid][key] = value
        self.queue_write(data)

    def _check_server_vars(self, sid, delete_old=True):
        data = self.cached_file
        modified = False

        server = data.get(sid)
        if data.get(sid):
            for var in server_nondepend_defaults.keys():
                # Check each var; add it if it does not exist
                if server.get(var) is None:
                    data[sid][var] = server_nondepend_defaults[var]
                    modified = True

        #if delete_old:
        #    self._check_deprecated_vars(sid, data, changed=modified)
        #else:
        if modified:
            self.queue_write(data)

    def _delete_old_servers(self, current_servers):
        data = self.cached_file
        modified = False

        # Iterate through servers and remove them if they are not in the current_servers list
        for server in list(data.keys()):
            if server not in current_servers:
                data.pop(server)
                modified = True

        if modified:
            self.queue_write(data)

    def update_command(self, server, trigger, response):
        try:
            data = self.cached_file

            data[server.id]["customcmds"][trigger] = response

            self.queue_write(data)

        except UnicodeEncodeError:
            pass

    def remove_command(self, server, trigger):
        data = self.cached_file

        data[server.id]["customcmds"].pop(trigger, 0)
        self.queue_write(data)

    def add_channel_blacklist(self, server, channel):
        data = self.cached_file

        data[server.id]["blacklisted"].append(str(channel))
        self.queue_write(data)

    def remove_channel_blacklist(self, server, channel):
        data = self.cached_file

        data[server.id]["blacklisted"].pop(str(channel))
        self.queue_write(data)

    def add_admin(self, server, user):
        data = self.cached_file

        # Ignore if user is already in admins
        if user.id in data[server.id]["admins"]:
            return

        data[server.id]["admins"].append(str(user.id))

        self.queue_write(data)

    def remove_admin(self, server, user):
        data = self.cached_file

        try:
            data[server.id]["admins"].remove(user.id)
        except ValueError:
            return  # Ignore if the admin did not exist

        self.queue_write(data)

    def get_prefix(self, server):
        data = self.cached_file

        return data.get(server.id).get("prefix")

    def change_prefix(self, server, prefix):
        data = self.cached_file

        # Check server existence
        if server.id not in data:
            self.server_setup(server)

        data[server.id]["prefix"] = prefix

        self.queue_write(data)

    def is_blacklisted(self, sid, channel):
        if channel.is_private:
            return

        try:
            data = self.cached_file
            return channel.name in data[sid]["blacklisted"]

        except KeyError:
            return False

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

    def set_sleep_state(self, server, var):
        data = self.cached_file

        data[server.id]["sleeping"] = var
        self.queue_write(data)

    def has_logging(self, server):
        if server is None:
            return True
        data = self.cached_file
            
        return bool(data[server.id]["logchannel"])

    def mute(self, user):
        data = self.cached_file

        if user.id not in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].append(user.id)
            self.queue_write(data)

    def is_muted(self, user):
        # user if actually supposed to be a an instance of discord.Member (not User, because it doesn't have server property)
        data = self.cached_file

        return bool(user.id in data[user.server.id]["muted"])

    def unmute(self, user):
        data = self.cached_file

        if user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"] = [u for u in data[user.server.id]["muted"] if user.id not in u]
            self.queue_write(data)

    def mute_list(self, server):
        data = self.cached_file

        return data[server.id]["muted"]

    def update_name(self, sid, name):
        data = self.cached_file

        data[sid]["name"] = name
        self.queue_write(data)

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

    # MAIN check
    def can_use_restricted_commands(self, user, server):
        bo = self.is_bot_owner(user.id)
        so = self.is_server_owner(user.id, server)
        ia = self.is_admin(user, server)

        return any([bo, so, ia])

    @staticmethod
    def is_bot_owner(uid):
        return str(uid) == str(par.get("Settings", "ownerid"))

    @staticmethod
    def is_server_owner(uid, server):
        return str(uid) == str(server.owner.id)

    def is_admin(self, user, server):

        try:
            is_admin = bool(user.id in self.cached_file.get(server.id).get("admins"))
        except TypeError:
            is_admin = False

        if not is_admin:
            for role in user.roles:
                if role.name == "Nano Admin":
                    return True

        return is_admin
