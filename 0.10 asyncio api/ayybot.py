import discord
import time,configparser,wordfilter,wikipedia,requests
from random import randint
from config import useful,meme,eightball,helpmsg1,creditsmsg,jokemsg,memelist,quotes,filterwords
from datetime import timedelta, datetime
from giphypop import translate
from bs4 import BeautifulSoup

__title__ = 'AyyBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '1.1'

# import logging
# logging.basicConfig(level=logging.DEBUG)

client = discord.Client()
clientchannel = discord.Channel()

# For !uptime
start_time = time.time()

parser = configparser.ConfigParser()
parser.read("settings.ini")
parser.set("Settings","state_sleep","0")
parser.set("Settings","lasttime",str(int(start_time)))
with open('settings.ini', 'w') as configfile:
    parser.write(configfile)

def deletemsg(message):
    client.delete_message(message)

def gettime(time_elapsed):
    sec = timedelta(seconds=time_elapsed)
    d = datetime(1, 1, 1) + sec
    this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
    return this

def logdis(message):
    if parser.getboolean("Settings", "WriteLogs") == 1:
        with open('data/log.txt',"a") as file2:
            one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
            str2 = one + str(" : {msg} by {usr}\n".format(msg=message.content,usr=message.author))
            file2.write(str2)

def checkwords(message):
    cmsg = str(message.content).lower()
    wordfilter.add_words(filterwords)
    if wordfilter.blacklisted(cmsg) and message.author != "AyyBot":
        client.send_message(message.channel, "@{usr}, watch it!".format(usr=message.author))

def checkwhitelist(name):
    # Checks for whitelisted users
    with open("data/whitelist.txt","r") as file:
        lines = (line.rstrip() for line in file)
        lines = list(line for line in lines if line)
    if name in lines:
        return True
    else:
        return False

def checkspam(message):
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
    if another > 7 and message.author != "AyyBot":
        client.delete_message(message)
        client.send_message(message.channel,
                            "@{usr} Spam is not allowed. **Deal with it** ( ͡° ͜ʖ ͡°)".format(usr=message.author))
        print("A message by {usr} was filtered - spam".format(usr=message.author))

