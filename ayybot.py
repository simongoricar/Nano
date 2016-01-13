import discord
from random import randint
from config import mail,password,useful,meme,eightball,helpmsg1,creditsmsg,jokemsg,memelist,quotes,filterwords
from datetime import timedelta, datetime
import time,configparser,os,wordfilter,wikipedia,requests
from giphypop import translate
from bs4 import BeautifulSoup

__title__ = 'AyyBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.15'

# import logging
# logging.basicConfig(level=logging.DEBUG)

client = discord.Client()
clientchannel = discord.Channel()
botvs = "0.15"

parser = configparser.ConfigParser()
parser.read("settings.ini")
parser.set("Settings","state_sleep","0")
with open('settings.ini', 'w') as configfile:
    parser.write(configfile)

def runme():
    client.run()

def loginme():
    client.login(mail,password)

def deletemsg(message):
    client.delete_message(message)

def gettime(time_elapsed):
    sec = timedelta(seconds=time_elapsed)
    d = datetime(1, 1, 1) + sec
    this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
    return this

def logdis(message):
    if parser.getboolean("Settings", "WriteLogs") == 1:
        with open('log.txt',"a") as file2:
            one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
            str2 = one + str(" : {msg} by {usr}\n".format(msg=message.content,usr=message.author))
            file2.write(str2)

