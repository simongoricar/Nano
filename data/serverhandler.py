# coding=utf-8

"""Server data handler for AyyBot"""


# Optimized in v2.1.3

from yaml import load,dump
import configparser
import threading


# Decorator

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

parser = configparser.ConfigParser()
parser.read("settings.ini")

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
    # "sayhi": 0, //moved
    "prefix": parser.get("Settings","defaultprefix")
}

class ServerHandler:
    def __init__(self):
        pass

    def serversetup(self,server):
        data = self._get_data()

        data[server.id] = {"name" : server.name,
                           "owner" : server.owner.name,
                           "filterwords" : 0,
                           "filterspam" : 0,
                           "welcomemsg": ":user, Welcome to :server!",
                           "kickmsg": ":user has been kicked.",
                           "banmsg": ":user has been banned.",
                           "blacklisted" : [],
                           "muted" : [],
                           "customcmds" : {},
                           "admins" : [],
                           "logchannel" : "logs",
                           "sleeping" : 0,
                           "prefix" : str(parser.get("Settings","defaultprefix"))}

        self.write(data)

    @staticmethod
    def write(data):
        with open("data/servers.yml", "w") as file:
            file.write(dump(data, default_flow_style=False))

    @staticmethod
    def _get_data():
        with open("data/servers.yml","r") as file:
            return load(file)

    def get_all_data(self, server_id):
        data = self._get_data()
        return data.get(server_id)

    def serverexists(self, server):
        data = self._get_data()

        try:
            if server.id in data:
                return True
            else:
                return False
        except AttributeError:
            return True

    def updatesettings(self, server, key, value):
        data = self._get_data()

        if str(value) == "True":
            value = 1
        elif str(value) == "False":
            value = 0

        elif int(value) >= 1:
            value = 1
        elif int(value) <= 0:
            value = 0

        if server.id not in data:
            self.serversetup(server)

        if str(key) == "filterwords" or str(key) == "wordfilter" or str(key).lower() == "word filter":
            data[server.id].update({"filterwords" : int(value)})
            self.write(data)

        elif str(key) == "filterspam" or str(key) == "spamfilter" or str(key).lower() == "spam filter":
            data[server.id].update({"filterspam" : int(value)})
            self.write(data)

        elif str(key) == "welcome" or str(key) == "sayhi" or str(key).lower() == "welcome message":
            data[server.id].update({"sayhi" : int(value)})
            self.write(data)

        elif str(key) == "announceban" or str(key) == "onban" or str(key).lower() == "announce ban":
            data[server.id].update({"onban" : int(value)})
            self.write(data)

        return bool(value)

    def _force_update_var(self, server, key, value):
        data = self._get_data()

        data[server][key] = value
        self.write(data)

    @threaded
    def _check_server_vars(self, server):
        data = self._get_data()

        for var in server_nondepend_defaults.keys():
            if data.get(server).get(var) is None:
                data.get(server)[var] = server_nondepend_defaults.get(var)
        self.write(data)

    def updatecommand(self, server, trigger, response):
        try:
            data = self._get_data()
                
            data[server.id]["customcmds"][trigger] = response
            if "ayybot.checkcmd" in data[server.id]["customcmds"]:
                data[server.id]["customcmds"].pop("ayybot.checkcmds",0)
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
        except UnicodeEncodeError:
            pass

    def removecommand(self, server, trigger):
        data = self._get_data()

        data[server.id]["customcmds"].pop(trigger,0)
        self.write(data)

    def updatechannels(self ,server, channel):
        data = self._get_data()

        data[server.id]["blacklisted"].append(str(channel))
        self.write(data)

    def removechannels(self,server,channel):
        data = self._get_data()

        data[server.id]["blacklisted"].pop(str(channel))
        self.write(data)

    def addadmin(self,server,user):
        data = self._get_data()

        if user.id in data[server.id]["admins"]:
            return
        data[server.id]["admins"].append(str(user.id))

        self.write(data)

    def changeprefix(self,server,prefix):
        data = self._get_data()
            
        if server.id not in data:
            self.serversetup(server)
        data[server.id]["prefix"] = prefix

        self.write(data)

    def removeadmin(self,server,user):
        data = self._get_data()

        try:
            data[server.id]["admins"].remove(user.id)
        except ValueError:
            return  # If user is not admin

        self.write(data)

    def isblacklisted(self, server, channel):
        if channel.is_private:
            return
        try:
            data = self._get_data()
               
            if channel.name in data[server.id]["blacklisted"]:
                return True
            else:
                return False
        except KeyError:
            return False

    def needspamfilter(self, server):
        data = self._get_data()
            
        return bool(data[server.id]["filterspam"])

    def needwordfilter(self, server):
        data = self._get_data()
            
        return bool(data[server.id]["filterwords"])

    def returnsettings(self, sid):
        data = self._get_data()
            
        return data.get(sid)

    def returncommands(self, server):
        data = self._get_data()
            
        return data[server.id]["customcmds"]

    def returnadmins(self, server):
        data = self._get_data()
            
        return data[server.id]["admins"]

    def returnlogch(self, server):
        data = self._get_data()
            
        return data[server.id]["logchannel"]

    def issleeping(self, server):
        data = self._get_data()
            
        return bool(data[server.id]["sleeping"])

    def setsleeping(self, server, var):
        data = self._get_data()

        data[server.id]["sleeping"] = var
        self.write(data)

    def haslogging(self, server):
        if server is None:
            return True
        data = self._get_data()
            
        return bool(data[server.id]["logchannel"])

    def sayhi(self, server):
        data = self._get_data()
            
        return bool(data[server.id]["welcomemsg"])

    def _onban(self, server):  # Deprecated
        data = self._get_data()
            
        return bool(data[server.id]["onban"])

    def mute(self, user):
        data = self._get_data()
            

        if not user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].append(user.id)
            self.write(data)

        else:
            pass

    def ismuted(self, user):  # Actually supposed to be a Member class (not User, because it doesn't have server property)
        data = self._get_data()

        return bool(user.id in data[user.server.id]["muted"])

    def unmute(self, user):
        data = self._get_data()
            

        if user.id in data[user.server.id]["muted"]:
            data[user.server.id]["muted"].pop(user.id)
            self.write(data)

        else:
            pass

    def mutelist(self, server):
        data = self._get_data()
            

        return data[server.id]["muted"]

    def get_name(self, sid):
        data = self._get_data()
            
        return data.get(sid)["name"]

    def update_name(self, sid, name):
        data = self._get_data()
            

        data[sid]["name"] = name
        self.write(data)

    def get_owner(self, sid):
        data = self._get_data()
            
        return data.get(sid)["owner"]

    def update_owner(self, sid, name):
        data = self._get_data()
            

        data[sid]["owner"] = name
        self.write(data)

    def get_var(self, sid, var):
        data = self._get_data()
            

        return data.get(sid).get(var)