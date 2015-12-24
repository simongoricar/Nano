__title__ = 'DiscordBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.4'

import discord
import time
from random import randint
from datetime import datetime, timedelta
#import logging

#logging.basicConfig(level=logging.DEBUG)
client = discord.Client()
clientchannel = discord.Channel()

def runme():
    client.run()
def loginme():
    client.login('mail', 'pass')
def logmeout():
    client.logout()
def deletemsg(message):
    client.delete_message(message)
loginme()

# TIME
start_time = time.time()
def Gettime(time_elapsed):
    sec = timedelta(seconds=time_elapsed)
    d = datetime(1,1,1) + sec
    this = "%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second)
    return this


def checkwords(message):
    data = [line.strip() for line in open("filterwords.txt", 'r')]
    msglist = (str(message.content).lower()).strip()
    for dis in data:
        if msglist.lower() in dis:
            client.send_message(message.channel, "Hey! Watch it!")
            print("A message by {usr} was filtered - swearing".format(usr=message.author))

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
        client.send_message(message.channel, "@{usr} Spam is not allowed. **Deal with it** ( ͡° ͜ʖ ͡°)".format(usr=message.author))
        print("A message by {usr} was filtered - spam".format(usr=message.author))

helpmsg1 = ("""\
Help:
!help 1 to display help message
!help 2 to display available funny messages
!hello bot says hi to you :)
!roll to get random number between 0 and 100
!game bot asks if anyone wants to play games
!who - to be implemented
!uptime tells you the uptime
!cats - so cute
!credits - version info, author and API
""")
creditsmsg = ("""\
**DiscordBot 0.3**
Made by *DefaltSimon* with the help of \"discord.py\" API(on github).
""")
jokemsg = ("""\
**Help, page 2:**
!ayy - ayy lmao
!moreayy - even more ayy lmao mit dem lenny face
!wot - u wot m8
!synagoge - much joke, such doge
!allstar just try it ( ͡° ͜ʖ ͡°)
!johncena dis too ( ͡° ͜ʖ ͡°)
!thecakeisalie - want it?
!cyka - russian
""")

@client.event
def on_message(message):
    try:
        #1
        disauthor = message.author
        checkwords(message)
        checkspam(message)
        if message.content.startswith('!hello'):
            deletemsg(message)
            client.send_message(message.channel, 'Hi, @{id}'.format(id=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!help"):
            client.send_message(message.channel, helpmsg1)
        elif message.content.startswith('!help 1'):
            client.send_message(message.channel, helpmsg1)
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!help 2"):
            client.send_message(message.channel, jokemsg)
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith('!roll'):
            notworkyet = "@{user}, this function does not fully work yet."
            client.send_message(message.channel, notworkyet.format(user=message.author))
            dis = ""
            msg2 = str(message.content)
            for c in msg2:
                if c == "!" or "r" or "o" or "l" or " ":
                    continue
                else:
                    dis = dis + c
                    dis = int(dis)
                    print(dis)
            client.send_message(message.channel, randint(0,100))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith('!game'):
            deletemsg(message)
            client.send_message(message.channel, "@everyone Anyone wants to play games?", mentions="@everyone")
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!johncena"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} O_O https://www.youtube.com/watch?v=58mah_0Y8TU".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!credits"):
            client.send_message(message.channel, creditsmsg)
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!allstar"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} https://www.youtube.com/watch?v=L_jWHffIx5E".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!rickrolled"):
            deletemsg(message)
            print(clientchannel.permissions_for(disauthor))
            if clientchannel.permissions_for(disauthor) == "serveradmin":
                client.send_message(message.channel, "*@{user}* DiscordBot shutting down.".format(user=disauthor))
                print('{msg} was executed by {usr}, quitting'.format(msg=str(message.content),usr=disauthor))
            else:
                client.send_message(message.channel, "You don't have correct permissions to execute this command.")
                print('{msg} was executed by {usr}, but he didn"t have correct permissions'.format(msg=str(message.content),usr=disauthor))
            client.send_message(message.channel, "*@{user}* DiscordBot shutting down.".format(user=disauthor))
            print('{msg} was executed by {usr}, quitting'.format(msg=str(message.content),usr=disauthor))
            exit(-420)
        elif message.content.startswith('!ayy'):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Ayyyyy lmao!".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith('!moreayy'):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Ayyyyyyyyyy lmao! ( ͡° ͜ʖ ͡°) 👾 ".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith('!wot'):
            deletemsg(message)
            client.send_message(message.channel, "U wot @{usr} ".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!cats"):
            deletemsg(message)
            client.send_file(message.channel,"cattypo.gif")
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith('!synagoge'):
            deletemsg(message)
            client.send_message(message.channel, "DIE ALTEE-SYNAGOGE")
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!thecakeisalie"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!who"):
            client.send_message(message.channel, "@{user} Can't manipulate strings. Not yet. Soon.".format(user=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!cyka"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Cyka Blyat!".format(usr=disauthor))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        #2
        elif message.content.startswith("!listmembers"):
            client.send_message(message.channel, "@{usr} **Current members:**".format(usr=disauthor))
            deletemsg(message)
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
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = Gettime(time_elapsed)
            client.send_message(message.channel, "@{usr} **Uptime: {uptime} **".format(usr=disauthor,uptime=converted))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!getinvite"):
            deletemsg(message)
            def disinvite(message):
                client.create_invite(message.server,max_age=86400)
#            dis = client.create_invite(message.server, max_age=86400)
            client.send_message(message.channel, "@{usr}, here is your code : {code} that expires in 24 hrs.".format(usr=disauthor,code=str(disinvite(message))))
            print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
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
#        logmeout()
#        loginme()
        runme()
@client.event
def on_ready():
    print('Logged in as:')
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('------------------')


@client.event
def on_member_join(member):
    server = member.server
    client.send_message(server, 'Welcome, {0}'.format(member.mention()))

runme()
