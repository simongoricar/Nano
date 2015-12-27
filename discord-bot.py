__title__ = 'DiscordBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.5'

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
def disinvite(message):
    client.create_invite(message.server,max_age=86400)
def printout(message,disauthor):
    print('{msg} was executed by {usr}'.format(msg=str(message.content),usr=disauthor))
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

things = {
    "!hello" : "Hi, @{usr}",
    "!test" : "@{usr} Ayy test works!",
    "!johncena" : "@{usr} O_O https://www.youtube.com/watch?v=58mah_0Y8TU",
    "!allstar" : "@{usr} https://www.youtube.com/watch?v=L_jWHffIx5E",
    "!game" : "@everyone Does anyone want to play games?",
    "!ayy" : "@{usr} Ayyyyy lmao!",
    "!moreayy" : "@{usr} Ayyyyyyyyyy lmao! ( ͡° ͜ʖ ͡°) 👾 ",
    "!wot" : "U wot @{usr}",
    "!synagoge" : "DIE ALTEE-SYNAGOGE",
    "!thecakeisalie" : "@{usr} : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "!cyka" : "@{usr} Cyka Blyat!",
    "!who" : "@{user} Can't manipulate strings. Not yet. Soon."
}

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
!getinvite - will work in the future
!listmembers lists all members in this server
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
!synagoge - much joke, such laugh
!allstar just try it ( ͡° ͜ʖ ͡°)
!johncena dis too ( ͡° ͜ʖ ͡°)
!thecakeisalie - want it?
!cyka - russian
""")

@client.event
def on_message(message):
    try:
        disauthor = message.author
        # Spam and swearing check
        checkwords(message)
        checkspam(message)
        # Dict check (fun commands)
        for onething in things.keys():
            if message.content.startswith(onething):
                deletemsg(message)
                second = things.get(str(message.content))
                printout(message,disauthor)
                client.send_message(message.channel, second.format(usr=disauthor))
        # Help
        if message.content.startswith("!help"):
            client.send_message(message.channel, helpmsg1)
        elif message.content.startswith('!help 1'):
            client.send_message(message.channel, helpmsg1)
            print('{msg} - {usr}'.format(msg=str(message.content),usr=disauthor))
        elif message.content.startswith("!help 2"):
            client.send_message(message.channel, jokemsg)
            print('{msg} - {usr}'.format(msg=str(message.content),usr=disauthor))
        # They see me rollin' // kinda works
        elif message.content.startswith('!roll'):
            client.send_message(message.channel, "@{user}, this function does not fully work yet.".format(user=message.author))
#            dis = ""
#            for char in str(message.content):
#                if char == "!" or "r" or "o" or "l" or " ":
#                    break
#                else:
#                    dis = dis + str(char)
#            print(dis)
            client.send_message(message.channel, randint(0,100))
            printout(message,disauthor)
        # Credits.
        elif message.content.startswith("!credits"):
            client.send_message(message.channel, creditsmsg)
            printout(message,disauthor)
        # Shut down.
        elif message.content.startswith("!adminshutdown"):
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
            printout(message,disauthor)
        # Cats are cute
        elif message.content.startswith("!cats"):
            deletemsg(message)
            client.send_file(message.channel,"cattypo.gif")
            printout(message,disauthor)
        # Lists all members is current server
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
            printout(message,disauthor)
        # Uptime
        elif message.content.startswith("!uptime"):
            deletemsg(message)
            time_elapsed = time.time() - start_time
            converted = Gettime(time_elapsed)
            client.send_message(message.channel, "@{usr} **Uptime: {uptime} **".format(usr=disauthor,uptime=converted))
            printout(message,disauthor)
        # Gets you an invite // doesnt work yet
        elif message.content.startswith("!getinvite"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr}, here is your code : {code} that expires in 24 hrs.".format(usr=disauthor,code=str(disinvite(message))))
            printout(message,disauthor)
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
    print('Logged in as:')
    print("Username:", client.user.name)
    print("ID:", client.user.id)
    print('------------------')


@client.event
def on_member_join(member):
    server = member.server
    client.send_message(server, 'Welcome, {0}'.format(member.mention()))

runme()