def checkwords(message):
    cmsg = str(message.content).lower()
    wordfilter.add_words(filterwords)
    if wordfilter.blacklisted(cmsg) and message.author != "AyyBot":
        client.send_message(message.channel, "@{usr}, watch it!".format(usr=message.author))

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
def on_message(message):
    try:
        state_sleep = int(parser.getboolean("Settings","state_sleep"))
        messagestr = str(message.content).lower()
        disauthor = message.author
        # check for !manage before (possibly) quiting out of def
        if messagestr.startswith("ayybot."):
            msg6 = str(message.content[7:])
            if msg6 == "sleep":
                if state_sleep == 1:
                    client.send_message(message.channel,"No need m8, I was already sleeping.")
                    return
                parser.set("Settings","state_sleep","1")
                with open('settings.ini', 'w') as configfile:
                    parser.write(configfile)
                client.send_message(message.channel,"Now sleeping...")
                print("Saved sleeping")
            elif msg6 == "wake":
                parser.set("Settings","state_sleep","0")
                with open('settings.ini', 'w') as configfile:
                    parser.write(configfile)
                client.send_message(message.channel,"Returned from winter sleep.")
                print("Returned to normal")
        if state_sleep == 1:
            print("Sleeping...")
            return
        # Spam and swearing check / with settings.txt check in config.checksettings(parm=1 or 2)
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
                client.send_message(message.channel, second.format(usr=disauthor.id))
                return
        for onething2 in useful.keys():
            if message.content.lower().startswith(onething2):
                second = useful.get(str(message.content.lower()))
                print(str("{} by {}".format(message.content,message.author)))
                logdis(message)
                client.send_message(message.channel, second.format(usr=disauthor.id))
                return
        if messagestr.startswith("!help"):
            if messagestr.startswith("!help useful") or messagestr == "!help":
                client.send_message(message.channel, helpmsg1)
            elif messagestr.startswith("!help fun"):
                client.send_message(message.channel, jokemsg)
            elif messagestr.startswith("!help meme") or messagestr.startswith("!help memes"):
                client.send_message(message.channel, memelist)
            elif messagestr.startswith("!help all"):
                client.send_message(message.channel, helpmsg1 + jokemsg + memelist)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Shut down
        elif messagestr.startswith("ayybot.kill"):
            role1 = discord.utils.find(lambda role: role.name == 'serveradmins', message.channel.server.roles)
            if message.author.id == message.channel.server.owner.id or role1:
                client.send_message(message.channel, "**DED**")
                print(str("{msg} by {usr}, quitting".format(msg=message.content,usr=message.author)))
                logdis(message)
                exit(-420)
            else:
                logdis(message)
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        # They see me rollin'
        elif messagestr.startswith('!roll'):
            deletemsg(message)
            msg5 = message.content.lower()[6:]
            client.send_message(message.channel, "<@" + disauthor.id + "> rolled :" + str(randint(0, int(msg5))))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Dice - 1 - 6
        elif messagestr.startswith("!dice"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + "> You got: " + str(randint(1,6)) + "!")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Game
        elif messagestr.startswith("!game"):
            deletemsg(message)
            msgcut = messagestr[5:]
            print(msgcut)
            client.send_message(message.channel,"@everyone Does anyone want to play {}? ({})".format(str(msgcut),disauthor))
        # Credits
        elif messagestr.startswith("!credits"):
            deletemsg(message)
            client.send_message(message.channel, creditsmsg.format(bot=str(botvs)))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Cats are cute
        elif messagestr.startswith("!cats"):
            client.send_file(message.channel, "images/cattypo.gif")
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Lists all members in current server
        elif messagestr.startswith("!members"):
            client.send_message(message.channel, "<@" + disauthor.id + "> **Current members:**")
            count = 0
            members = ''
            for mem in client.get_all_members():
                count += 1
                mem = str(mem)
                if count != 1:
                    members += ', '
                members += mem
            final = "**Total : {count1} members.**".format(count1=count)
            client.send_message(message.channel, members)
            client.send_message(message.channel, final)
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Online users
#        elif messagestr.startswith("!online"):
#            count = 0
#            memberson = ""
#            member = discord.Member()
#            for mem in client.get_all_members():
#                if mem.status() != "offline":
#                    count += 1
#                    mem = str(mem)
#                    if count != 1:
#                        members += ', '
#                    members += mem
#            final = "**Total : {count1} online members.**".format(count1=count)
#            client.send_message(message.channel, memberson)
#            client.send_message(message.channel, final)
#            print(str("{} by {}".format(message.content,message.author)))
#            logdis(message)
        # Uptime
        elif messagestr.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = gettime(time_elapsed)
            client.send_message(message.channel, "<@" + disauthor.id + "> **Uptime: {upt} **".format(upt=converted))
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Says something
        elif messagestr.startswith("ayybot say"):
            msgcut = messagestr
        # Returns mentioned user's avatar, or if no mention present, yours.
        elif messagestr.startswith("!avatar"):
            deletemsg(message)
            if len(message.mentions) > 0:
                for user in message.mentions:
                    if user.avatar_url() != "":
                        client.send_message(message.channel, "<@" + user.id + ">'s avatar: " + user.avatar_url())
                    else:
                        client.send_message(message.channel, user.name + " doesn't have an avatar.")
            else:
                user2 = message.author
                client.send_message(message.channel,"<@" + disauthor.id + ">'s avatar: " + user2.avatar_url())
            print(str("{} by {}".format(message.content,message.author)))
            logdis(message)
        # Decides between two or more words
        elif messagestr.startswith("!decide"):
            deletemsg(message)
            msg3 = str(message.content.lower()[7:]).split()
            if randint(1,2) == 1:
                client.send_message(message.channel, "<@" + disauthor.id + "> I have decided: " + msg3[0])
            else:
                client.send_message(message.channel, "<@" + disauthor.id + "> I have decided: " + msg3[1])
                logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Answers your question - 8ball style
        elif messagestr.startswith("!8ball"):
            deletemsg(message)
            msg6 = str(message.content[6:])
            answer = eightball[randint(1,len(eightball))]
            client.send_message(message.channel,"<@" + disauthor.id + "> asked : " + msg6 + "\n**" + answer + "**")
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a gif matching the name from Giphy (!gif <name>)
        elif messagestr.startswith("!gif"):
            msg2 = str(message.content.lower()[4:])
            img = str(translate(msg2))
            client.send_message(message.channel, "<@" + disauthor.id + "> " + img)
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
                    avatar = user.avatar_url()
                    final = "`Name: " + name + "\nId: " + uid + "\nDiscriminator: " + discrim + "\nAvatar url: " + avatar + "`"
                    client.send_message(message.channel,final)
            else:
                client.send_message(message.channel, "Please mention someone to display their info")
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # Returns a random quote
        elif messagestr.startswith("!quote"):
            deletemsg(message)
            answer = quotes[randint(1,len(quotes))]
            client.send_message(message.channel,answer)
            logdis(message)
            print(str("{} by {}".format(message.content,message.author)))
        # For managing roles
        elif messagestr.startswith("!role"):
            role1 = discord.utils.find(lambda role: role.name == 'serveradmins', message.channel.server.roles)
            if message.author.id == message.channel.server.owner.id or role1:
                for dis in message.mentions:
                    user = discord.utils.find(lambda member: member.name == dis.name, message.channel.server.members)
                    splitcmd = message.content.split()
                    if "mod" in splitcmd:
                        role = discord.utils.find(lambda role: role.name == 'mods', message.channel.server.roles)
                        if role is not None:
                            client.replace_roles(user, role)
                            print('Changed a user to mod.')
                            logdis(message)
                            client.send_message(message.channel,'Successfully added ' + user.name + ' to mods.')
                    elif "removemod" in splitcmd:
                        role = discord.utils.find(lambda role: role.name == 'mods', message.channel.server.roles)
                        if role is not None:
                            client.remove_roles(user,role)
                            print("Removed permissions.")
                            logdis(message)
                            client.send_message(message.channel,'Successfully removed ' + user.name + ' from mods')
                    elif "member" in splitcmd:
                        role = discord.utils.find(lambda role: role.name == "members", message.channel.server.roles)
                        if role is not None:
                            client.replace_roles(user,role)
                            print("Changed permissions to member.")
                            logdis(message)
                            client.send_message(message.channel,"Changed " + user.name + "'s permissions to member.")
            else:
                logdis(message)
                print(str("{msg} by {usr}, but incorrect permissions".format(msg=message.content,usr=message.author)))
        elif messagestr.startswith("!wiki"):
            try:
                wikipage = wikipedia.summary(str(messagestr[5:]),sentences=2)
                client.send_message(message.channel,"*Wikipedia definition for* **" + messagestr[6:] + "** *:*\n" + wikipage)
            except wikipedia.exceptions.PageError:
                client.send_message(message.channel,"No definitions for " + messagestr[6:] + " were found")
        elif messagestr.startswith("!urban"):
            query = messagestr[6:]
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(query))
            purehtml = BeautifulSoup(define.content, "html.parser")
            client.send_message(message.channel,"*Urban definition for* **" + messagestr[6:] + "** *:*" + purehtml.find("div",attrs={"class":"meaning"}).text)
    except discord.InvalidArgument:
        print("Error -3 : InvalidArgument")
        client.send_message(message.channel, "Error -3 : InvalidArgument")
        client.send_message(message.channel, "Restarting, hold on...")
        os.system("python launchbot.py")
    except discord.ClientException:
        print("Error -1 : ClientException")
        print("Restarting, hold on...")
        client.send_message(message.channel, "Error -1 : ClientException")
        os.system("python launchbot.py")
    except discord.HTTPException:
        print("Error -2 : HTTPException")
        client.send_message(message.channel, "Error -2 : HTTPException")
        client.send_message(message.channel, "Restarting, hold on...")
        os.system("python launchbot.py")

@client.event
def on_ready():
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('------------------')

@client.event
def on_member_join(member):
    server = member.server
    client.send_message(server, 'Welcome to the server, {0}'.format(member.mention()))
    logdis("{one} joined the server".format(one=member))


# TIME
start_time = time.time()
# Write log line ----
if parser.getboolean("Settings","WriteLogs") == 1:
    with open('log.txt','a') as file:
        file.write("\n------------------------------\n".format(vs=botvs))

loginme()
runme()