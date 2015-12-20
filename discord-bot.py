__title__ = 'DiscordBot'
__author__ = 'DefaltSimon with discord.py api'
__version__ = '0.2'

import discord
from random import randint
#import logging
#logging.basicConfig(level=logging.DEBUG)
client = discord.Client()
def runme():
    client.run()
def loginme():
    client.login('mymail@gmail.com', 'mypass')
def logmeout():
    client.logout()
def deletemsg(message):
    client.delete_message(message)
loginme()

helpmsg = "Help: \n!help to display this message \n!hello bot says \"hello\" \n!roll to get random number between 0 and 100.\n!game bot asks if anyone wants to play games.\n" \
          "\n!who - to be implemented\n!credits - version info, author and API\n\n Type !help 2 for fun commands."
creditsmsg = "**DiscordBot 0.2** \nMade by *DefaltSimon* with the help of \"discord.py\" API(on github).\n"
jokemsg = "!ayy - ayy lmao\n!moreayy - even more ayy lmao mit dem lenny face\n!wot - u wot m8\n!synagoge - synagogß\n!thecakeisalie - want it?\n!cyka - russians"

@client.event
def on_message(message):
    try:
        if message.content.startswith('!hello'):
            client.send_message(message.channel, "Hi m8!")
            print("!hello was executed")
        elif message.content.startswith('!help'):
            client.send_message(message.channel, helpmsg)
            print("!help was executed")
        elif message.content.startswith("!help 2"):
            client.send_message(message.channel,jokemsg)
        elif message.content.startswith('!roll'):
            client.send_message(message.channel, "Rolled: " + str(randint(0, 100)))
            print("!roll was executed")
        elif message.content.startswith('!game'):
            client.send_message(message.channel, "@everyone Anyone wants to play games?", mentions="@everyone")
            print("!game was executed")
        elif message.content.startswith("!credits"):
            client.send_message(message.channel, creditsmsg)
            print("!credits was executed")
        elif message.content.startswith("!rickrolled"):
            client.send_message(message.channel, "DiscordBot shutting down. **U FAGS**")
            exit(-420)
        elif message.content.startswith('!ayy'):
            client.send_message(message.channel, "Ayyyyy lmao!")
            print("!ayy was executed")
        elif message.content.startswith('!moreayy'):
            client.send_message(message.channel, "Ayyyyyyyyyy lmao! ( ͡° ͜ʖ ͡°) 👾 ")
            print("!moreayy was executed")
        elif message.content.startswith('!wot'):
            client.send_message(message.channel, "U wot m8 ")
            print("!wot was executed")
        elif message.content.startswith('!synagoge'):
            client.send_message(message.channel, "DIE ALTEEH-SYNAGOGE")
            print("!synagoge was executed")
        elif message.content.startswith("!thecakeisalie"):
            client.send_message(message.channel, "Roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        elif message.content.startswith("!who"):
            client.send_message(message.channel, "*You.*")
        elif message.content.startswith("!cyka"):
            client.send_message(message.channel, "Cyka Blyat!")
        elif message.content.startswith("!listmembers"):
            count = 0
            members = []
            for mem in client.get_all_members():
                count = count + 1
                members.append(mem)
#                client.send_message(message.channel, mem)
            final = "**Done, Total :",count,"members.**"
            client.send_message(message.channel, (str(members),final))
            print("!listmembers was executed")
        elif message.content.startswith("!"):
            client.send_message(message.channel, "The command was not recognised.")
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
