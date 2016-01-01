__title__ = 'DiscordieBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.8'

import discord
import time
from random import randint
from datetime import datetime, timedelta
from time import strftime
from scommands import *
import os
# import logging
# logging.basicConfig(level=logging.DEBUG)
client = discord.Client()
clientchannel = discord.Channel()
botvs = "0.8"

def runme():
    client.run()

def loginme():
    client.login('mail', 'pass')

def logmeout():
    client.logout()

def deletemsg(message):
    client.delete_message(message)

def printout(message, disauthor):
    print('{msg} was executed by {usr}'.format(msg=str(message.content), usr=disauthor))

loginme()
# TIME
start_time = time.time()

def Gettime(time_elapsed):
    sec = timedelta(seconds=time_elapsed)
    d = datetime(1, 1, 1) + sec
    this = "%d:%d:%d:%d" % (d.day - 1, d.hour, d.minute, d.second)
    return this

def checkwords(message):
    cmsg = str(message.content).strip()
    with open('filterwords.txt') as f:
        mylist = [line.rstrip('\n') for line in f]
    for bads in mylist:
        if bads in cmsg and message.author != "AyyBot":
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

def checksettings(parm):
    with open('settings.txt') as a:
        appsettings = [line.rstrip('\n') for line in a]
    if parm == 1:
        if appsettings[0] == "FilterWords: yes":
            return 1
        else:
            return 0
    if parm == 2:
        if appsettings[1] == "FilterSpam: yes":
            return 1
        else:
            return 0

with open('log.txt','a') as file:
    file.write("\n------------------------------\n".format(vs=botvs))

def logdis(message):
    with open('log.txt',"a") as file:
        one = str(strftime("%Y-%m-%d %H:%M:%S", ))
        str2 = one + str(" : {msg} by {usr}".format(msg=message.content,usr=message.author))
        print(str2)
        file.write(str2)

helpmsg1 = ("""\
Help:
!help 1 - displays available commads (almost all)
!help 2 - funny commands
!hello - says hi
!roll - random number between 0 and 100
!dice - like !roll but 0 - 6
!listmembers - displays all members on the server
!uptime - displays bot uptime
!getinvite - returns an invite for the server/channel
!avatar ""@<usr>"" or "me" - returns a link to your/mentioned person's avatar
!restart - restarts the bot
!credits - author, etc.
""")
creditsmsg = ("""\
**DiscordBot 0.8**
Made by *DefaltSimon* with the help of \"discord.py\" API(on github).
""")
jokemsg = ("""\
**Help, page 2:**
!johncena - meme
!allstar - all star song
!game - mentions everyone and asks about playing a game
!ayy - ayy lmao
!moreayy - even more ayy with lenny
!wot - idk why I added this
!synagoge - just a friend's joke
!thecakeisalie - get rick roll'd
!cats - aren't they cute?
""")

@client.event
def on_message(message):
    try:
        disauthor = message.author
        # Spam and swearing check / with settings.txt check in checksettings(parm=1 or 2)
        if checksettings(parm=1) == 1:
            checkwords(message)
        if checksettings(parm=2) == 1:
            checkspam(message)
        # commands imported from scommands.py
        for onething in things.keys():
            if message.content.startswith(onething):
                deletemsg(message)
                second = things.get(str(message.content))
                logdis(message)
                client.send_message(message.channel, second.format(usr=disauthor.id))
        # Help
        if message.content.startswith("!help"):
            client.send_message(message.channel, helpmsg1)
            logdis(message)
        elif message.content.startswith('!help 1'):
            client.send_message(message.channel, helpmsg1)
            logdis(message)
        elif message.content.startswith("!help 2"):
            client.send_message(message.channel, jokemsg)
            logdis(message)
        # Restart // will add permission check
        elif message.content.startswith("!restart"):
            client.send_message(message.channel, "<@" + disauthor.id + "> Restarting...")
            client.logout()
            loginme()
            runme()
            os.system('clear')
            print("Should be properly restarted.")
            logdis(message)
        # They see me rollin' // kinda works
        elif message.content.startswith('!roll'):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + "> rolled :" + randint(0, 100))
            logdis(message)
        elif message.content.startswith("!dice"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + "> You got: " + str(randint(0,6)) + "!")
        # Credits.
        elif message.content.startswith("!credits"):
            deletemsg(message)
            client.send_message(message.channel, creditsmsg)
            logdis(message)
        # Shut down. // to do : add check for permissions.
        elif message.content.startswith("!shutmedown"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + ">, DiscordieBot shutting down.")
            exit(-420)
            logdis(message)
        # Cats are cute
        elif message.content.startswith("!cats"):
            deletemsg(message)
            client.send_file(message.channel, "cattypo.gif")
            printout(message, disauthor)
        # Lists all members in current server
        elif message.content.startswith("!listmembers"):
            deletemsg(message)
            client.send_message(message.channel, "<@" + disauthor.id + "> **Current members:**")
            count = 0
            members = ''
            for mem in client.get_all_members():
                count = count + 1
                mem = str(mem)
                if count != 1:
                    members += ', '
                members += mem
            final = "**Total : {count1} members.**".format(count1=count)
            client.send_message(message.channel, members)
            client.send_message(message.channel, final)
            logdis(message)
        # Uptime
        elif message.content.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = Gettime(time_elapsed)
            client.send_message(message.channel, "<@" + disauthor.id + "> **Uptime: {upt} **".format(upt=converted))
            logdis(message)
        # Gets you an invite // doesnt work yet
        elif message.content.startswith("!getinvite"):
            disinvite = client.create_invite(message.server)
            deletemsg(message)
            client.send_message(message.channel,
                                "<@{usr}>, here is your code : {code} that expires in 24 hrs.".format(usr=disauthor.id,code=str(disinvite)))
            logdis(message)
        # If followed by "me", returns yours, otherwise mentioned user's avatar
        elif message.content.startswith("!avatar"):
            deletemsg(message)
            if message.content.startswith("!avatar me"):
                user2 = message.author
                client.send_message(message.channel,"<@" + disauthor.id + ">'s avatar: " + user2.avatar_url())
            if len(message.mentions) > 0:
                for user in message.mentions:
                    if user.avatar_url() != "":
                        client.send_message(message.channel, "<@" + user.id + ">'s avatar: " + user.avatar_url())
                    else:
                        client.send_message(message.channel, user.name + " doesn't have an avatar.")
            else:
                if message.content.startswith() != "!avatar me":
                    client.send_message(message.channel, message.author.mention() + " Mention the users you want to get avatars from.")
            logdis(message)
            ####End of commands###
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

runme()
