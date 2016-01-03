import discord
from random import randint
from config import things,eightball,helpmsg1,creditsmsg,jokemsg,memelist
from datetime import timedelta, datetime
import time
import configparser
from giphypop import translate
import wordfilter

__title__ = 'DiscordieBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.11'

# import logging
# logging.basicConfig(level=logging.DEBUG)
client = discord.Client()
clientchannel = discord.Channel()
botvs = "0.11"
parser = configparser.ConfigParser()
parser.read("settings.ini")

def runme():
    client.run()

def loginme():
    client.login('mail', 'pass')
loginme()

def logmeout():
    client.logout()

def deletemsg(message):
    client.delete_message(message)

def printout(message, disauthor):
    print('{msg} was executed by {usr}'.format(msg=str(message.content), usr=disauthor))

def gettime(time_elapsed):
    sec = timedelta(seconds=time_elapsed)
    d = datetime(1, 1, 1) + sec
    this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
    return this


def logdis(message):
    if parser.getboolean("SettingsOne", "WriteLogs") == 1:
        with open('log.txt',"a") as file2:
            one = str(time.strftime("%Y-%m-%d %H:%M:%S", ))
            str2 = one + str(" : {msg} by {usr}\n".format(msg=message.content,usr=message.author))
            file2.write(str2)


def checkwords(message):
    cmsg = str(message.content).lower()
    with open('filterwords.txt') as f:
        mylist = [line.rstrip('\n') for line in f]
    wordfilter.add_words(mylist)
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
    if another > 7:
        client.delete_message(message)
        client.send_message(message.channel,
                            "@{usr} Spam is not allowed. **Deal with it** ( ͡° ͜ʖ ͡°)".format(usr=message.author))
        print("A message by {usr} was filtered - spam".format(usr=message.author))

# TIME
start_time = time.time()

@client.event
def on_message(message):
    try:
        disauthor = message.author
        messagestr = str(message.content).lower()
        # Spam and swearing check / with settings.txt check in config.checksettings(parm=1 or 2)
        if parser.getboolean("SettingsOne", "FilterWords") == 1:
            checkwords(message)
        if parser.getboolean("SettingsOne", "FilterSpam") == 1:
            checkspam(message)
        # commands imported from config.py
        for onething in things.keys():
            if message.content.lower().startswith(onething):
                deletemsg(message)
                second = things.get(str(message.content.lower()))
                print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
                logdis(message)
                client.send_message(message.channel, second.format(usr=disauthor.id))
        if messagestr.startswith("!help"):
            deletemsg(message)
            if messagestr.startswith("!help useful") or messagestr == "!help":
                client.send_message(message.channel, helpmsg1)
            elif messagestr.startswith("!help fun"):
                client.send_message(message.channel, jokemsg)
            elif messagestr.startswith("!help meme") or messagestr.startswith("!help memes"):
                client.send_message(message.channel, memelist)
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Restart // will add permission check
        elif messagestr.startswith("!restart"):
            deletemsg(message)
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            client.send_message(message.channel, "<@" + disauthor.id + "> Restarting...")
            logdis(message)
            client.logout()
            loginme()
            runme()
            print("Should be properly restarted.")
        # They see me rollin'
        elif messagestr.startswith('!roll'):
            deletemsg(message)
            msg5 = message.content.lower()[6:]
            client.send_message(message.channel, "<@" + disauthor.id + "> rolled :" + str(randint(0, int(msg5))))
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        elif messagestr.startswith("!dice"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + "> You got: " + str(randint(0,6)) + "!")
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Credits.
        elif messagestr.startswith("!credits"):
            deletemsg(message)
            client.send_message(message.channel, creditsmsg)
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Shut down. // to do : add check for permissions.
        elif messagestr.startswith("!shutmedown"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + ">, DiscordieBot shutting down.")
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
            exit(-420)
        # Cats are cute
        elif messagestr.startswith("!cats"):
            deletemsg(message)
            client.send_file(message.channel, "images/cattypo.gif")
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Lists all members in current server
        elif messagestr.startswith("!listmembers"):
            deletemsg(message)
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
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Uptime
        elif messagestr.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = gettime(time_elapsed)
            client.send_message(message.channel, "<@" + disauthor.id + "> **Uptime: {upt} **".format(upt=converted))
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
        # Gets you an invite // doesnt work yet
        elif messagestr.startswith("!getinvite"):
            disinvite = client.create_invite(message.server)
            deletemsg(message)
            client.send_message(message.channel,"<@{usr}>, here is your code : {code} that expires in 24 hrs.".format(usr=disauthor.id,code=str(disinvite)))
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
            logdis(message)
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
            print(str("{msg} by {usr}".format(msg=message.content,usr=message.author)))
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
        # Answers your question - 8ball style
        elif messagestr.startswith("!8ball"):
            deletemsg(message)
            msg6 = str(message.content[6:])
            answer = eightball[randint(1,len(eightball))]
            client.send_message(message.channel,"<@" + disauthor.id + "> asked : " + msg6 + "\n**" + answer + "**")
            logdis(message)
        # Returns a gif matching the name from Giphy (!gif <name>)
        elif messagestr.startswith("!gif"):
            deletemsg(message)
            msg2 = str(message.content.lower()[4:])
            img = str(translate(msg2))
            client.send_message(message.channel, "<@" + disauthor.id + "> " + img)
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
    except discord.InvalidArgument:
        print("Error -3 : InvalidArgument")
        client.send_message(message.channel, "Error -3 : InvalidArgument")
        client.send_message(message.channel, "Restarting, hold on...")
        print("Restarting with runme(), hold on...")
        logmeout()
        loginme()
        runme()
    except discord.ClientException:
        print("Error -1 : ClientException")
        print("Restarting with runme(), hold on...")
        client.send_message(message.channel, "Error -1 : ClientException")
        client.send_message(message.channel, "Restarting, hold on...")
        logmeout()
        loginme()
        runme()
    except discord.HTTPException:
        print("Error -2 : HTTPException")
        client.send_message(message.channel, "Error -2 : HTTPException")
        client.send_message(message.channel, "Restarting, hold on...")
        print("Restarting with runme(), hold on...")
        logmeout()
        loginme()
        runme()

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

if parser.getboolean("SettingsOne","WriteLogs") == 1:
    with open('log.txt','a') as file:
        file.write("\n------------------------------\n".format(vs=botvs))

runme()
