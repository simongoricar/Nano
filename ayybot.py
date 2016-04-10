import discord,asyncio
import time,configparser,wikipedia,requests
from random import randint
from config import customcmd,eightball,helpmsg1,adminmsg,creditsmsg,jokemsg,memelist,quotes,conversation
from datetime import timedelta, datetime
from giphypop import translate
from bs4 import BeautifulSoup
from plugins import moderator,votebot,gametime

__author__ = 'DefaltSimon'
__version__ = '1.6.1'

class SetStatus:
    def __init__(self):
        pass
    async def startup(self):
        game = discord.Game(name=str(parser.get("Settings","status")))
        loop.create_task(client.change_status(game=game))
    async def set(self,game):
        game = discord.Game(name=str(game))
        loop.create_task(client.change_status(game=game))

class BotSleep:
    def __init__(self):
        self.state_sleep = 0
    def getstate(self):
        return bool(self.state_sleep)
    def sleep(self):
        self.state_sleep = 1
    def wake(self):
        self.state_sleep = 0

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
BotSleep = BotSleep()
Timeutil = TimeUtil()
parser = configparser.ConfigParser()

vote = votebot.Vote()
spam = moderator.SpamDetection()
swearing = moderator.Swearing()
game = gametime.GameCount()

parser.read("settings.ini")
ownerid = str(parser.get("Settings","ownerid"))
prefix = str(parser.get("Settings","prefix"))

# Write two newlines to data/log.txt
if parser.getboolean("Settings","WriteLogs") is True:
    with open('data/log.txt','a') as file:
        file.write("\n----- " + str(time.strftime("%Y-%m-%d %H:%M:%S", )) + " : startup -----\n")

def logdis(message,type):
    if parser.getboolean("Settings","WriteLogs") is True:
        if type == "message":
            with open('data/log.txt',"a") as file2:
                one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
                str2 = one + str(" : {msg} by {usr}\n".format(msg=message.content,usr=message.author))
                file2.write(str2)
        elif type == "write":
            with open('data/log.txt',"a") as file2:
                one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
                str2 = one + str(" : {}\n".format(message))
                file2.write(str2)

