# coding=utf-8

"""Server data handler for AyyBot"""


# This module is pretty much the same compared to v1, with some optimizations

from yaml import load,dump
import configparser


class ServerHandler:
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.parser.read("settings.ini")

    def serversetup(self,server):
        with open("data/servers.yml","r+") as file:
            data = load(file)

            defaultpref = self.parser.get("Settings","defaultprefix")
            data[server.id] = {"name" : server.name, "owner" : server.owner.name, "filterwords" : 0, "filterspam" : 0, "blacklisted" : [], "muted" : [], "customcmds" : {}, "admins" : [], "logchannel" : "logs", "sleeping" : 0, "onban": 0, "sayhi" : 0, "prefix" : str(defaultpref)}

        self.write(data)

    @staticmethod
    def write(data):
        with open("data/servers.yml","w") as file:
            file.write(dump(data,default_flow_style=False))

    @staticmethod
    def serverexists(server):
        with open("data/servers.yml","r") as file:
            data = load(file)

            try:
                if server.id in data:
                    return True
                else:
                    return False
            except AttributeError:
                return True

    def updatesettings(self,server,key,value):
        with open("data/servers.yml","r+") as file:

            data = load(file)

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
    @staticmethod
    def updatecommand(server,trigger,response):
        try:
            with open("data/servers.yml","r+") as file:
                data = load(file)
                data[server.id]["customcmds"][trigger] = response
                if "ayybot.checkcmd" in data[server.id]["customcmds"]:
                    data[server.id]["customcmds"].pop("ayybot.checkcmds",0)
                with open("data/servers.yml","w") as outfile:
                    outfile.write(dump(data,default_flow_style=False))
        except UnicodeEncodeError:
            pass

    def removecommand(self,server,trigger):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["customcmds"].pop(trigger,0)

        self.write(data)

    def updatechannels(self,server,channel):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["blacklisted"].append(str(channel))

        self.write(data)

    def removechannels(self,server,channel):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["blacklisted"].pop(str(channel))

        self.write(data)

    def addadmin(self,server,user):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            if user.id in data[server.id]["admins"]:
                return
            data[server.id]["admins"].append(str(user.id))

        self.write(data)

    def changeprefix(self,server,prefix):
        with open("data/servers.yml","r") as file:
            data = load(file)
            if server.id not in data:
                self.serversetup(server)
            data[server.id]["prefix"] = prefix

        self.write(data)

    def removeadmin(self,server,user):
        with open("data/servers.yml","r+") as file:
            data = load(file)

            try:
                data[server.id]["admins"].remove(user.id)
            except ValueError:
                return  # If user is not admin

        self.write(data)

    @staticmethod
    def isblacklisted(server,channel):
        if channel.is_private:
            return
        try:
            with open("data/servers.yml","r") as file:
               data = load(file)
               if channel.name in data[server.id]["blacklisted"]:
                   return True
               else:
                   return False
        except KeyError:
            return False

    @staticmethod
    def needspamfilter(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["filterspam"])

    @staticmethod
    def needwordfilter(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["filterwords"])

    @staticmethod
    def returnsettings(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]

    @staticmethod
    def returncommands(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["customcmds"]

    @staticmethod
    def returnadmins(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["admins"]

    @staticmethod
    def returnlogch(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["logchannel"]

    @staticmethod
    def issleeping(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["sleeping"])

    def setsleeping(self,server,wat):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["sleeping"] = wat

        self.write(data)

    @staticmethod
    def haslogging(server):
        if server is None:
            return True
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["logchannel"])

    @staticmethod
    def sayhi(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["sayhi"])

    @staticmethod
    def onban(server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["onban"])

    def mute(self, user):
        with open("data/servers.yml","r") as file:
            data = load(file)

            if not user.id in data[user.server.id]["muted"]:
                data[user.server.id]["muted"].append(user.id)
                self.write(data)

            else:
                pass

    def ismuted(self, user):  # Actually supposed to be a Member class (not User, because it doesn't have server property)
        with open("data/servers.yml","r") as file:
            data = load(file)

            return bool(user.id in data[user.server.id]["muted"])

    def unmute(self, user):
        with open("data/servers.yml","r") as file:
            data = load(file)

            if user.id in data[user.server.id]["muted"]:
                data[user.server.id]["muted"].pop(user.id)
                self.write(data)

            else:
                pass

    def mutelist(self, server):
        with open("data/servers.yml","r") as file:
            data = load(file)

            return data[server.id]["muted"]