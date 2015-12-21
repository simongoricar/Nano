__title__ = 'DiscordBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.3'

# discord.py API is required
# install with :
# pip install discord.py

import discord
from random import randint
import reprlib
#import logging
#logging.basicConfig(level=logging.DEBUG)
client = discord.Client()
def runme():
    client.run()
def loginme():
    client.login('mail', 'pass')
def logmeout():
    client.logout()
def deletemsg(message):
    client.delete_message(message)
loginme()

helpmsg1 = ("""\
Help:
!help 1 to display help message
!help 2 to display available funny messages
!hello bot says hi to you :)
!roll to get random number between 0 and 100
!game bot asks if anyone wants to play games
!who - to be implemented
!credits - version info, author and API
""")
creditsmsg = ("""\
**DiscordBot 0.2**
Made by *DefaltSimon* with the help of \"discord.py\" API(on github).
""")
jokemsg = ("""\
**Help, page 2:**
!ayy - ayy lmao
!moreayy - even more ayy lmao mit dem lenny face
!wot - u wot m8
!synagoge - much joke, such doge
!thecakeisalie - want it?
!cyka - russian
""")

@client.event
def on_message(message):
    try:
        #1
        disauthor = message.author
        msgstr = str(message)
        if message.content.startswith('!hello'):
            deletemsg(message)
            client.send_message(message.channel, 'Hi, @{id}'.format(id=disauthor))
            print(str("{msg} was executed".format(msg=msgstr)))
        elif message.content.startswith("!help"):
            client.send_message(message.channel, helpmsg1)
        elif message.content.startswith('!help 1'):
            client.send_message(message.channel, helpmsg1)
            print("!help 1 was executed")
        elif message.content.startswith("!help 2"):
            client.send_message(message.channel, jokemsg)
            print("!help 2 was exectuted")
        elif message.content.startswith('!roll'):
            notworkyet = "@{user}, this function does not fully work yet."
            client.send_message(message.channel, notworkyet.format(user=message.author))
            client.send_message(message.channel, randint(0,100))
            print('{msg} was executed'.format(msgstr))
        elif message.content.startswith('!game'):
            deletemsg(message)
            client.send_message(message.channel, "@everyone Anyone wants to play games?", mentions="@everyone")
            print("!game was executed")
        elif message.content.startswith("!johncena"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} O_O https://www.youtube.com/watch?v=58mah_0Y8TU".format(usr=disauthor))
            print("!johncena was executed")
        elif message.content.startswith("!credits"):
            client.send_message(message.channel, creditsmsg)
            print("!credits was executed")
        elif message.content.startswith("!allstar"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} https://www.youtube.com/watch?v=L_jWHffIx5E".format(usr=disauthor))
        elif message.content.startswith("!rickrolled"):
            deletemsg(message)
            client.send_message(message.channel, "*@{user}* DiscordBot shutting down.".format(user=disauthor))
            exit(-420)
        elif message.content.startswith('!ayy'):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Ayyyyy lmao!".format(usr=disauthor))
            print("!ayy was executed")
        elif message.content.startswith('!moreayy'):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Ayyyyyyyyyy lmao! ( ͡° ͜ʖ ͡°) 👾 ".format(usr=disauthor))
            print("!moreayy was executed")
        elif message.content.startswith('!wot'):
            deletemsg(message)
            client.send_message(message.channel, "U wot @{usr} ".format(usr=disauthor))
            print("!wot was executed")
        elif message.content.startswith('!synagoge'):
            deletemsg(message)
            client.send_message(message.channel, "DIE ALTEEH-SYNAGOGE")
            print("!synagoge was executed")
        elif message.content.startswith("!thecakeisalie"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ".format(usr=disauthor))
        elif message.content.startswith("!who"):
            client.send_message(message.channel, "@{user} Can't manipulate strings. Not yet. Soon.".format(user=disauthor))
        elif message.content.startswith("!cyka"):
            deletemsg(message)
            client.send_message(message.channel, "@{usr} Cyka Blyat!".format(usr=disauthor))
            print("!cyka was executed")
        #2
        elif message.content.startswith("!listmembers"):
            client.send_message(message.channel, "@{usr} -".format(usr=disauthor))
            client.send_message(message.channel, "**Current members:**")
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
            print("!listmembers was executed")
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
