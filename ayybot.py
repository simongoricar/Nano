import discord,asyncio
import time,configparser,wordfilter,wikipedia,requests
from random import randint
from config import customcmd,eightball,helpmsg1,creditsmsg,jokemsg,memelist,quotes,filterwords,conversation
from datetime import timedelta, datetime
from giphypop import translate
from bs4 import BeautifulSoup

__author__ = 'DefaltSimon'
__version__ = '1.4 n. 21'

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
        pass
    def gettime(self,time_elapsed):
        sec = timedelta(seconds=time_elapsed)
        d = datetime(1, 1, 1) + sec
        this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
        return this

class Vote:
    def __init__(self):
        self.votecontent = []
        self.voters = []
        self.votesgot1 = 0
        self.votesgot2 = 0
        self.votesgot3 = 0
        self.votesgot4 = 0
        self.votesgot5 = 0
    def create(self,author,vote):
        self.hm = 0
        for this in str(vote).split('""'):
            self.hm += 1
            this = "**" + str(self.hm) + "**" + ". " + str(this).strip("(").strip(")")
            self.votecontent.append(this)
        self.initiator = str(author)
    def reset(self):
        self.votecontent = []
        self.voters = []
        self.votesgot1 = 0
        self.votesgot2 = 0
        self.votesgot3 = 0
        self.votesgot4 = 0
        self.votesgot5 = 0
    def getcontent(self):
        if not self.votecontent:
            return None
        else:
            return self.votecontent
    def countone(self,option,voter):
        option = int(option)
        self.voters.append(voter)
        if option == 1:
            self.votesgot1 += 1
        elif option == 2:
            self.votesgot2 += 1
        elif option == 3:
            self.votesgot3 += 1
        elif option == 4:
            self.votesgot4 += 1
        elif option == 5:
            self.votesgot5 += 1
    def returnvotes(self):
        list = [self.votesgot1,self.votesgot2,self.votesgot3,self.votesgot4,self.votesgot5]
        return list
    def returncontent(self):
        return self.votecontent

client = discord.Client()
BotSleep = BotSleep()
Timeutil = TimeUtil()
votebot = Vote()
parser = configparser.ConfigParser()

parser.read("settings.ini")
ownerid = str(parser.get("Settings","ownerid"))
prefix = str(parser.get("Settings","prefix"))

# Write two newlines to data/log.txt
if parser.getboolean("Settings","WriteLogs") == 1:
    with open('data/log.txt','a') as file:
        file.write("\n-----------------------\n")

def logdis(message,type):
    if parser.getboolean("Settings", "WriteLogs") == 1:
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

def checkwords(message):
    wordfilter.add_words(filterwords)
    cmsg = str(message.content).lower()
    if wordfilter.blacklisted(cmsg) and message.author != "AyyBot":
        return True


# Temporary, its shit
def checkspam(message):
    if message.author.name == "AyyBot":
        return
    spamword = ""
    another = 0
    dis = 0
    for c in str(message.content):
        if dis == 0:
            spamword = c
            dis += 1
            continue
        if c == spamword:
            another += 1
    if another > 7:
        return True

def checkwhitelist(name):
    with open("data/whitelist.txt","r") as file:
        lines = (line.rstrip() for line in file)
        lines = list(line for line in lines if line)
    return bool(name in lines)


