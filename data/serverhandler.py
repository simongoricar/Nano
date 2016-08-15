# coding=utf-8

"""Server data handler for Nano"""


# Optimized in v2.1.3

import configparser
import threading
import time
import logging

from yaml import load,dump


# Decorator

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

parser = configparser.ConfigParser()
parser.read("settings.ini")

logger = logging.getLogger(__name__)

server_nondepend_defaults = {
    "filterwords": 0,
    "filterspam": 0,
    "welcomemsg": "Welcome to :server, :user!",
    "kickmsg": ":user has been kicked.",
    "banmsg": ":user has been banned.",
    "leavemsg": "Bye, **:user**",
    "blacklisted": [],
    "muted": [],
    "customcmds": {},
    "admins": [],
    "logchannel": "logs",
    "sleeping": 0,
    # "onban": 0, //removed
    # "sayhi": 0, //changed
    "prefix": parser.get("Settings","defaultprefix")
}

server_deprecated_settings = [
    "onban",
    "sayhi"
]

# Singleton class
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ServerHandler(metaclass=Singleton):
    def __init__(self):
        self.file = "data/servers.yml"

        with open(self.file, "r") as file:
            self.cached_file = load(file)

        self.is_old = False
        self.data_lock = False

    def lock(self):
        self.data_lock = True

    def wait_until_release(self):
        while self.data_lock is True:
            time.sleep(0.05)
        return

    def release_lock(self):
        self.data_lock = False

    def server_setup(self, server):
        data = self.cached_file

        data[server.id] = {"name" : server.name,
                           "owner" : server.owner.name,
                           "filterwords" : False,
                           "filterspam" : False,
                           "welcomemsg": ":user, Welcome to :server!",
                           "kickmsg": ":user has been kicked.",
                           "banmsg": ":user has been banned.",
                           "blacklisted" : [],
                           "muted" : [],
                           "customcmds" : {},
                           "admins" : [],
                           "logchannel" : "logs",
                           "sleeping" : False,
                           "prefix" : str(parser.get("Settings","defaultprefix"))}

        logger.info("Queued new server for write: {}".format(server.name))

        self.queue_write(data)

    @threaded
    def queue_write(self, data):
        self.cached_file = data
        self.wait_until_release()

        self.lock()
        logger.info("Write queued")

        with open(self.file, "w") as file:
            file.write(dump(data, default_flow_style=False))  # Makes it readable
        self.release_lock()

    def reload(self):
        self.wait_until_release()

        self.lock()
        with open(self.file, "r") as file:
            self.cached_file = load(file)
        self.release_lock()

        logger.info("Reloaded servers.yml")

    def get_all_data(self):
        return self.cached_file

    def get_server_data(self, server_id):
        return self.cached_file.get(server_id)

    def serverexists(self, server):
        try:
            if server.id in self.cached_file:
                return True
            else:
                return False
        except AttributeError:
            return True

    def update_moderation_settings(self, server, key, value):
        data = self.cached_file

        # XD
        #if value is True:
        #    value = True
        #elif value is False:
        #    value = False

        if int(value) > 1:
            value = True
        elif int(value) < 0:
            value = False

        if server.id not in data:
            self.server_setup(server)

        if str(key) == "filterwords" or str(key) == "wordfilter" or str(key).lower() == "word filter":
            data[server.id]["filterwods"] = value
            self.queue_write(data)

        elif str(key) == "filterspam" or str(key) == "spamfilter" or str(key).lower() == "spam filter":
            data[server.id]["filterspam"] = value
            self.queue_write(data)

        return bool(value)

    def update_var(self, sid, key, value):
        data = self.cached_file

        data[sid][key] = value
        self.queue_write(data)

    def _check_server_vars(self, sid, delete_old=True):
        data = self.cached_file
        do = self.cached_file

        for var in server_nondepend_defaults.keys():
            sd = data.get(sid)
            if sd:
                if sd.get(var) is None:
                    data[sid][var] = server_nondepend_defaults.get(var)

        if delete_old:
            self._check_deprecated_vars(sid, data, old=do)
        else:
            if do != data:
                self.queue_write(data)

    def _check_deprecated_vars(self, server, data=None, old=None):
        if not data:
            data = self.cached_file
        if not old:
            old = self.cached_file

        data[server] = {key: value for key, value in data[server].items() if key not in server_deprecated_settings}
        if old != data:
            self.queue_write(data)

    def update_command(self, server, trigger, response):
        try:
            data = self.cached_file
                
            data[server.id]["customcmds"][trigger] = response
            if "nano.checkcmd" in data[server.id]["customcmds"]:
                data[server.id]["customcmds"].pop("nano.checkcmds",0)
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
        except UnicodeEncodeError:
            pass

    def remove_command(self, server, trigger):
        data = self.cached_file

        data[server.id]["customcmds"].pop(trigger,0)
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

        if user.id in data[server.id]["admins"]:
            return
        data[server.id]["admins"].append(str(user.id))

        self.queue_write(data)

    def remove_admin(self, server, user):
        data = self.cached_file

        try:
            data[server.id]["admins"].remove(user.id)
        except ValueError:
            return  # If user is not admin

        self.queue_write(data)

    def change_prefix(self, server, prefix):
        data = self.cached_file

        if server.id not in data:
            self.server_setup(server)
        data[server.id]["prefix"] = prefix

        self.queue_write(data)

    def isblacklisted(self, server, channel):
        if channel.is_private:
            return
        try:
            data = self.cached_file
               
            if channel.name in data[server.id]["blacklisted"]:
                return True
            else:
                return False
        except KeyError:
            return False

    def needspamfilter(self, server):
        data = self.cached_file
            
        return bool(data[server.id]["filterspam"])

    def needwordfilter(self, server):
        data = self.cached_file
            
        return bool(data[server.id]["filterwords"])

    def returnsettings(self, sid):
        data = self.cached_file
            
        return data.get(sid)

    def returncommands(self, server):
        data = self.cached_file
            
        return data[server.id]["customcmds"]

    def returnadmins(self, server):
        data = self.cached_file
            
        return data[server.id]["admins"]

    def returnlogch(self, server):
        data = self.cached_file
            
        return data[server.id]["logchannel"]

    def issleeping(self, server):
        data = self.cached_file
            
        return bool(data[server.id]["sleeping"])

    def setsleeping(self, server, var):
        data = self.cached_file

        data[server.id]["sleeping"] = var
        self.queue_write(data)

    def haslogging(self, server):
        if server is None:
            return True
        data = self.cached_file
            
        return bool(data[server.id]["logchannel"])

    def mute(self, user):
        data = self.cached_file
            

        if not user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].append(user.id)
            self.queue_write(data)

        else:
            pass

    def ismuted(self, user):  # Actually supposed to be a Member class (not User, because it doesn't have server property)
        data = self.cached_file

        return bool(user.id in data[user.server.id]["muted"])

    def unmute(self, user):
        data = self.cached_file
            

        if user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].pop(user.id)
            self.queue_write(data)

        else:
            pass

    def mutelist(self, server):
        data = self.cached_file
            

        return data[server.id]["muted"]

    def get_name(self, sid):
        data = self.cached_file
            
        return data.get(sid)["name"]

    def update_name(self, sid, name):
        data = self.cached_file
            

        data[sid]["name"] = name
        self.queue_write(data)

    def get_owner(self, sid):
        data = self.cached_file
            
        return data.get(sid)["owner"]

    def update_owner(self, sid, name):
        data = self.cached_file
            

        data[sid]["owner"] = name
        self.queue_write(data)

    def get_var(self, sid, var):
        data = self.cached_file
            

        return data.get(sid).get(var)