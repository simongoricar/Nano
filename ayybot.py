__author__ = 'DefaltSimon'
__version__ = '1.6.4'

import discord,asyncio
import time,configparser,wikipedia,requests,sys,urllib,socket
from os import listdir,rename,system
from random import randint
from config import customcmd,eightball,helpmsg1,adminmsg,infomsg,jokemsg,memelist,quotes,conversation
from datetime import timedelta, datetime
from giphypop import translate,screensaver,gif
from bs4 import BeautifulSoup
from plugins import moderator,votebot,gametime,stats
from data import serverhandler
from yaml import load
from io import StringIO

class SetStatus:
    def __init__(self):
        pass
    async def startup(self):
        game = discord.Game(name=str(parser.get("Settings","status")))
        loop.create_task(client.change_status(game=game))
    async def set(self,game):
        game = discord.Game(name=str(game))
        loop.create_task(client.change_status(game=game))

class TimeUtil:
    def __init__(self):
        self.starttime = time.time()
        self.lasttime = time.time()
    def getstartup(self):
        return int(self.starttime)
    def getlast(self):
        return int(self.lasttime)
    def setlast(self):
        self.lasttime = time.time()
    def gettime(self,timeelapsed):
        sec = timedelta(seconds=timeelapsed)
        d = datetime(1, 1, 1) + sec
        this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
        return this

client = discord.Client()

Timeutil = TimeUtil()
parser = configparser.ConfigParser()
handler = serverhandler.ServerHandler()

stat = stats.BotStats()
vote = votebot.Vote()
spam = moderator.SpamDetection()
swearing = moderator.Swearing()
game = gametime.GameCount()

parser.read("settings.ini")
ownerid = str(parser.get("Settings","ownerid"))

# Write two newlines to data/log.txt
if parser.getboolean("Settings","WriteLogs") is True:
    with open('data/log.txt','a') as file:
        file.write("\n----- " + str(time.strftime("%Y-%m-%d %H:%M:%S", )) + " : startup -----\n")

def logdis(message,type):
    try:
        if parser.getboolean("Settings","WriteLogs") is True:
            if type == "message":
                with open('data/log.txt',"a") as file2:
                    one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
                    str2 = one + str(" : {msg} by {usr}\n".format(msg=message.content,usr=message.author))
                    file2.write(str2)
            elif type == "write":
                with open('data/log.txt',"a") as file2:
                    one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
                    str2 = one + str(" : {}\n".format(str(message)))
                    file2.write(str2)
    except UnicodeEncodeError:
        pass