@client.event
async def on_message(message):
    try:
        state_sleep = int(parser.getboolean("Settings","state_sleep"))
        messagestr = str(message.content).lower()
        disauthor = message.author
        userId = message.author.id
        # check for ayybot.sleep/wake before (possibly) quiting out of on_message
        if (message.author.id == message.channel.server.owner.id) or checkwhitelist(name=disauthor):
            if messagestr.startswith("ayybot."):
                msg6 = str(message.content[7:])
                if msg6 == "sleep":
                    if state_sleep == 1:
                        await client.send_message(message.channel,"No need m8, I was already sleeping.")
                        return
                    parser.set("Settings","state_sleep","1")
                    with open('settings.ini', 'w') as configfile2:
                        parser.write(configfile2)
                    await client.send_message(message.channel,"Now sleeping...")
                    print("Saved sleeping")
                elif msg6 == "wake":
                    parser.set("Settings","state_sleep","0")
                    with open('settings.ini', 'w') as configfile3:
                        parser.write(configfile3)
                    await client.send_message(message.channel,"**I'm BACK MFS**")
                    print("Returned to normal")
        if state_sleep == 1:
            return
        # Spam and swearing check / with settings.ini
        if parser.getboolean("Settings", "filterwords") == 1:
            checkwords(message)
        if parser.getboolean("Settings", "filterspam") == 1:
            checkspam(message)
        # commands imported from config.py
        for onething in meme.keys():
            if message.content.lower().startswith(onething):
                deletemsg(message)
                second = meme.get(str(message.content.lower()))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message)
                await client.send_message(message.channel, second.format(usr=disauthor.id))
                return
        for onething2 in useful.keys():
            if message.content.lower().startswith(onething2):
                second = useful.get(str(message.content.lower()))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message)
                await client.send_message(message.channel, second.format(usr=disauthor.id))
                return
        # Check for commands in data/customcmds.txt
        with open("data/customcmds.txt","r") as disone:
            for disonea in disone.readlines():
                if disonea.strip() == "":
                    continue
                if messagestr.startswith((disonea.strip().split(':'))[0]):
                    await client.send_message(message.channel,disonea.strip().split(':')[1])
                    logdis(message)
                    return
        if messagestr.startswith("!help"):
            if int(time.time()) - int(parser.get("Settings","lasttime")) < 10:
                return
            def dothis():
                parser.set("Settings","lasttime",str(int(time.time())))
                with open('settings.ini', 'w') as configfile:
                    parser.write(configfile)
            if messagestr.startswith("!help useful") or messagestr == "!help":
                await client.send_message(message.channel, "**Help, useful commands:**\n" + helpmsg1)
                dothis()
            elif messagestr.startswith("!help fun"):
                await client.send_message(message.channel, "**Help, fun commands:**\n" + jokemsg)
                dothis()
            elif messagestr.startswith("!help meme") or messagestr.startswith("!help memes"):
                await client.send_message(message.channel, "**Help, meme list:**\n" + memelist)
                dothis()
            elif messagestr.startswith("!help all"):
                await client.send_message(message.channel, "**Help:**\n*1. Useful commands*\n" + helpmsg1 + "*2. Fun commands*\n" + jokemsg + "*3. Meme commands*\n" + memelist)
                dothis()
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Shut down
        elif messagestr.startswith("ayybot.kill"):
            if (message.author.id == message.channel.server.owner.id) or checkwhitelist(name=disauthor):
                await client.send_message(message.channel, "**DED**")
                print(str("{msg} by {usr}, quitting".format(msg=message.content,usr=message.author)))
                logdis(message)
                exit(-420)
            else:
                logdis(message)
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        elif messagestr.startswith("!hello"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel,"Hi, <@" + message.author.id + ">")
            else:
                for dis in message.mentions:
                    await client.send_message(message.channel,"Hi, <@" + dis.id + ">")
            logdis(message)
        # They see me rollin'
        elif messagestr.startswith('!roll'):
            msg5 = message.content.lower()[6:]
            await client.send_message(message.channel, "<@" + disauthor.id + "> rolled :" + str(randint(0, int(msg5))))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Dice - 1 - 6
        elif messagestr.startswith("!dice"):
            await client.send_message(message.channel, "<@" + disauthor.id + "> You got: " + str(randint(1,6)) + "!")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Game
        elif messagestr.startswith("!game"):
            deletemsg(message)
            msgcut = messagestr[6:]
            print(msgcut)
            await client.send_message(message.channel,"@everyone Does anyone want to play {}? ({})".format(str(msgcut),disauthor))
        # Credits
        elif messagestr.startswith("!credits"):
            deletemsg(message)
            await client.send_message(message.channel, creditsmsg.format(bot=str(__version__)))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Cats are cute
        elif messagestr.startswith("!cats"):
            await client.send_file(message.channel, "data/images/cattypo.gif")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        elif messagestr.startswith("!kappa"):
            await client.send_file(message.channel,"data/images/kappasmall.png")
            logdis(message)
        # Lists all members in current server
        elif messagestr.startswith("!members"):
            await client.send_message(message.channel, "<@" + disauthor.id + "> **Current members:**")
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
            logdis(message)
        # Uptime
        elif messagestr.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = gettime(time_elapsed)
            await client.send_message(message.channel, "<@" + disauthor.id + "> **Uptime: {upt} **".format(upt=converted))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Returns mentioned user's avatar, or if no mention present, yours.
        elif messagestr.startswith("!avatar"):
            deletemsg(message)
            if len(message.mentions) > 0:
                for user in list(message.mentions):
                    print(user)
                    if user.avatar_url != "":
                        await client.send_message(message.channel, "<@" + user.id + ">'s avatar: " + user.avatar_url)
                    else:
                        await client.send_message(message.channel, user.name + " doesn't have an avatar.")
            else:
                user2 = message.author
                await client.send_message(message.channel,"<@" + disauthor.id + ">'s avatar: " + user2.avatar_url())
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Decides between two or more words
        elif messagestr.startswith("!decide"):
            msg3 = str(message.content.lower()[7:]).split()
            if randint(1,2) == 1:
                await client.send_message(message.channel, "<@" + disauthor.id + "> " + "\nI have decided: " + msg3[0])
            else:
                await client.send_message(message.channel, "<@" + disauthor.id + "> I have decided: " + msg3[1])
                logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Answers your question - 8ball style
        elif messagestr.startswith("!8ball"):
            deletemsg(message)
            msg6 = str(message.content[6:])
            answer = eightball[randint(1,len(eightball))]
            await client.send_message(message.channel,"<@" + disauthor.id + "> asked : " + msg6 + "\n**" + answer + "**")
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a gif matching the name from Giphy (!gif <name>)
        elif messagestr.startswith("!gif"):
            msg2 = str(message.content.lower()[4:])
            img = str(translate(msg2))
            await client.send_message(message.channel, "<@" + disauthor.id + "> " + img)
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Returns user info (name,id,discriminator and avatar url)
        elif messagestr.startswith("!user"):
            deletemsg(message)
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
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a random quote
        elif messagestr.startswith("!quote"):
            deletemsg(message)
            answer = quotes[randint(1,len(quotes))]
            await client.send_message(message.channel,answer)
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # For managing roles
        elif messagestr.startswith("!role"):
            if (message.author.id == message.channel.server.owner.id) or checkwhitelist(name=disauthor):
                for dis in message.mentions:
                    user = discord.utils.find(lambda member: member.name == dis.name, message.channel.server.members)
                if messagestr.startswith("!role member") or messagestr.startswith("!role members"):
                    role = discord.utils.find(lambda role: role.name == "members", message.channel.server.roles)
                    await client.add_roles(user,role)
                    print("Changed permissions to member.")
                    logdis(message)
                    await client.send_message(message.channel,"Changed " + user.name + "'s permissions to member.")
                elif messagestr.startswith("!role mod") or messagestr.startswith("!role mods"):
                    print("ok")
                    roles = discord.utils.find(lambda m: m.name == 'mods', message.channel.server.roles)
                    await client.add_roles(user, roles)
                    print('Changed a user to mod.')
                    logdis(message)
                    await client.send_message(message.channel,'Successfully added ' + user.name + ' to mods.')
                elif messagestr.startswith("!role member") or messagestr.startswith("!role members"):
                    role = discord.utils.find(lambda role: role.name == 'mods', message.channel.server.roles)
                    await client.remove_roles(user,role)
                    print("Removed permissions.")
                    logdis(message)
                    await client.send_message(message.channel,'Successfully removed ' + user.name + ' from mods')
                elif messagestr.startswith("!role admin") or messagestr.startswith("!role admins"):
                    role = discord.utils.find(lambda role: role.name == 'admins', message.channel.server.roles)
                    await client.remove_roles(user,role)
                    print("Changed a user to admin.")
                    logdis(message)
                    await client.send_message(message.channel,'Successfully added ' + user.name + ' to admins.')
            else:
                logdis(message)
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        # Gets something from Wikipedia
        elif messagestr.startswith("!wiki"):
            try:
                wikipage = wikipedia.summary(str(messagestr[6:]),sentences=parser.get("Settings","wikisentences"))
                await client.send_message(message.channel,"*Wikipedia definition for* **" + messagestr[6:] + "** *:*\n" + wikipage)
            except wikipedia.exceptions.PageError:
                await client.send_message(message.channel,"No definitions for " + messagestr[6:] + " were found")
            except wikipedia.exceptions.DisambiguationError:
                await client.send_message(message.channel,"There are multiple definitions of {}, please be more specific".format(str(messagestr[6:])))
            logdis(message)
        # Gets urban dictionary term
        elif messagestr.startswith("!urban"):
            query = messagestr[7:]
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(query))
            purehtml = BeautifulSoup(define.content, "html.parser")
            convertedhtml = purehtml.find("div",attrs={"class":"meaning"}).text
            if convertedhtml == None or str(convertedhtml).startswith("There"):
                await client.send_message(message.channel,"There are no *urban* definitions for {}".format(query))
            await client.send_message(message.channel,"*Urban definition for* **" + messagestr[7:] + "** *:*" + convertedhtml)
            logdis(message)
        # Adds custom commands on the fly
        elif messagestr.startswith("!cmd"):
            if (message.author.id == message.channel.server.owner.id) or checkwhitelist(name=disauthor):
                if messagestr.startswith("!cmd add"):
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
                elif messagestr.startswith("!cmd list"):
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
                elif messagestr.startswith("!cmd remove"):
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
            logdis(message)