# Commands
class AyyBot:
    def __init__(self):
        self.whitelist = self.getwhitelist()
    def getwhitelist(self):
        with open("data/whitelist.txt","r") as file:
            lines = (line.rstrip() for line in file)
            lines = list(line for line in lines if line)
        return lines
    async def on_message(self,message):
        if message.author.id == client.user.id:
            return
        messagestr = str(message.content).lower()

        # Shut down, even if in sleep mode
        if messagestr.startswith("ayybot.kill"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                await client.send_message(message.channel, "**DED**")
                print(str("{msg} by {usr}, quitting".format(msg=message.content,usr=message.author)))
                logdis(message,type="message")
                exit()
            else:
                logdis(message,type="message")
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        # Reloads settings.ini
        elif messagestr.startswith("ayybot.config.reload"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                parser.clear()
                parser.read("settings.ini")
                logdis("Successfully reloaded configuration.",type="write")
                await client.send_message(message.channel, "Successfully reloaded config.")
        # Reloads whitelist
        elif messagestr.startswith("ayybot.whitelist.reload"):
            self.whitelist = self.getwhitelist()
            logdis("Successfully reloaded whitelist.",type="write")
            await client.send_message(message.channel, "Successfully reloaded whitelist.")
        # check for ayybot.sleep/wake before (possibly) quiting out of on_message
        elif (message.author.id == ownerid) or (message.author.name in self.whitelist):
            if messagestr.startswith("ayybot."):
                msg6 = str(message.content[7:])
                if msg6 == "sleep":
                    if BotSleep.getstate is True:
                        await client.send_message(message.channel,"No need m8, I was already sleeping.")
                        return
                    BotSleep.sleep()
                    await client.send_message(message.channel,"Now sleeping...")
                    print("Saved sleeping")
                elif msg6 == "wake" and BotSleep.getstate() is not False:
                    BotSleep.wake()
                    await client.send_message(message.channel,"**I'm BACK MFS**")
                    print("Returned to normal")
        # Checks if put to sleep
        if BotSleep.getstate() is True:
            return
        # Spam and swearing check
        if bool(parser.get("Settings", "filterwords")) is True:
            if (swearing.check(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                print("ok")
                await client.delete_message(message)
                if bool(parser.get("Settings","logchannel")) is not False:
                    logchannel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), message.channel.server.channels)
                    await client.send_message(logchannel, "```{}'s message was (not) filtered : swearing \n{}```".format(message.author.name,message.content))
                print("{}'s message was (not) filtered : swearing".format(message.author.name))
        if bool(parser.get("Settings", "filterspam")) is True:
            if (spam.check(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                await client.delete_message(message)
                if bool(parser.get("Settings","logchannel")) is not False:
                    logchannel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), message.channel.server.channels)
                    await client.send_message(logchannel, "```{}'s message was filtered : spam\n{}```".format(message.author.name,message.content))
                print("{}'s message was filtered : spam".format(message.author.name))
        # Commands from config.py
        for onething in customcmd.keys():
            if message.content.lower().startswith(onething.replace("+",prefix)):
                client.delete_message(message)
                second = customcmd.get(str(message.content.lower()))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
                await client.send_message(message.channel, str(second).format(usr=message.author.id))
                return
        # Commands in customcmds.txt
        with open("data/customcmds.txt","r") as disone:
            for disonea in disone.readlines():
                if disonea.strip() == "":
                    continue
                if messagestr.startswith((disonea.strip().split('()',maxsplit=2))[0]):
                    await client.send_message(message.channel,disonea.strip().split('()')[1])
                    logdis(message,type="message")
                    return
        # Just a conversation thingie
        for dis in message.mentions:
            if dis.id == client.user.id:
                cutmsg = message.content[(len(client.user.id) + 4):]
                # 1.
                for thing in conversation:
                    if cutmsg == thing:
                        this = conversation.get(thing)
                        await client.send_message(message.channel, "<@" + message.author.id + "> " + this)
                # 2.
                if cutmsg.lower().startswith("are you there"):
                    if BotSleep.getstate is False:
                        await client.send_message(message.channel,"<@" + message.author.id + "> I'm awake, what is it?")
                    elif BotSleep.getstate is True:
                        await client.send_message(message.channel,"<@" + message.author.id + "> I'm sleeping")
                elif cutmsg.lower().startswith("how are you"):
                    if message.author.id == ownerid:
                        await client.send_message(message.channel,"<@" + message.author.id + "> I'm fine, thanks")
                    else:
                        await client.send_message(message.channel,"<@" + message.author.id + "> eh")
                elif cutmsg.lower().startswith("say"):
                    await client.send_message(message.channel,cutmsg[4:],tts=True)
                elif "prefix" in cutmsg.lower():
                    await client.send_message(message.channel,"My prefix is {}".format(str(prefix)))
        # Help commands
        if messagestr.startswith(prefix+"help"):
            if (int(time.time()) - int(Timeutil.getlast()) < parser.getint("Settings","helpdelay")) and ((message.author.id != ownerid) or (message.author.name in self.whitelist)):
                return
            if "here" in messagestr:
                receiver = message.channel
            else:
                receiver = message.author

            if messagestr.startswith(prefix+"help useful") or messagestr == prefix+"help":
                await client.send_message(receiver, "**Help, useful commands:**\n" + helpmsg1.replace("+",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help admin"):
                await client.send_message(receiver, "**Help, admin commands:**\n" + adminmsg.replace("+",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help fun"):
                await client.send_message(receiver, "**Help, fun commands:**\n" + jokemsg.replace("+",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help meme") or messagestr.startswith(prefix+"help memes"):
                await client.send_message(receiver, "**Help, meme list:**\n" + memelist.replace("+",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help all"):
                await client.send_message(receiver, "**Help:**\n*1. Useful commands*\n" + helpmsg1.replace("+",prefix) + "*2. Fun commands*\n" + jokemsg.replace("+",prefix) + "*3. Meme commands*\n" + memelist.replace("+",prefix))
                Timeutil.setlast()
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
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
            await client.send_message(message.channel, "<@" + message.author.id + "> rolled :" + str(randint(0, int(msg5))))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Dice, 1 - 6
        elif messagestr.startswith(prefix+"dice"):
            await client.send_message(message.channel, "<@" + message.author.id + "> You got: " + str(randint(1,6)) + "!")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Credits?
        elif messagestr.startswith(prefix+"credits"):
            await client.delete_message(message)
            await client.send_message(message.channel, creditsmsg.format(bot=str(__version__)))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Cats are cute
        elif messagestr.startswith(prefix+"cats"):
            await client.send_file(message.channel, "data/images/cattypo.gif")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Kappa
        elif messagestr.startswith(prefix+"kappa"):
            await client.send_file(message.channel,"data/images/kappasmall.png")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Lists all members in current server
        elif messagestr.startswith(prefix+"members"):
            await client.send_typing(message.channel)
            count = 0
            members = ''
            for mem in message.channel.server.members:
                count += 1
                mem = str(mem)
                if count != 1:
                    members += ', '
                members += mem
            final = "Total : **{}** *members.*".format(count)
            await client.send_message(message.channel, "**Members:**\n" + members + "\n" + final)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Uptime
        elif messagestr.startswith(prefix+"uptime"):
            timeelapsed = time.time() - Timeutil.getstartup()
            converted = Timeutil.gettime(timeelapsed).split(":")
            await client.send_message(message.channel, "Uptime: {} days, {} hours, {} minutes and {} seconds ".format(converted[0],converted[1],converted[2],converted[3]))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Returns mentioned user's avatar, or if no mention present, yours.
        elif messagestr.startswith(prefix+"avatar"):
            if len(message.mentions) > 0:
                for user in list(message.mentions):
                    print(user)
                    if user.avatar_url != "":
                        await client.send_message(message.channel, "<@" + user.id + ">'s avatar: " + user.avatar_url)
                    else:
                        await client.send_message(message.channel, user.name + " doesn't have an avatar.")
            else:
                await client.send_message(message.channel,"<@" + message.author.id + ">'s avatar: " + message.author.avatar_url())
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
        # Returns user info (name,id,discriminator and avatar url)
        elif messagestr.startswith(prefix+"user"):
            await client.send_typing(message.channel)
            if len(message.mentions) > 0:
                for user in message.mentions:
                    name = user.name
                    uid = user.id
                    discrim = user.discriminator
                    avatar = user.avatar_url
                    final = "`Name: " + name + "\nId: " + uid + "\nDiscriminator: " + discrim + "\nAvatar url: " + avatar + "`"
                    await client.send_message(message.channel,final)
            else:
                await client.send_message(message.channel, "Please mention someone to display their info")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"games"):
            if parser.getboolean("Settings","monitorgames") is False:
                await client.send_message(message.channel,"This feature was disabled by the owner.")
                return
            games = game.getplayer(user=message.author.id)
            if message.channel.is_private:
                if games is None:
                    await client.send_message(message.author, "```You haven't played any games```")
                else:
                    full = ""
                    for that in games.keys():
                        if that == "username":
                            continue
                        a, b = divmod(int(round(games[that]/60,0)),60)
                        full += "{} : {} hours, {} minutes\n".format(that,a,b)
                    await client.send_message(message.author,"<@" + message.author.id + "> You played:\n```" + full + "```")
            else:
                if games is None:
                    await client.send_message(message.channel, "<@" + message.author.id + "> ```You haven't played any games```")
                else:
                    full = ""
                    for that in games.keys():
                        a, b = divmod(int(round(games[that]/60,0)),60)
                        full += "{} : {} hours, {} minutes\n".format(that,a,b)
                    await client.send_message(message.channel,"<@" + message.author.id + "> You played:\n```" + full + "```")
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
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                if len(message.mentions) == 0:
                    await client.send_message(message.channel,"Please mention someone to manage permissions")
                elif len(message.mentions) >= 2:
                    await client.send_message(message.channel, "Please mention only one person at a time")
                user = discord.utils.find(lambda member: member.name == dis.name, message.mentions)
                if messagestr.startswith(prefix+"role " +  "add "):
                    gotrole = str(message.content[len(prefix + "role " + "add "):]).split("<")[0].strip()
                    role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                    await client.add_roles(user,role)
                    await client.send_message(message.channel,'Successfully added *' + user.name + "* to " + gotrole)
                elif messagestr.startswith(prefix+"role " +  "remove "):
                    gotrole = str(message.content[len(prefix + "role " + "remove "):]).split("<")[0].strip()
                    role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                    await client.remove_roles(user,role)
                    await client.send_message(message.channel,'Successfully removed *' + user.name + "* from " + gotrole)
                elif messagestr.startswith(prefix+"role " +  "replacewith "):
                    gotrole = str(message.content[len(prefix + "role " + "replaceall "):]).split("<")[0].strip()
                    role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)
                    await client.replace_roles(user,role)
                    await client.send_message(message.channel,'Successfully replaced all ' + user.name + "'s roles : " + gotrole)
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
            else:
                logdis(message,type="message")
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        # Gets something from Wikipedia
        elif messagestr.startswith(prefix+"wiki") or messagestr.startswith(prefix+"define"):
            if messagestr.startswith(prefix+"wiki"):
                cut = str(messagestr[len(prefix)+len("wiki ")])
            elif messagestr.startswith(prefix+"define"):
                cut = str(messagestr[len(prefix)+len("define ")])
            try:
                wikipage = wikipedia.summary(cut,sentences=parser.get("Settings","wikisentences"))
                await client.send_message(message.channel,"*Wikipedia definition for* **" + cut + "** *:*\n" + wikipage)
            except wikipedia.exceptions.PageError:
                await client.send_message(message.channel,"No definitions for " + cut + " were found")
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
            await client.send_message(message.channel,"*Urban definition for* **" + messagestr[7:] + "** *:*" + convertedhtml)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # User kick
        elif messagestr.startswith(prefix+"kick"):
            if ((message.author.id == ownerid) or (message.author.name in self.whitelist)) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.kick(user)
                    await client.send_message(message.channel,"User " + user.name + " has been kicked.")
                    logdis("User {} has been kicked from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
        # User ban
        elif messagestr.startswith(prefix+"ban"):
            if ((message.author.id == ownerid) or (message.author.name in self.whitelist)) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.ban(user)
                    await client.send_message(message.channel,"User " + user.name + " has been banned from this server.")
                    logdis("User {} has been banned from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
        # User unban
        elif messagestr.startswith(prefix+"unban"):
            if ((message.author.id == ownerid) or (message.author.name in self.whitelist)) and len(message.mentions) != 0:
                for mention in message.mentions:
                    user = discord.utils.find(lambda  usr: usr.name == mention.name, message.channel.server.members)
                    await client.unban(user)
                    await client.send_message(message.channel,"User " + user.name + " has been unbanned.")
                    logdis("User {} has been unbanned from {}.".format(user.name,message.channel.server),type="write")
                    print(str("{} by {}".format(message.content,message.author)))
        # Adds custom commands
        elif messagestr.startswith(prefix+"cmd"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                if messagestr.startswith(prefix+"cmd add"):
                    cutstr = (message.content.replace("\n"," ")).split(maxsplit=3)
                    print(cutstr)
                    try:
                        processed = str("{}(){}".format(cutstr[2],cutstr[3]))
                    except IndexError:
                        await client.send_message(message.channel,"<@" + message.author.id + "> Please specify response.")
                        return
                    route = []
                    for line in open('data/customcmds.txt', 'r'):
                        if line == "":
                            continue
                        route.append(line.strip())
                    if processed in route:
                        await client.send_message(message.channel,"<@" + message.author.id + "> This command already exists.")
                        return
                    # now writing
                    with open("data/customcmds.txt","a") as file:
                        file.write("\n" + processed)
                    await client.send_message(message.channel,"<@" + message.author.id + "> Command {} has been added.".format("!" + cutstr[2]))
                elif messagestr.startswith(prefix+"cmd list"):
                    thatlist = []
                    for line in open('data/customcmds.txt', 'r'):
                        if line in ['\n', '\r\n']:
                            continue
                        thatlist.append(line.strip().split(':'))
                    completelist = ""
                    for this in thatlist:
                        completelist += this[0] + ", "
                    completelist = completelist[:-2]
                    if thatlist is not False:
                        await client.send_message(message.channel,"<@" + message.author.id + "> *Custom commands:*\n{}".format(completelist))
                    else:
                        await client.send_message(message.channel,"<@" + message.author.id + "> There are currently no custom commands")
                elif messagestr.startswith(prefix+"cmd remove"):
                        deletelist = messagestr[12:]
                        with open("data/customcmds.txt","r+") as f:
                            d = f.readlines()
                            f.seek(0)
                            for i in d:
                                if i.startswith(deletelist) is not True:
                                    f.write(i)
                            f.truncate()
                        if (deletelist is not False) or deletelist != "" or " ":
                            await client.send_message(message.channel,"<@" + message.author.id + "> Command {} successfully removed".format(deletelist))
                        else:
                            await client.send_message(message.channel,"<@" + message.author.id + "> Failed to delete command, it does not exist")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Changes "playing 'something'" status
        elif messagestr.startswith(prefix+"playing"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                cutstr = message.content[len(prefix)+len("playing")+1:]
                try:
                    status = SetStatus()
                    await status.set(cutstr)
                    await client.send_message(message.channel,"Status changed")
                except AssertionError:
                    pass
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        # Starts a vote
        elif messagestr.startswith(prefix+"vote start"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                cutstr = message.content[len(prefix)+len("vote start")+1:]
                if vote.getcontent() is not None:
                    await client.send_message(message.channel,"Vote already in progress")
                    return
                vote.create(str(message.author.name),cutstr.strip("(").strip(")").split('+')[1])
                one = 0
                list1 = ""
                name = cutstr.strip("(").strip(")").split('+')
                for this in name[1].split('""'):
                    list1 = list1 + "**" + str(one+1) + ". ** " + this + "\n"
                    one += 1
                await client.send_message(message.channel,"Vote started: \n{}\n{}".format(name[0],list1))
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        # Ends the voting
        elif messagestr.startswith(prefix+"vote end"):
            if (message.author.id == ownerid) or (message.author.name in self.whitelist):
                if vote.getcontent() is not None:
                    one = 0
                    endstr = "Voting has ended. Results: \n"
                    for this in vote.getcontent():
                        endstr += "{} :    {} votes\n".format(this,vote.returnvotes()[one])
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

# Events
@client.event
async def on_message(message):
    try:
        await AyyBot().on_message(message)
    except discord.InvalidArgument:
        print("Error : discord.InvalidArgument")
    except discord.ClientException:
        print("Error : discord.ClientException")
    except discord.errors.HTTPException:
        print("Error : discord.errors.HTTPException")

@client.async_event
async def on_member_join(member):
    if bool(parser.get("Settings","welcomemsg")) is True and BotSleep.getstate() is False:
        await client.send_message(member.server, 'Welcome to the server, {0}'.format(member.name))
        print("{} joined the server".format(member.name))
        logdis(message="{} joined the server".format(member.name),type="write")

@client.async_event
async def on_message_delete(message):
    if bool(parser.get("Settings","logchannel")) is not False and swearing.check(message) is False and BotSleep.getstate() is False:
        messagestr = str(message.content)
        channel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), message.channel.server.channels)
        if message.channel == channel or messagestr.startswith("!") or message.author.name == client.user.name:
            return
        await client.send_message(channel,"```User {} deleted his/her message:\n{}\nin channel: #{}```".format(message.author,messagestr,message.channel.name))

@client.async_event
async def on_message_edit(before,after):
    if bool(parser.get("Settings","logchannel")) is not False and BotSleep.getstate() is False:
        msgbefore = str(before.content)
        msgafter = str(after.content)
        if msgbefore == msgafter:
            return
        logchannel = discord.utils.find(lambda channel: channel.name == parser.get("Settings","logchannel"), before.channel.server.channels)
        if before.channel == logchannel:
            return
        if msgbefore.startswith("!") or msgafter.startswith("!"):
            return
        try:
            await client.send_message(logchannel,"```User {} edited his message:\nBefore: {}\nAfter: {}\nin channel: #{}```".format(before.author,msgbefore,msgafter,before.channel.name))
        except discord.errors.InvalidArgument:
            print("No 'logs' channel")

@client.async_event
async def on_member_update(before,after):
    # ayybot.sleep does not impact this feature!
    # However, it can be disabled in settings.ini
    if bool(parser.get("Settings","monitorgames")) is False:
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
    if bool(parser.get("Settings","status")) is not False:
        try:
            status = SetStatus()
            await status.startup()
        except AssertionError:
            pass

# Starts the bot
@asyncio.coroutine
def start():
    print("Connecting... ",end="")
    yield from client.login(parser.get("Credentials","mail"),parser.get("Credentials","password"))
    yield from client.connect()

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(start())
except:
    print("Exception raised, logging out.")
    loop.run_until_complete(client.logout())
finally:
    loop.close()
