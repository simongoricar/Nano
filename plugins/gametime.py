from yaml import load,dump
import time,discord

__author__ = "DefaltSimon"

# Game time counting plugin for AyyBot
class GameCount:
    def __init__(self):
        self.lasttime = {}
        self.cooldown = {}
    def setlast(self,user,time1):
        self.lasttime[user] = time1
    def deletelast(self,user):
        self.lasttime[user] = None
    def hasplayed(self,user):
        if user in self.lasttime:
            return False
        else:
            return True
    def getplayer(self,user):
        with open("plugins/data.yml","r") as file:
            file = load(file)
            for this in file.keys():
                if this == user:
                    return file[user]
    def getgame(self,user,game):
        with open("plugins/data.yml","r") as file:
            file = load(file)
            mins = file.get(user).get(game)
            return mins
    def add(self,user,server,game,time1):
        user2 = discord.utils.get(server.members, name=user)
        if user in self.cooldown:
            if time.time() - self.cooldown[user] < 0.20:
                return
        else:
            self.cooldown[user] = time.time()
        with open("plugins/data.yml","r+") as file:
            file = load(file)
            final = file
            if user2.name not in self.lasttime:
                return
            if user2.id not in file:
                final[user2.id] = {"username" : user2.name}
            if game not in file[user2.id]:
                final[user2.id][game] = 0
            final[user2.id].update( { game :  int(final[user2.id][game] + round(time1 - self.lasttime[user2.name],0)) })
        with open("plugins/data.yml","w") as outfile:
            outfile.write(dump(final,default_flow_style=False))
