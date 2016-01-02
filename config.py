__name__ = "AyyBot simple commands list"

things = {
    "!hello": "Hi, <@{usr}>",
    "!test": "<@{usr}> Ayy test works!",
    "!johncena": "<@{usr}> O_O https://www.youtube.com/watch?v=58mah_0Y8TU",
    "!allstar": "<@{usr}> https://www.youtube.com/watch?v=L_jWHffIx5E",
    "!game": "@everyone Does anyone want to play games?",
    "!ayy": "<@{usr}> Ayyyyy lmao!",
    "!moreayy": "<@{usr}> Ayyyyyyyyyy lmao! ( ͡° ͜ʖ ͡°) 👾 ",
    "!wot": "U wot <@{usr}>",
    "!synagoge": "DIE ALTEE-SYNAGOGE",
    "!thecakeisalie": "<@{usr}> : Rick roll'd https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "!who": "<@{usr}> Can't manipulate strings. Not yet. Soon."
}
'''
settings.ini :

FilterWords: 1 or 0 (filters words in filterwords.txt)
FilterSpam: 1 or 0 (filters spam)
WriteLogs: 1 or 0 (writes logs to log.txt)


Adding commands:

Just add them with the help of a template:

"<yourtriggercommand>": "<whatYouWantToPrint>",
                                              ^ everywhere except the last line

The second can include <@{usr}> to mention the author.
Use \n anywhere for new line in the same message.
'''

eightball = [
    "It is certain","It is surely so","Without a doubt","You may rely on it","Most likely","Yes",
    "Ask again later","Cannot predict now","Concentrate and ask again","I would say yes","JUST DO IT",
    "My replay is no","My sources say no","Signs point to yes"]

helpmsg1 = ("""\
Help:
!help useful - displays available commands
!help fun - funny commands
!hello - says hi
!listmembers - displays all members on the server
!uptime - displays bot uptime
!getinvite - returns an invite for the server/channel
!avatar ""@<usr>"" returns a link to mentioned person's avatar or yours if there is no mention
!user @mention - returns info about the user
!restart - restarts the bot
!credits - author, etc.
""")
creditsmsg = ("""\
**DiscordBot 0.9**
Made by *DefaltSimon* with the help of \"discord.py\" API(on github).
""")
jokemsg = ("""\
**Help, fun commands:**
!gif <name> - returns a gif from Giphy
!roll <number> - random number
!dice - like !roll but 0 - 6
!decide word word - decides between two words
""")

memelist = ("""\
**Help, meme list:**
!ayy - ayy lmao
!moreayy - even more ayy lmao with lenny face
!wot - u wot m8
!allstar just try it ( ͡° ͜ʖ ͡°)
!johncena dis too ( ͡° ͜ʖ ͡°)
!thecakeisalie - want it?
""")