#        elif messagestr.startswith("!whitelist"):
#            if message.author.id == message.channel.server.owner.id:
#                if messagestr.startswith("!whitelist add"):
#                    cutmsg = messagestr[15:]
#                    route = []
#                    for line in open('data/whitelist.txt', 'r'):
#                        if line == "":
#                            continue
#                        route.append(line.strip())
#                    if cutmsg in route:
#                        return
#                    for mention in message.mentions:
#                        print(mention)
#                        with open("data/whitelist.txt","a") as file:
#                            file.write("\n" + mention)
#                elif messagestr.startswith("!whitelist remove"):
#                    cutmsg = messagestr[18:]
    except discord.InvalidArgument:
        print("Error -3 : InvalidArgument")
        await client.send_message(message.channel, "Error -3 : InvalidArgument")
    except discord.ClientException:
        print("Error -1 : ClientException")
        await client.send_message(message.channel, "Error -1 : ClientException")
    except discord.HTTPException:
        print("Error -2 : HTTPException")
        await client.send_message(message.channel, "Error -2 : HTTPException")

@client.async_event
async def on_ready():
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('------------------')

@client.async_event
async def on_member_join(member):
    server = member.server
    await client.send_message(server, 'Welcome to the server, {0}'.format(member.mention()))
    print("{} joined the server".format(member.name))

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

# Write log line ---- (will change in the future)
if parser.getboolean("Settings","WriteLogs") == 1:
    with open('data/log.txt','a') as file:
        file.write("\n------------------------------\n")

# Starts the bot (blocking call)
client.run(parser.get("Credentials","username"),parser.get("Credentials","password"))