# ALL commands
class AyyBot:
    def __init__(self):
        pass
    async def on_message(self,message):
        if message.author.id == client.user.id:
            return
        messagestr = str(message.content).lower()
        # check for ayybot.sleep/wake before (possibly) quiting out of on_message
        if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
            if messagestr.startswith("ayybot."):
                msg6 = str(message.content[7:])
                if msg6 == "sleep":
                    if BotSleep.getstate is True:
                        await client.send_message(message.channel,"No need m8, I was already sleeping.")
                        return
                    BotSleep.sleep()
                    await client.send_message(message.channel,"Now sleeping...")
                    print("Saved sleeping")
                elif msg6 == "wake":
                    BotSleep.wake()
                    await client.send_message(message.channel,"**I'm BACK MFS**")
                    print("Returned to normal")
        if BotSleep.getstate() is True:
            return
        # Spam and swearing check / with settings.ini
        if parser.getboolean("Settings", "filterwords") == 1:
            if (checkwords(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                await client.send_message(message.channel, "<@" + message.author.id + ">, watch it!".format(usr=message.author))
                print("A message by {usr} was filtered - bad word".format(usr=message.author))
        if parser.getboolean("Settings", "filterspam") == 1:
            if (checkspam(message) is True) and message.channel.name != str(parser.get("Settings","logchannel")):
                await client.delete_message(message)
                await client.send_message(message.channel,"@{usr} Spam is not allowed. **Deal with it** ( ͡° ͜ʖ ͡°)".format(usr=message.author))
                print("A message by {usr} was filtered - spam".format(usr=message.author))
        # commands imported from config.py
        for onething in customcmd.keys():
            if message.content.lower().startswith(onething):
                client.delete_message(message)
                second = customcmd.get(str(message.content.lower()))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message,type="message")
                await client.send_message(message.channel, second.format(usr=message.author.id))
                return
        # Check for commands in data/customcmds.txt
        with open("data/customcmds.txt","r") as disone:
            for disonea in disone.readlines():
                if disonea.strip() == "":
                    continue
                if messagestr.startswith((disonea.strip().split(':',maxsplit=2))[0]):
                    await client.send_message(message.channel,disonea.strip().split(':')[1])
                    logdis(message,type="message")
                    return
        for dis in message.mentions:
            if dis.name == "AyyBot":
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
                    await client.send_message(message.channel,cutmsg[4:])
        if messagestr.startswith(prefix+"help"):
            if (int(time.time()) - int(Timeutil.getlast()) < 10) and ((message.author.id != ownerid) or (checkwhitelist(message.author.name) is False)):
                return
            if messagestr.startswith(prefix+"help useful") or messagestr == prefix+"help":
                await client.send_message(message.channel, "**Help, useful commands:**\n" + helpmsg1.replace("!",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help fun"):
                await client.send_message(message.channel, "**Help, fun commands:**\n" + jokemsg.replace("!",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help meme") or messagestr.startswith("!help memes"):
                await client.send_message(message.channel, "**Help, meme list:**\n" + memelist.replace("!",prefix))
                Timeutil.setlast()
            elif messagestr.startswith(prefix+"help all"):
                await client.send_message(message.channel, "**Help:**\n*1. Useful commands*\n" + helpmsg1.replace("!",prefix) + "*2. Fun commands*\n" + jokemsg.replace("!",prefix) + "*3. Meme commands*\n" + memelist.replace("!",prefix))
                Timeutil.setlast()
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Shut down
        elif messagestr.startswith("ayybot.kill"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                await client.send_message(message.channel, "**DED**")
                print(str("{msg} by {usr}, quitting".format(msg=message.content,usr=message.author)))
                logdis(message,type="message")
                exit(-420)
            else:
                logdis(message,type="message")
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        elif messagestr.startswith(prefix+"hello"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel,"Hi, <@" + message.author.id + ">")
            else:
                for dis in message.mentions:
                    await client.send_message(message.channel,"Hi, <@" + dis.id + ">")
            logdis(message,type="message")
        # They see me rollin'
        elif messagestr.startswith(prefix+"roll"):
            msg5 = message.content.lower()[6:]
            await client.send_message(message.channel, "<@" + message.author.id + "> rolled :" + str(randint(0, int(msg5))))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Dice - 1 - 6
        elif messagestr.startswith(prefix+"dice"):
            await client.send_message(message.channel, "<@" + message.author.id + "> You got: " + str(randint(1,6)) + "!")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Game
        elif messagestr.startswith(prefix+"game"):
            client.delete_message(message)
            msgcut = message.content[6:]
            print(msgcut)
            await client.send_message(message.channel,"@everyone Does anyone want to play {}? ({})".format(str(msgcut),message.author))
        # Credits
        elif messagestr.startswith(prefix+"credits"):
            client.delete_message(message)
            await client.send_message(message.channel, creditsmsg.format(bot=str(__version__)))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Cats are cute
        elif messagestr.startswith(prefix+"cats"):
            await client.send_file(message.channel, "data/images/cattypo.gif")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        elif messagestr.startswith(prefix+"kappa"):
            await client.send_file(message.channel,"data/images/kappasmall.png")
            logdis(message,type="message")
        # Lists all members in current server
        elif messagestr.startswith(prefix+"members"):
            await client.send_message(message.channel, "<@" + message.author.id + "> **Current members:**")
            count = 0
            members = ''
            for mem in message.channel.server.members:
                count += 1
                mem = str(mem)
                if count != 1:
                    members += ', '
                members += mem
            final = "**Total : {count1} members.**".format(count1=count)
            await client.send_message(message.channel, members)
            await client.send_message(message.channel, final)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Uptime
        elif messagestr.startswith(prefix+"uptime"):
            client.delete_message(message)
            time_elapsed = time.time() - Timeutil.getstartup()
            converted = Timeutil.gettime(time_elapsed)
            await client.send_message(message.channel, "Uptime: {} ".format(converted))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Returns mentioned user's avatar, or if no mention present, yours.
        elif messagestr.startswith(prefix+"avatar"):
            client.delete_message(message)
            if len(message.mentions) > 0:
                for user in list(message.mentions):
                    print(user)
                    if user.avatar_url != "":
                        await client.send_message(message.channel, "<@" + user.id + ">'s avatar: " + user.avatar_url)
                    else:
                        await client.send_message(message.channel, user.name + " doesn't have an avatar.")
            else:
                user2 = message.author
                await client.send_message(message.channel,"<@" + message.author.id + ">'s avatar: " + user2.avatar_url())
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message,type="message")
        # Decides between two or more words
        elif messagestr.startswith(prefix+"decide"):
            msg3 = str(message.content.lower()[7:]).split()
            if randint(1,2) == 1:
                await client.send_message(message.channel, "<@" + message.author.id + "> " + "\nI have decided: " + msg3[0])
            else:
                await client.send_message(message.channel, "<@" + message.author.id + "> I have decided: " + msg3[1])
                logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Answers your question - 8ball style
        elif messagestr.startswith(prefix+"8ball"):
            client.delete_message(message)
            msg6 = str(message.content[6:])
            answer = eightball[randint(1,len(eightball))]
            await client.send_message(message.channel,"<@" + message.author.id + "> asked : " + msg6 + "\n**" + answer + "**")
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a gif matching the name from Giphy (!gif <name>)
        elif messagestr.startswith(prefix+"gif"):
            msg2 = str(message.content.lower()[4:])
            img = str(translate(msg2))
            await client.send_message(message.channel, "<@" + message.author.id + "> " + img)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Returns user info (name,id,discriminator and avatar url)
        elif messagestr.startswith(prefix+"user"):
            client.delete_message(message)
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
        # Returns a random quote
        elif messagestr.startswith(prefix+"quote"):
            client.delete_message(message)
            answer = quotes[randint(1,len(quotes))]
            await client.send_message(message.channel,answer)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # For managing roles
        elif messagestr.startswith(prefix+"role"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                if len(message.mentions) == 0:
                    await client.send_message(message.channel,"Please mention someone to add permissions")
                elif len(message.mentions) >= 2:
                    await client.send_message(message.channel, "Please mention only one person at a time")
                for dis in message.mentions:
                    user = discord.utils.find(lambda member: member.name == dis.name, message.channel.server.members)
                roles = []
                for role in message.server.roles:
                    roles.append(role.name)
                for this1 in roles:
                    if messagestr.startswith(prefix+"role " +  "add " + this1):
                        role = discord.utils.find(lambda role: role.name == this1, message.channel.server.roles)
                        await client.add_roles(user,role)
                        await client.send_message(message.channel,'Successfully added ' + user.name + " to " + this1)
                    elif messagestr.startswith(prefix+"role " +  "remove " + this1):
                        role = discord.utils.find(lambda role: role.name == this1, message.channel.server.roles)
                        await client.remove_roles(user,role)
                        await client.send_message(message.channel,'Successfully removed ' + user.name + " from " + this1)
                    elif messagestr.startswith(prefix+"role " +  "replacewith " + this1):
                        role = discord.utils.find(lambda role: role.name == this1, message.channel.server.roles)
                        await client.replace_roles(user,role)
                        await client.send_message(message.channel,'Successfully replaced all ' + user.name + "'s roles : " + this1)
            else:
                logdis(message,type="message")
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        # Gets something from Wikipedia
        elif messagestr.startswith(prefix+"wiki") or messagestr.startswith(prefix+"define"):
            cut = str(messagestr[6:])
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
            query = str(messagestr[7:])
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(query))
            purehtml = BeautifulSoup(define.content, "html.parser")
            convertedhtml = purehtml.find("div",attrs={"class":"meaning"}).text
            if convertedhtml is None or str(convertedhtml).startswith("There"):
                await client.send_message(message.channel,"There are no *urban* definitions for {}".format(query))
            await client.send_message(message.channel,"*Urban definition for* **" + messagestr[7:] + "** *:*" + convertedhtml)
            logdis(message,type="message")
            print(str("{} by {}".format(message.content,message.author)))
        # Adds custom commands on the fly
        elif messagestr.startswith(prefix+"cmd"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                if messagestr.startswith("cmd add"):
                    cutstr = (messagestr.replace("\n"," ")).split(maxsplit=3)
                    print(cutstr)
                    try:
                        processed = str("!{}:{}".format(cutstr[2],cutstr[3]))
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
                elif messagestr.startswith(prefix+"!cmd list"):
                    thatlist = []
                    for line in open('data/customcmds.txt', 'r'):
                        if line in ['\n', '\r\n']:
                            continue
                        thatlist.append(line.strip().split(':'))
                    completelist = ""
                    for this in thatlist:
                        completelist += this[0] + ", "
                    if thatlist is not False:
                        await client.send_message(message.channel,"<@" + message.author.id + "> *Current custom commands:*\n{}".format(completelist))
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
        elif messagestr.startswith(prefix+"playing"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                cutstr = message.content[9:]
                try:
                    status = SetStatus()
                    await status.set(cutstr)
                    await client.send_message(message.channel,"Successfully set status to *{}*".format(cutstr))
                except AssertionError:
                    pass
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"vote start"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                cutstr = message.content[12:]
                if votebot.getcontent() == None:
                    await client.send_message(message.channel,"There is an ongoing vote right now, cannot start another one.")
                votebot.create(str(message.author.name),cutstr.strip("(").strip(")").split('+')[1])
                one = 0
                list1 = ""
                name = cutstr.strip("(").strip(")").split('+')
                for this in name[1].split('""'):
                    list1 = list1 + "**" + str(one+1) + ". ** " + this + "\n"
                    one += 1
                await client.send_message(message.channel,"Vote started: \n{}\n{}".format(name[0],list1))
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"vote end"):
            if (message.author.id == ownerid) or checkwhitelist(name=message.author.name):
                if votebot.getcontent() is not None:
                    one = 0
                    endstr = "Voting has ended. Results: \n"
                    for this in votebot.getcontent():
                        endstr = endstr + "{} :    {} votes\n".format(this,votebot.returnvotes()[one])
                        one += 1
                    await client.send_message(message.channel,endstr)
                    votebot.reset()
                logdis(message,type="message")
                print(str("{} by {}".format(message.content,message.author)))
        elif messagestr.startswith(prefix+"vote"):
            for this in votebot.voters:
                if message.author.id == this:
                    await client.send_message(message.channel,"<@" + message.author.id + "> Cheater! :smile:")
                    return
            votebot.countone(messagestr[6:],voter=message.author.id)

@client.event
async def on_message(message):
    try:
        await AyyBot().on_message(message)
    except discord.InvalidArgument:
        print("Error -3 : InvalidArgument")
        await client.send_message(message.channel, "Error: InvalidArgument")
    except discord.ClientException:
        print("Error -1 : ClientException")
        await client.send_message(message.channel, "Error: ClientException")
    except discord.HTTPException:
        print("Error -2 : HTTPException")
        await client.send_message(message.channel, "Error: HTTPException")

@client.async_event
async def on_member_join(member):
    server = member.server
    await client.send_message(server, 'Welcome to the server, {0}'.format(member.mention()))
    print("{} joined the server".format(member.name))
    logdis(message="{} joined the server".format(member.name),type="write")

@client.async_event
async def on_message_delete(message):
    messagestr = str(message.content)
    channel = discord.utils.find(lambda channel: channel.name == "logs", message.channel.server.channels)
    if message.channel == channel or messagestr.startswith("!"):
        return
    await client.send_message(channel,"```User {} deleted his/her message:\n{}\nin channel: #{}```".format(message.author,messagestr,message.channel.name))

@client.async_event
async def on_message_edit(before,after):
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
async def on_ready():
    print("connected and running")
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('------------------')
    # sets status
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
    loop.run_until_complete(client.logout())
finally:
    loop.close()
