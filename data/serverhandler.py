"""Part of AyyBot"""

from yaml import load,dump
import configparser



class ServerHandler:
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.parser.read("settings.ini")
    def serversetup(self,server):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            # Setup
            defaultprf = self.parser.get("Settings","defaultprefix")
            data[server.id] = {"name" : server.name, "owner" : server.owner.name, "filterwords" : 0, "filterspam" : 0, "blacklisted" : [], "customcmds" : {}, "admins" : [], "logchannel" : "logs", "sleeping" : 0, "sayhi" : 0, "prefix" : str(defaultprf)}
        with open("data/servers.yml","w") as outfile:
            outfile.write(dump(data,default_flow_style=False))
    def serverexists(self,server):
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
            if value != 0 or 1:
                value == 1
            if server.id not in data:
                self.serversetup(server)

            if str(key) == "filterwords":
                data[server.id].update({"filterwords" : int(value)})
                with open("data/servers.yml","w") as outfile:
                    outfile.write(dump(data,default_flow_style=False))
            elif str(key) == "filterspam":
                data[server.id].update({"filterspam" : int(value)})
                with open("data/servers.yml","w") as outfile:
                    outfile.write(dump(data,default_flow_style=False))
    def updatecommand(self,server,trigger,response):
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
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
    def updatechannels(self,server,channel):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["blacklisted"].append(str(channel))
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
    def updateadmins(self,server,user):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            if user.id in data[server.id]["admins"]:
                return
            data[server.id]["admins"].append(str(user.id))
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
    def changeprefix(self,server,prefix):
        with open("data/servers.yml","r") as file:
            data = load(file)
            if server.id not in data:
                self.serversetup(server)
            data[server.id]["prefix"] = prefix
        with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
    def removeadmin(self,server,user):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["admins"].remove(user.id)
            with open("data/servers.yml","w") as outfile:
                outfile.write(dump(data,default_flow_style=False))
    def isblacklisted(self,server,channel):
        if channel.is_private:
            return
        try:
            with open("data/servers.yml","r+") as file:
               data = load(file)
               if channel.name in data[server.id]["blacklisted"]:
                   return True
               else:
                   return False
        except KeyError:
            return False
    def needspamfilter(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["filterspam"])
    def needwordfilter(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["filterwords"])

    def returnsettings(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]
    def returncommands(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["customcmds"]
    def returnwhitelisted(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["admins"]
    def returnlogch(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return data[server.id]["logchannel"]

    def issleeping(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["sleeping"])
    def setsleeping(self,server,wat):
        with open("data/servers.yml","r+") as file:
            data = load(file)
            data[server.id]["sleeping"] = wat
        with open("data/servers.yml","w") as outfile:
            outfile.write(dump(data,default_flow_style=False))
    def disabledlogging(self,server):
        if server is None:
            return True
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["logchannel"])
    def shouldsayhi(self,server):
        with open("data/servers.yml","r") as file:
            data = load(file)
            return bool(data[server.id]["sayhi"])