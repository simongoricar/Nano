from config import filterwords
__author__ = "DefaltSimon"

# Spam detection plugin for AyyBot

# Add users you want to be ignored
ignored = ["AyyBot"]


class SpamDetection:
    def __init__(self):
        self.whitelist = []
        for this in ignored:
            self.whitelist.append(this)
    def addwhitelist(self,user):
        self.whitelist.append(user.name)
        return
    def check(self,message):
        pass
        # Is disabled until further... update
        #if message.author.name in self.whitelist or len(message.mentions) > 0:
        #    return
        #words = message.content.lower().split()
        #wordminus = round(len(words)/2,0)
        ## Checks start here
        #count = 0
        #spamcount = 0
        #for w in words:
        #    if w == words[count - 1] or words[count - 2]:
        #        spamcount += 1
        #    count += 1
        #if (spamcount - wordminus) > 7:
        #    return True

# Swearing detection for AyyBot

class Swearing:
    def __init__(self):
        self.whitelist = []
    def check(self,message):
        if message.author.name in self.whitelist:
            return
        msg = str(message.content).lower().split()
        for word in msg:
            if word in filterwords:
                return True