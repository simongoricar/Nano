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