# Commands
class AyyBot:
    def __init__(self):
        self.admins = {}
        self.prefixes = {}

        self.updateadmins()
        self.updateprefixes()

        self.something = None
    def updateadmins(self):
        with open("data/servers.yml","r") as file:
            data = load(file)
            for this in data:
                try:
                    self.admins[str(this)] = data[this]["admins"]
                except KeyError:
                    pass
    def updateprefixes(self):
        with open("data/servers.yml","r") as file:
            data = load(file)
            for this in data:
                try:
                    self.prefixes[str(this)] = data[this]["prefix"]
                except KeyError:
                    pass
    async def on_message(self,message):
        # Cached prefix and message
        try:
            if not message.channel.is_private:
                prefix = self.prefixes[message.server.id]
            else:
                prefix = str(parser.get("Settings","defaultprefix"))
        except KeyError or AttributeError:
            self.updateprefixes()
            prefix = self.prefixes[message.server.id]

        messagestr = str(message.content).lower()

        if message.channel.is_private:
            try:
                itsk = False
                allowed = ["+ping","+help","ayybot.invitelink","ayybot.changeavatar"]
                for hm in allowed:
                    hm.replace("+",prefix)
                    if messagestr.startswith(hm):
                        itsk = True
                if itsk is True:
                    pass
                else:
                    return
            except UnboundLocalError:
                prefix = str(parser.get("Settings","defaultprefix"))
        if message.author.id == client.user.id:
            return
        if handler.isblacklisted(message.server,message.channel):
            return
        if not handler.serverexists(message.server):
            handler.serversetup(message.server)

        msglist = ["ping","help","help useful","help admin","help fun","hello","wiki","urban","define","avatar","games","uptme","credits"
                       "ban","unban","kick","vote start","vote end","playing","memes","role","cmd","roll","dice","decide","8ball","gif"
                       "cats","ayy","ayy lmao","wot","eval","exec","timetosec","download","status","pic","dlmanage"]

        if messagestr.startswith("ayybot."):
            stat.plusmsg()
            dont = 1
        else:
            dont = None
        ahem = str(message.content).lower()[len(prefix):]
        for mm in msglist:
            if dont != 1:
                if str(ahem).startswith(mm):
                    stat.plusmsg()
                    break

        if messagestr.startswith("ayybot."):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                # Shut down, even if in sleep mode
                if messagestr.startswith("ayybot.kill"):
                    await client.send_message(message.channel, "**DED**")
                    print(str("{msg} by {usr}, quitting".format(msg=message.content,usr=message.author)))
                    logdis(message,type="message")
                    exit()
                # Reloads settings.ini
                elif messagestr.startswith("ayybot.config.rl"):
                    parser.clear()
                    parser.read("settings.ini")
                    logdis("Reloaded configuration",type="write")
                    await client.send_message(message.channel, "Reloaded config")
                # Reloads whitelist
                elif messagestr.startswith("ayybot.admins.rl"):
                    self.updateadmins()
                    logdis("Reloaded admins list",type="write")
                    await client.send_message(message.channel, "Reloaded whitelist")
                elif messagestr.startswith("ayybot.prefix.rl"):
                    self.updateprefixes()
                    logdis("Reloaded prefixes",type="write")
                    await client.send_message(message.channel,"Reloaded prefix list")
                elif messagestr.startswith("ayybot.server.setup"):
                    if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                        handler.serversetup(message.server)
                        await client.send_message(message.channel, "Default server settings generated")
                elif messagestr.startswith("ayybot.settings"):
                    cut = message.content[len("ayybot.settings") + 1:].split()
                    if cut == "filterwords" or "filterspam" or "sayhi" or "logchannel":
                        handler.updatesettings(message.server,cut[0],cut[1])
                        await client.send_message(message.channel,"Value of {} changed to {}".format(cut[0],cut[1]))
                    else:
                        await client.send_message(message.channel,"{} could not be recognised as a valid server value".format(cut))
                        stat.pluswrongarg()
                elif messagestr.startswith("ayybot.blacklistchannel"):
                    cut = message.content[len("ayybot.blacklistchannel") + 1:]
                    handler.updatechannels(message.server,cut)
                    await client.send_message(message.channel,"Channel {} has been blacklisted".format(cut))
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.changeprefix"):
                    cut = message.content[len("ayybot.changeprefix") + 1:]
                    cut = message.content[len("ayybot.changeprefix") + 1:]
                    handler.changeprefix(message.server,cut)
                    self.updateprefixes()
                    await client.send_message(message.channel,"Prefix changed :ok:")
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.displaysettings"):
                    settings = handler.returnsettings(message.server)
                    await client.send_message(message.channel, """\
```Settings for current server:

Blacklisted channels: {}
Custom commands: {}
Spam filter: {}
Word filter: {}
Log channel: {}
Number of admins: {}
Prefix: {}```""".format(settings["blacklisted"],settings["customcmds"],bool(settings["filterspam"]),bool(settings["filterwords"]),settings["logchannel"],len(settings["admins"]),settings["prefix"]))
                elif messagestr.startswith("ayybot.admins add"):
                    if len(message.mentions) > 5:
                        await client.send_message(message.channel,"Too muchhh!\nSeriously, up to 5 at a time")
                        stat.pluswrongarg()
                        return
                    for ment in message.mentions:
                            cut = message.content[len("ayybot.admins add") + 1:]
                            handler.updateadmins(message.server,ment)
                            await client.send_message(message.channel,":ok:".format(ment.name))
                    self.updateadmins()
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.admins remove"):
                    if len(message.mentions) > 5:
                        await client.send_message(message.channel,"Too muchhh!\nSeriously, up to 5 at a time")
                        stat.pluswrongarg()
                        return
                    for ment in message.mentions:
                            cut = message.content[len("ayybot.admins remove") + 1:]
                            handler.removeadmin(message.server,ment)
                            await client.send_message(message.channel,":ok:".format(ment.name))
                    self.updateadmins()
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.admins list"):
                    self.updateadmins()
                    admins = handler.returnwhitelisted(message.server)
                    final = ""
                    for this1 in admins:
                        user = discord.utils.find(lambda user: user.id == this1, message.channel.server.members)
                        final += "\n- {}".format(user.name)
                    await client.send_message(message.channel,"Admins :" + final)
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                # check for ayybot.sleep/wake before (possibly) quiting out of on_message
                elif messagestr.startswith("ayybot.info"):
                    await client.send_message(message.channel,str(infomsg).format(__version__,discord.__version__))
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.invitelink"):
                    if parser.get("Credentials","applicationid") is None:
                        return
                    if not message.channel.is_private:
                        await client.send_message(message.channel,"```I've sent you a private message!```")
                    await client.send_message(message.author, "Here is your link! https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions=0".format(parser.get("Credentials","applicationid")))
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")
                elif messagestr.startswith("ayybot.leaveserver"):
                    if message.author.id == ownerid:
                        await client.send_message(message.channel,"Bai. *leaves the sever*")
                        await client.leave_server(message.channel.server)
                        stat.plusleftserver()
                        print(str("{} by {}".format(message.content,message.author)))
                        logdis("Left {}".format(message.server.name),type="write")
                elif (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                    msg6 = str(message.content[7:])
                    if msg6 == "sleep":
                        if handler.issleeping(message.server):
                            return
                        handler.setsleeping(message.server,1)
                        await client.send_message(message.channel,"Now sleeping...")
                        print("Saved sleeping for server {}".format(message.server.name))
                    elif msg6 == "wake" and handler.issleeping(message.server) is True:
                        handler.setsleeping(message.server,0)
                        await client.send_message(message.channel,"**I'm BACK MFS**")
                        stat.plusslept()
                        print("Returned to normal on server {}".format(message.server.name))
            else:
                logdis(message.content+"| denied: incorrect permissions",type="write")
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                print(message.content+"| denied: incorrect permissions")
                stat.pluswrongperms()
        # Just a conversation thingie
        for um in message.mentions:
            if client.user.id == um.id:
                cutmsg = message.content[(len(client.user.id) + 4):]
                # 1.
                for thing in conversation:
                    if cutmsg.startswith(thing):
                        this = conversation.get(thing)
                        await client.send_message(message.channel, "<@" + message.author.id + "> " + this)
                # 2.
                if cutmsg.lower().startswith("are you there"):
                    if handler.issleeping(message.server) is False:
                        await client.send_message(message.channel,"<@" + message.author.id + "> I'm awake, what is it?")
                    else:
                        await client.send_message(message.channel,"<@" + message.author.id + "> I'm sleeping :sleeping:")
                if handler.issleeping(message.server) is False:
                    if cutmsg.lower().startswith("how are you"):
                        if message.author.id == ownerid:
                            await client.send_message(message.channel,"<@" + message.author.id + "> I'm fine, thanks")
                        else:
                            await client.send_message(message.channel,"<@" + message.author.id + "> eh")
                    elif cutmsg.lower().startswith("say"):
                        await client.send_message(message.channel,cutmsg[4:],tts=True)
                    elif "prefix" in cutmsg.lower():
                        await client.send_message(message.channel,"Prefix for this server is {}".format(str(prefix)))
        # Checks if put to sleep (is_private just to avoid problems)
        if not message.channel.is_private:
            if handler.issleeping(message.server) is True:
                return
            # Spam and swearing check
            if handler.needwordfilter(message.server):
                if (swearing.check(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                    await client.delete_message(message)
                    if parser.getboolean("Settings","logchannel") is not False:
                        logchannel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), message.channel.server.channels)
                        await client.send_message(logchannel, "```{}'s message was (not) filtered : swearing \n{}```".format(message.author.name,message.content))
                    print("{}'s message was (not) filtered : swearing".format(message.author.name))
            if handler.needspamfilter(message.server):
                if (spam.check(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                    await client.delete_message(message)
                    if parser.getboolean("Settings","logchannel") is not False:
                        logchannel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), message.channel.server.channels)
                        await client.send_message(logchannel, "```{}'s message was filtered : spam\n{}```".format(message.author.name,message.content))
                    print("{}'s message was filtered : spam".format(message.author.name))
        # Commands from config.py
        for onething in customcmd.keys():
            if message.content.lower().startswith(onething.replace("+",prefix)):
                print(onething.replace("+",prefix))
                second = customcmd.get(str(onething))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
                await client.send_message(message.channel, str(second).format(usr=message.author.id))
                return
        # Server custom commands
        if not message.channel.is_private:
            for one in handler.returncommands(message.server):
                if str(message.content).startswith(str(one)):
                    await client.send_message(message.channel, str(cmdlist.get(one)))
                    print(str("{} by {}".format(message.content,message.author)))
                    logdis(message,type="message")

        # Help commands
        if messagestr.startswith(prefix+"help"):
            if not message.channel.is_private:
                if (int(time.time()) - int(Timeutil.getlast()) < parser.getint("Settings","helpdelay")) and ((message.author.id != ownerid) or (message.author.name not in self.admins[message.server.id])):
                    return
            if "here" in messagestr:
                receiver = message.channel
            else:
                receiver = message.author
                if not messagestr == prefix+"help" and not message.channel.is_private:
                    await client.send_message(message.channel,"```I've sent you a private message!```")

            if messagestr.startswith(prefix+"help useful"):
                await client.send_message(receiver, "**`Help, useful commands:`**\n```" + helpmsg1.replace("+",prefix) + "```")
                Timeutil.setlast()
                stat.plushelpcommand()
            elif messagestr.startswith(prefix+"help admin"):
                await client.send_message(receiver, "**`Help, admin commands:`**\n```" + adminmsg.replace("+",prefix) + "```")
                Timeutil.setlast()
                stat.plushelpcommand()
            elif messagestr.startswith(prefix+"help fun"):
                await client.send_message(receiver, "**`Help, fun commands:`**\n```" + jokemsg.replace("+",prefix) + "```")
                Timeutil.setlast()
                stat.plushelpcommand()
            elif messagestr.startswith(prefix+"help meme") or messagestr.startswith(prefix+"help memes"):
                await client.send_message(receiver, "**`Help, meme list:`**\n```" + memelist.replace("+",prefix) + "```")
                Timeutil.setlast()
                stat.plushelpcommand()
            elif messagestr.startswith(prefix+"help all"):
                await client.send_message(receiver, "Here is a list of all available commands:\n`Help, useful commands:`\n```" + helpmsg1.replace("+",prefix) + "```")
                await client.send_message(receiver, "`Help, admin commands:`\n```" + adminmsg.replace("+",prefix) + "```")
                await client.send_message(receiver, "`Help, fun commands:`\n```" + jokemsg.replace("+",prefix) + "```")
                await client.send_message(receiver, "`Help, meme list:`\n```" + memelist.replace("+",prefix) + "```")
                # Wont work, is too long for Discord.
                #await client.send_message(receiver, "**Help:**\n*1. Useful commands*\n" + helpmsg1.replace("+",prefix) + "*2. Fun commands*\n" + jokemsg.replace("+",prefix) + "*3.Admin commands*\n" + adminmsg.replace("+",prefix) + "*4. Meme commands*\n" + memelist.replace("+",prefix))
                Timeutil.setlast()
                stat.plushelpcommand()
            elif messagestr.startswith(prefix+"help"):
                await client.send_message(message.channel, "Available:\n`{}help useful`, `{}help admin`, `{}help fun`, `{}help meme`\n`Full command list can be found at https://github.com/DefaltSimon/AyyBot/wiki/Commands-list`".format(prefix,prefix,prefix,prefix))
                Timeutil.setlast()
                stat.plushelpcommand()
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        elif messagestr.startswith(prefix+"ping"):
            cut = str(message.content)[len(prefix+"ping "):]
            if cut == "" or cut.startswith(" "):
                address = "http://google.com"
            else:
                if not cut.startswith("http://"):
                    address = "http://" + cut
                else:
                    address = cut
            try:
                timest = time.time()
                urllib.request.urlopen(address)
                end = str(round(time.time() - timest,3))
            except urllib.request.URLError:
                await client.send_message(message.channel,"Could not ping (Does not exist)")
                return
            except urllib.request.HTTPError:
                await client.send_message(message.channel,"Could not ping (403: Forbidden)")
                return
            await client.send_message(message.channel,"Pong! **" + end + " ms**")
            urllib.request.urlcleanup()
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
            stat.plusoneping()
        elif messagestr.startswith(prefix+"hello"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel,"Hi, <@" + message.author.id + ">")
            else:
                for dis in message.mentions:
                    await client.send_message(message.channel,"Hi, <@" + dis.id + ">")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # They see me rollin'
        elif messagestr.startswith(prefix+"roll"):
            msg5 = message.content.lower()[len(prefix)+len("roll")+1:]
            await client.send_message(message.channel, "<@" + message.author.id + "> rolled " + str(randint(0, int(msg5))))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Dice, 1 - 6
        elif messagestr.startswith(prefix+"dice"):
            await client.send_message(message.channel, "<@" + message.author.id + "> got " + str(randint(1,6)))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Cats are cute
        elif messagestr.startswith(prefix+"cats"):
            await client.send_file(message.channel, "data/images/cattypo.gif")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
            stat.plusimagesent()
        # Kappa
        elif messagestr.startswith(prefix+"kappa"):
            await client.send_file(message.channel,"data/images/kappasmall.png")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
            stat.plusimagesent()
        # Lists all members in current server
        elif messagestr.startswith(prefix+"members"):
            await client.send_typing(message.channel)
            count = 0
            members = ''
            for mem in message.channel.server.members:
                count += 1
                mem = str(mem.name)
                if count != 1:
                    members += ', '
                members += mem
            final = "Total : **{}**".format(count)
            if count > 20:
                await client.send_message(message.channel, final)
                return
            await client.send_message(message.channel, "**Members:**\n`" + members + "`\n" + final)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Uptime
        elif messagestr.startswith(prefix+"uptime"):
            timeelapsed = time.time() - Timeutil.getstartup()
            converted = Timeutil.gettime(timeelapsed).split(":")
            await client.send_message(message.channel, "I've been running for **{}** days, **{}** hours, **{}** minutes and **{}** seconds ".format(converted[0],converted[1],converted[2],converted[3]))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Returns mentioned user's avatar, or if no mention present, yours.
        elif messagestr.startswith(prefix+"avatar"):
            if len(message.mentions) > 0:
                for user in list(message.mentions):
                    print(user)
                    if user.avatar_url != "":
                        await client.send_message(message.channel, "**" + user.name + "**'s avatar: " + user.avatar_url)
                    else:
                        await client.send_message(message.channel, "**" + user.name + "** doesn't have an avatar :rolling_eyes:")
            else:
                await client.send_message(message.channel,"**" + message.author.name + "**'s avatar: " + message.author.avatar_url)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Decides between two or more words
        elif messagestr.startswith(prefix+"decide"):
            msg3 = str(message.content.lower()[len(prefix)+len("decide")+1:]).split()
            if randint(1,2) == 1:
                await client.send_message(message.channel, "<@" + message.author.id + "> " + "\nI have decided: " + msg3[0])
            else:
                await client.send_message(message.channel, "<@" + message.author.id + "> I have decided: " + msg3[1])
                logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Answers your question - 8ball style
        elif messagestr.startswith(prefix+"8ball"):
            await client.send_typing(message.channel)
            msg6 = str(message.content[len(prefix)+len("8ball")+1:])
            answer = eightball[randint(1,len(eightball))]
            await client.send_message(message.channel,"<@" + message.author.id + "> asked : " + msg6 + "\n**" + answer + "**")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a gif matching the name from Giphy (!gif <name>)
        elif messagestr.startswith(prefix+"gif"):
            msg2 = str(message.content.lower()[len(prefix)+len("gif")+1:])
            img = str(translate(msg2))
            await client.send_message(message.channel, "<@" + message.author.id + "> " + img)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
            stat.plusimagesent()
        elif messagestr.startswith(prefix+"randomgif"):
            await client.send_message(message.channel,gif(str(screensaver)))
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
            stat.plusimagesent()
        # Returns user info (name,id,discriminator and avatar url)
        elif messagestr.startswith(prefix+"user"):
            await client.send_typing(message.channel)
            if len(message.mentions) > 0:
                for user in message.mentions:
                    name = user.name
                    uid = user.id
                    discrim = user.discriminator
                    avatar = user.avatar_url
                    creationtime = user.created_at
                    if user.bot is True:
                        isbot = "Yes"
                    else:
                        isbot = "No"
                    final = "```javascript\nName: " + name + "\nId: " + uid + "\nDiscriminator: #" + discrim + "\nBot account: " + isbot + "\nAvatar url: " + avatar + "\nCreation date: " + str(creationtime) + " UTC" +"```"
                    await client.send_message(message.channel,final)
            else:
                await client.send_message(message.channel, "Please mention someone to display their info")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"games"):
            if parser.getboolean("Settings","monitorgames") is False:
                await client.send_message(message.channel,":no_entry_sign: This feature was disabled by the owner.")
                return
            if len(message.mentions) != 0:
                games = game.getplayer(user=message.mentions[0].id)
            else:
                games = game.getplayer(user=message.author.id)
            if message.channel.is_private:
                if games is None:
                    await client.send_message(message.author, "```No games found```")
                else:
                    full = ""
                    for that in games.keys():
                        if that == "username":
                            continue
                        a, b = divmod(int(round(games[that]/60,0)),60)
                        full += "{} : {} hours, {} minutes\n".format(that,a,b)
                    await client.send_message(message.author,"<@" + message.author.id + "> Played:\n```" + full + "```")
            else:
                if games is None:
                    await client.send_message(message.channel, "No games found```")
                else:
                    full = ""
                    for that in games.keys():
                        if that == "username":
                            break
                        a, b = divmod(int(round(float(games[that])/60,0)),60)
                        full += "{} : {} hours, {} minutes\n".format(that,a,b)
                    await client.send_message(message.channel,"<@" + message.author.id + "> {} played:\n```".format(message.author.name) + full + "```")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a random quote
        elif messagestr.startswith(prefix+"quote"):
            await client.delete_message(message)
            answer = quotes[randint(1,len(quotes))]
            await client.send_message(message.channel,answer)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # For managing roles
        elif messagestr.startswith(prefix+"role"):
            try:
                if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                    if len(message.mentions) == 0:
                        await client.send_message(message.channel,"Please mention someone")
                        return
                    elif len(message.mentions) >= 2:
                        await client.send_message(message.channel, "Please mention only one person at a time")
                        return
                    for ye in message.mentions:
                        user = discord.utils.find(lambda member: member.name == ye.name, message.mentions)
                        break
                    if messagestr.startswith(prefix+"role " +  "add "):
                        gotrole = str(message.content[len(prefix + "role " + "add "):]).split("<")[0].strip()
                        role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                        await client.add_roles(user,role)
                        await client.send_message(message.channel,":ok:")
                    elif messagestr.startswith(prefix+"role " +  "remove "):
                        gotrole = str(message.content[len(prefix + "role " + "remove "):]).split("<")[0].strip()
                        role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                        await client.remove_roles(user,role)
                        await client.send_message(message.channel,":ok:")
                    elif messagestr.startswith(prefix+"role " +  "replacewith "):
                        gotrole = str(message.content[len(prefix + "role replacewith "):]).split("<")[0].strip()
                        role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                        await client.replace_roles(user,role)
                        await client.send_message(message.channel,":ok:")
                    logdis(message,type="message")
                    print(str("{} by {}".format(message.content,message.author)))
                else:
                    logdis(message.content+"| denied: incorrect permissions",type="write")
                    await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                    print(message.content+"| denied: incorrect permissions")
            except discord.errors.Forbidden:
                await client.send_message(message.channel,":no_entry_sign: I do not have the correct permissions (need \"Manage permissions\")")
                print(str("{} by {}, but did not have correct permissions".format(message.content,message.author)))
                logdis(message,type="message")
        # Gets something from Wikipedia
        elif messagestr.startswith(prefix+"wiki") or messagestr.startswith(prefix+"define"):
            if messagestr.startswith(prefix+"wiki"):
                cut = str(messagestr[len(prefix)+len("wiki "):])
            elif messagestr.startswith(prefix+"define"):
                cut = str(messagestr[len(prefix)+len("define "):])
            try:
                await client.send_typing(message.channel)
                wikipage = wikipedia.summary(cut,sentences=parser.get("Settings","wikisentences"),auto_suggest=True)
                await client.send_message(message.channel,"*Wikipedia definition for* **" + cut + "** *:*\n" + wikipage)
            except wikipedia.exceptions.PageError:
                await client.send_message(message.channel,"No definitions found")
            except wikipedia.exceptions.DisambiguationError:
                await client.send_message(message.channel,"There are multiple definitions of {}, please be more specific".format(cut))
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Gets urban dictionary term
        elif messagestr.startswith(prefix+"urban"):
            await client.send_typing(message.channel)
            query = str(messagestr[len(prefix)+len("urban")+1:])
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(query))
            purehtml = BeautifulSoup(define.content, "html.parser")
            convertedhtml = purehtml.find("div",attrs={"class":"meaning"}).text
            if convertedhtml is None or str(convertedhtml).startswith("There"):
                await client.send_message(message.channel,"There are no *urban* definitions for {}".format(query))
                return
            await client.send_message(message.channel,"*Urban definition for* **" + messagestr[7:] + "** *:*" + convertedhtml)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"sskj"):
            await client.send_typing(message.channel)
            query = str(messagestr[len(prefix+"sskj "):])
            req = requests.get("http://bos.zrc-sazu.si/cgi/a03.exe?name=sskj_testa&expression={}&hs=1".format(query))
            purehtml = BeautifulSoup(req.content,"html.parser")
            gotit = purehtml.find("li",attrs={"class":"nounderline"}).find("i").text
            if str(gotit).endswith(":") or str(gotit).endswith(","):
                gotit = gotit[:-1]
            print(gotit)
            if gotit is None:
                await client.send_message(message.channel,"No definition for " + query)
            else:
                await client.send_message(message.channel,"Sskj definition for **{}**:\n".format(query) + str(gotit))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # User kick
        elif messagestr.startswith(prefix+"kick"):
            if ((message.author.id == ownerid) or (message.author.id in self.admins[message.server.id])) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.kick(user)
                    await client.send_message(message.channel,"User " + user.name + " has been kicked.")
                    logdis("User {} has been kicked from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
            else:
                if len(message.mentions) == 0 and message.author.id in self.admins[message.server.id]:
                    await client.send_message(message.channel,"Please mention somebody")
                elif len(message.mentions) != 0:
                    logdis(message.content+"| denied: incorrect permissions",type="write")
                    await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                    print(message.content+"| denied: incorrect permissions")
        # User ban
        elif messagestr.startswith(prefix+"ban"):
            if ((message.author.id == ownerid) or (message.author.id in self.admins[message.server.id])) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.ban(user)
                    await client.send_message(message.channel,"User " + user.name + " has been banned from this server.")
                    logdis("User {} has been banned from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
            else:
                if len(message.mentions) == 0 and message.author.id in self.admins[message.server.id]:
                    await client.send_message(message.channel,"Please mention somebody")
                elif len(message.mentions) != 0:
                    logdis(message.content+"| denied: incorrect permissions",type="write")
                    await client.send_message(message.channel,"You do not have the permission to use this feature.")
                    print(message.content+"| denied: incorrect permissions")
        # User unban
        elif messagestr.startswith(prefix+"unban"):
            if ((message.author.id == ownerid) or (message.author.id in self.admins[message.server.id])) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.unban(user)
                    await client.send_message(message.channel,"User " + user.name + " has been unbanned.")
                    logdis("User {} has been unbanned from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
            else:
                if len(message.mentions) == 0 and message.author.id in self.admins[message.server.id]:
                    await client.send_message(message.channel,"Please mention somebody")
                elif len(message.mentions) != 0:
                    logdis(message.content+"| denied: incorrect permissions",type="write")
                    await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                    print(message.content+"| denied: incorrect permissions")
        # Adds custom commands
        elif messagestr.startswith(prefix+"cmd"):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                if messagestr.startswith(prefix+"cmd add"):
                    try:
                        cut = str(message.content)[len(prefix+"cmd add "):].split("|")
                        handler.updatecommand(message.server,cut[0],cut[1])
                        await client.send_message(message.channel,":ok:")
                    except KeyError:
                        await client.send_message(message.channel,":no_entry_sign: Wrong args, separate trigger and response with |")
                        stat.pluswrongarg()
                    except IndexError:
                        await client.send_message(message.channel,":no_entry_sign: Wrong args, separate trigger and response with |")
                        stat.pluswrongarg()
                elif messagestr.startswith(prefix+"cmd remove"):
                    cut = str(message.content)[len(prefix+"cmd remove "):]
                    handler.removecommand(message.server,cut)
                    await client.send_message(message.channel,":ok:")
                elif messagestr.startswith(prefix+"cmd list"):
                    cut = str(message.content)[len(prefix+"cmd list "):]
                    comm = handler.returncommands(message.server)
                    final = ""
                    for this in comm.keys():
                        print(this)
                        final += "\n{} - {}".format(this,comm[this])
                    if not final:
                        await client.send_message(message.channel,"No commands registered for this server ")
                    await client.send_message(message.channel,"*Command list:*" + final)
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
            else:
                logdis(message.content+"| denied: incorrect permissions",type="write")
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                print(message.content+"| denied: incorrect permissions")
        # Changes "playing 'something'" status
        elif messagestr.startswith(prefix+"playing"):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                cutstr = message.content[len(prefix)+len("playing")+1:]
                try:
                    status = SetStatus()
                    await status.set(cutstr)
                    await client.send_message(message.channel,"Status changed :ok:")
                except AssertionError:
                    pass
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
            else:
                logdis(message.content+"| denied: incorrect permissions",type="write")
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                print(message.content+"| denied: incorrect permissions")
        # Starts a vote
        elif messagestr.startswith(prefix+"vote start"):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                cutstr = message.content[len(prefix)+len("vote start")+1:]
                if vote.getcontent() is not None:
                    await client.send_message(message.channel,"Vote already in progress")
                    return
                vote.create(str(message.author.name),cutstr.strip("(").strip(")").split('+')[1])
                one = 0
                list1 = ""
                name = cutstr.strip("(").strip(")").split('++')
                for this in name[1].split('""'):
                    list1 = list1 + "" + str(one+1) + ". " + this + "\n"
                    one += 1
                await client.send_message(message.channel,"Vote started: \n{}\n{}".format(name[0],list1))
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
            else:
                logdis(message.content+"| denied: incorrect permissions",type="write")
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
                print(message.content+"| denied: incorrect permissions")
        # Ends the voting
        elif messagestr.startswith(prefix+"vote end"):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                if vote.getcontent() is not None:
                    one = 0
                    endstr = "Voting has ended. Results: \n"
                    for this in vote.getcontent():
                        endstr += "{} :    *{} votes*\n".format(this,vote.returnvotes()[one])
                        one += 1
                    await client.send_message(message.channel,endstr)
                    vote.reset()
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        # For everybody to vote
        elif messagestr.startswith(prefix+"vote"):
            for this in vote.voters:
                if message.author.id == this:
                    await client.send_message(message.channel,"<@" + message.author.id + "> Cheater! :smile:")
                    return
            vote.countone(messagestr[6:],voter=message.author.id)
            stat.plusonevote()
        elif messagestr.startswith(prefix+"status") or messagestr.startswith("ayybot.status"):
            channels = client.get_all_channels()
            fchannels = 0
            for this in channels:
                fchannels += 1

            members = client.get_all_members()
            fmembers = 0
            for this in members:
                fmembers += 1

            servers = client.servers
            fservers = 0
            for this in servers:
                fservers += 1

            del channels
            del members
            del servers
            await client.send_message(message.channel,"```python\nUsers: {}\nServers: {}\nChannels: {}```".format(fmembers,fservers,fchannels))
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"stats") or messagestr.startswith("ayybot.stats"):
            with open("plugins/stats.yml","r+") as file:
                file = load(file)
                mcount = file["msgcount"]
                downsize = str( round(int(stat.sizeofdown())/1024/1024/1024,3) )
                wrongargc = file["wrongargcount"]
                timesleft = file["serversleft"]
                timesslept = file["timesslept"]
                wrongpermc = file["wrongpermscount"]
                pplhelp = file["peoplehelped"]
                imgc = file["imagessent"]
                votesc = file["votesgot"]
                pings = file["timespinged"]
            onetosend = "Stats:\n```python\n{} messages sent\n{} people yelled at because of wrong args\n{} people denied because of wrong permissions\n{} people helped\n{} votes got\n{} times slept\n{} servers left\n{} images sent\n{} mb of pictures downloaded\n{} sites pinged```".format(mcount,wrongargc,wrongpermc,pplhelp,votesc,timesslept,timesleft,imgc,downsize,pings)
            await client.send_message(message.channel,onetosend)
        elif messagestr.startswith(prefix+"eval") or messagestr.startswith(prefix+"calc"):
            done = eval(message.content[len(prefix+"eval "):])
            await client.send_message(message.channel,"```python\nResult= " + str(done) + "```")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"exec"):
            if (message.author.id == ownerid) or (message.author.id in self.admins[message.server.id]):
                cut = str(message.content[len(prefix+"exec "):]).strip("```")
                if cut.startswith("python"):
                    cut = str(cut[len("python "):])
                dangerous = False
                blacklisted = ["open","open(","sys","import sys","daemon","asyncio"]
                for this in blacklisted:
                    if str(cut).find(this) is not -1:
                        dangerous = True
                        break
                if dangerous and message.author.id != ownerid:
                    logdis(message,type="message")
                    print(str("Code executed by {}| Denied: potentially dangerous".format(message.author)))
                    return
                tajm = time.time()
                buffer = StringIO()
                sys.stdout = buffer
                try:
                    exec(cut)
                except Exception as e:
                    sys.stdout = sys.__stdout__
                    timetook = time.time() - tajm
                    await client.send_message(message.channel,"You done goofed, but here's the output anyway: ({} s)\n```".format(timetook) + str(e) + "```")
                    return
                sys.stdout = sys.__stdout__
                timetook = time.time() - tajm
                await client.send_message(message.channel,":ok:\nExecution took **{} sec**.\n*Output:*\n```python\n".format(timetook) + str(buffer.getvalue()) + "```")
                logdis(message,type="message")
                print(str("Code exeuted by {}".format(message.author)))
            else:
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature.")
        elif messagestr.startswith(prefix+"download"):
            if message.author.id == ownerid:
                cut = str(message.content[len(prefix + "download "):])
                if cut.endswith(".jpg") or cut.endswith(".jpeg") or cut.endswith(".png") or cut.endswith(".gif"):
                    import urllib.request as req
                    import os
                    filename = cut[cut.rfind("/")+1:]
                    img = req.urlopen(cut)
                    with open(str("downloads/" + filename), 'wb') as image:
                        image.write(img.read())
                    await client.send_message(message.channel,"File has been downloaded. (" + filename + ")")
                else:
                    await client.send_message(message.channel,"The link you provided is not a picture. :frowning2:")
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
            else:
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature (must be the owner)")
                print(str("{} by {} | denied: not admin".format(message.content,message.author)))
                logdis(message,type="message")
        elif messagestr.startswith("ayybot.changeavatar"):
            if message.author.id == ownerid:
                cut = str(message.content[len("ayybot.changeavatar "):]).split("|")
                if cut[0] == "file":
                    try:
                        avatar2 = open(cut[1],"rb").read()
                        await client.edit_profile(avatar=avatar2)
                        await client.send_message(message.channel,":ok:")
                    except FileNotFoundError:
                        await client.send_message(message.channel,"File not found :frowning:")
                        return
                elif cut[0] == ("www" or "download" or "link" or "web" or "get"):
                    cut = cut[1]
                    if cut.endswith(".jpg") or cut.endswith(".jpeg") or cut.endswith(".png"):
                        import urllib.request as req
                        img = req.urlopen(cut)
                        filename = cut[cut.rfind("/")+1:]
                        await client.edit_profile(avatar=img.read())
                        await client.send_message(message.channel,":ok:")
                    else:
                        await client.send_message(message.channel,"The link you provided is not a picture. :frowning2: (supported: .jpg/.jpeg/.png)")
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
            else:
                await client.send_message(message.channel,":no_entry_sign: You do not have the permission to use this feature (must be the owner)")
                print(str("{} by {} |denied: not admin".format(message.content,message.author)))
                logdis(message,type="message")
        # Renames files for use of +pic
        elif messagestr.startswith(prefix+"dlmanage"):
            await client.send_message(message.channel,"Current download directory: \n```python\n" + str(listdir("downloads")) + "```\n`Size: {}`\n`Reply with -rename <filename>|<whattorenameit> to rename the file`\n`Reply with -delete <filename> to delete the file`\n`Reply with -cancel to cancel your actions`".format(str(round(int(stat.sizeofdown())/1024/1024/1024,3)) + "mb" ))
            self.something = None
            def checkthis(msg):
                if str(msg.content).startswith("-rename"):
                    if str(msg.content).endswith(".jpg") or str(msg.content).endswith(".jpeg") or str(msg.content).endswith(".png") or str(msg.content).endswith(".gif"):
                        self.something = 1
                        return True
                    else:
                        return False

                elif str(msg.content).startswith("-delete") or str(msg.content).startswith("-remove"):
                    if str(msg.content).endswith(".jpg") or str(msg.content).endswith(".jpeg") or str(msg.content).endswith(".png") or str(msg.content).endswith(".gif"):
                        self.something = 2
                        return True
                    else:
                        return False

                elif str(msg.content).startswith("-cancel"):
                    self.something = 3
                    return True
                else:
                    return False

            followup = await client.wait_for_message(author=message.author,channel=message.channel,timeout=25,check=checkthis)
            if followup is None:
                await client.send_message(message.channel,"You ran out of time :upside_down:")
            if self.something == 1:
                try:
                    cut = str(str(followup.content)[len("-rename "):]).split("|")
                except AttributeError:
                    await client.send_message(message.channel,"An error occured, please check your args and try again")
                try:
                    rename("downloads/"+cut[0],"downloads/"+cut[1])
                    await client.send_message(message.channel,"File renamed successfully")
                except FileNotFoundError:
                    await client.send_message(message.channel,"File does not exist :no_entry_sign:")
            elif self.something == 2:
                try:
                    cut = str("downloads/"+str(followup.content)[len("-remove "):])
                    print(cut)
                except AttributeError:
                    await client.send_message(message.channel,"An error occured, please check your args and try again")
                try:
                    from os import remove
                    remove(cut)
                    await client.send_message(message.channel,"File has been deleted successfully")
                except FileNotFoundError:
                    await client.send_message(message.channel,"File does not exist :no_entry_sign:")
            elif self.something == 3:
                await client.send_message(message.channel,"Okay :upside_down:")
        # Sends downloaded pictures
        elif messagestr.startswith(prefix+"pic"):
            cut = str(message.content).lower()[len(prefix+"pic "):]
            files = listdir("downloads")
            setone = None
            for this in files:
                if cut == this[:str(this).rfind(".")]:
                    setone = this
                    break
            await client.send_file(message.channel,fp=str("downloads/"+str(setone)))
        # Ignore, just some tests and fun commands
        elif messagestr.startswith(prefix+"timetosec"):
            cut = str(message.content[len(prefix+"timetosec "):]).split(".")
            if cut[1] == "sec":
                await client.send_message(message.channel,"rly.")
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
                return
            elif cut[1] == "min":
                timerem = int(cut[0]) * 60
            elif cut[1] == "hr":
                timerem = int(cut[0]) * 360
            elif cut[1] == "day":
                timerem = int(cut[0]) * 8640
            elif cut[1] == "week":
                timerem = int(cut[0]) * 60480
            elif cut[1] == "month":
                timerem = int(cut[0]) * 259200
            elif cut[1] == "year":
                timerem = int(cut[0]) * 3153600
            else:
                return
            await client.send_message(message.channel,cut[0] + " " + cut[1] + " in seconds: *" + str(timerem) + "*")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")

# Events
ayybot = AyyBot()
@client.event
async def on_message(message):
    #try:
    await ayybot.on_message(message)
    #except discord.InvalidArgument:
    #    print("Error : discord.InvalidArgument")
    #except discord.ClientException:
    #    print("Error : discord.ClientException")
    #except discord.errors.HTTPException:
    #    print("Error : discord.errors.HTTPException")

@client.async_event
async def on_member_join(member):
    if (parser.getboolean("Settings","disableallwelcomes") is False) and handler.issleeping(member.server) is False and handler.shouldsayhi(member.server) is True:
        await client.send_message(member.server, 'Welcome to the server, {0}'.format(member.name))
        print("{} joined the server".format(member.name))
        logdis(message="{} joined the server {}".format(member.name,member.server.name),type="write")

@client.async_event
async def on_message_delete(message):
    if parser.getboolean("Settings","disablealllogging") is False and handler.issleeping(message.server) is False and handler.disabledlogging(message.server):
        messagestr = str(message.content)
        channel = discord.utils.find(lambda channel: channel.name == handler.returnlogch(message.server), message.channel.server.channels)
        if message.channel == channel or messagestr.startswith("!") or message.author.name == client.user.name:
            return
        await client.send_message(channel,"```User {} deleted his/her message:\n{}\nin channel: #{}```".format(message.author,messagestr,message.channel.name))

@client.async_event
async def on_message_edit(before,after):
    if parser.getboolean("Settings","disablealllogging") is not True and handler.issleeping(before.server) is False or handler.disabledlogging(before.server):
        msgbefore = str(before.content)
        msgafter = str(after.content)
        if msgbefore == msgafter:
            return
        logchannel = discord.utils.find(lambda channel: channel.name == handler.returnlogch(before.server), before.channel.server.channels)
        if before.channel == logchannel:
            return
        if msgbefore.startswith("!") or msgafter.startswith("!"):
            return
        try:
            await client.send_message(logchannel,"```User {} edited his message:\nBefore: {}\nAfter: {}\nin channel: #{}```".format(before.author,msgbefore,msgafter,before.channel.name))
        except discord.errors.InvalidArgument:
            pass


@client.async_event
async def on_member_update(before,after):
    # ayybot.sleep does not impact this feature!
    # However, it can be disabled in settings.ini
    if parser.getboolean("Settings","monitorgames") is False:
        return
    if before.name in game.cooldown:
            if time.time() - game.cooldown[before.name] < 0.20:
                return
    if ((game.hasplayed(before.name)) or before.game is None) and after.game is not None:
        game.lasttime[before.name] = time.time()
    elif (after.game is None and before.game is not None) and game.hasplayed(before.name) is True:
        game.add(user=before.name,server=before.server,game=before.game.name,time1=time.time())
        game.lasttime[before.name] = None
    elif before.game != after.game:
        game.add(user=before.name,server=before.server,game=before.game.name,time1=time.time())
        game.lasttime[before.name] = time.time()


@client.async_event
async def on_ready():
    print("connected as")
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('\nNow running...\n')
    # sets status
    if parser.get("Settings","status") is not "False":
        try:
            status = SetStatus()
            await status.startup()
        except AssertionError:
            pass

# Starts the bot
@asyncio.coroutine
def start():
    print("Connecting... ",end="")
    # yield from client.login(parser.get("Credentials","mail"),parser.get("Credentials","password"))
    yield from client.login(parser.get("Credentials","token"))
    yield from client.connect()

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(start())
except:
    print("Exception raised, logging out.")
    loop.run_until_complete(client.logout())
finally:
    loop.close()
