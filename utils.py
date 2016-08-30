# coding=utf-8

__author__ = "DefaltSimon"
# Messages file for Nano


messagelist = {
    "_rip": "Rest in *peperoni* indeed.",
    "nano.prefix": "The prefix to use is **_**",
    "_prefix": "You guessed it!",
    "ayy lmao": "Ayy lmao, my great inspiration in the world of memes.",
    "_cat": "meow! https://gif-avatars.com/img/90x90/cattypo.gif",
    "_cmds": "A 'complete' list of commands is available here: https://github.com/DefaltSimon/Nano/wiki/Commands-list"
}


helpmsg = """**Hey, I'm Nano!**

To get familiar with simple commands, type `>help simple`.
If you want specific info about a command, do `>help command`.

Or you could just simply take a look at my wiki page: https://github.com/DefaltSimon/Nano/wiki/Commands-list
If you are an admin and want to set up your server for Nano, type `>getstarted`.
If you need additional help, you can visit "my official server" : https://discord.gg/FZJB6UJ
"""

simples = """`_hello` - Welcomes you or the mentioned person.
`_randomgif` - Posts a random gif from Giphy
`_roll number` - rolls a random number
`_wiki term` - gives you a description of a term from Wikipedia
`_urban term` - gives you a description of a term from Urban Dictionary
`_decide option|option...` - decides between your options so you don't have to
`_tf item_name` - item prices from backpack.tf
`_steam user_id` - search users on Steam

These are just a few of some of the simpler commands. For more info about each command, use `_help command` or type `_cmds` to look at the wiki page with all the commands."""

# Template: {"desc": "", "use": None, "alias": None},
commandhelpsnormal = {
    "_help": {"desc": "This is here.", "use": None, "alias": None},
    "_hello": {"desc": "Welcomes a **mentioned** person, or if no mentions are present, you.", "use": "Use: <command> <mention>", "alias": None},
    "_uptime": {"desc": "Tells you for how long I have been running.", "use": None, "alias": None},
    "_randomgif": {"desc": "Sends a random gif from Giphy.", "use": None, "alias": None},
    "_8ball": {"desc": "Answers your question. 8ball style.", "use": "Use: <command> <question>", "alias": None},
    "_wiki": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "Use: <command> <word>", "alias": "Aliases: _define"},
    "_define": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "Use: <command> <word>", "alias": "Aliases: _wiki"},
    "_urban": {"desc": "Gives you the definition of a word from Urban Dictionary.", "use": "Use: <command> <word>", "alias": None},
    "_avatar": {"desc": "Gives you the avatar url of a mentioned person", "use": "Use: <command> <mention or name>", "alias": None},
    "_ping": {"desc": "Just to check if I'm alive. fyi: I love ping-pong.", "use": None, "alias": None},
    "_roll": {"desc": "Replies with a random number in range from 0 to your number.", "use": "Use: <command> <number>", "alias": None},
    "_ayybot": {"desc": "A little info about me.", "use": None, "alias": "Alias: `nano.info`"},
    "_github": {"desc": "Link to my project on GitHub.", "use": None, "alias": None},
    "_decide": {"desc": "Decides between different choices so you don't have to.", "use": "Use: <command> word1|word2|word3|...", "alias": None},
    "_cmd list": {"desc": "Returns a server-specific command list.", "use": None, "alias": None},
    "_cat": {"desc": "I love cats. And this is a gif of a cat.", "use": None, "alias": None},
    "_kappa": {"desc": "I couldn't resist it.", "use": None, "alias": None},
    "_johncena": {"desc": "I have to remove this someday. dun dun dun dun, dun dun dun dun", "use": None, "alias": None},
    "_rip": {"desc": "Rest in peperoni, man.", "use": "Use: <command> <mention>", "alias": None},
    "ayy lmao": {"desc": "Yes, it'stm the ayy lmao meme.", "use": None, "alias": None},
    "_music join": {"desc": "Joins a voice channel.", "use": "Use: <command> <channel name>", "alias": None},
    "_music leave": {"desc": "Leaves a music channel.", "use": None, "alias": None},
    "_music volume": {"desc": "Returns the current volume or sets one.", "use": "Use: <command> <volume 0-150>", "alias": None},
    "_music pause": {"desc": "Pauses the current song.", "use": None, "alias": None},
    "_music resume": {"desc": "Resumes the paused song", "use": None, "alias": None},
    "_music skip": {"desc": "Skips the current song.", "use": None, "alias": "Alias: `_music stop`"},
    "_music stop": {"desc": "Skips the current song", "use": None, "alias": "Alias: `_music skip`"},
    "_music playing": {"desc": "Gives you info about the current song.", "use": None, "alias": None},
    "_music help": {"desc": "Some help with all the music commands.", "use": None, "alias": None},
    "_prefix": {"desc": "No use whatsoever, but jk here you have it.", "use": None, "alias": None},
    "_vote": {"desc": "One up for your choice, if there'stm a vote running.", "use": "Use: <command> <choice>", "alias": None},
    "_status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "Alias: nano.status"},
    "nano.status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "Alias: _status"},
    "_stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "Alias: nano.stats"},
    "nano.stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "Alias: _stats"},
    "_bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "Alias: nano.bug"},
    "nano.bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "Alias: _bug"},
    "_feature": {"desc": "Place where you can submit your ideas for this bot", "use": None, "alias": None},
    "nano.info": {"desc": "A little info about me.", "use": None, "alias": "Alias: _ayybot"},
    "nano.prefix": {"desc": "Helps you figure out the prefix.", "use": None, "alias": None},
    "_changes": {"desc": "A list of changes in the recent versions.", "use": None, "alias": "Alias: _changelog"},
    "_changelog": {"desc": "A list of changes in the recent versions.", "use": None, "alias": "Alias: _changes"},
    "_steam": {"desc": "Searches for the specified steam id.\nSubcommands: 'steam games', 'steam friends'", "use": "Use: <command> <end of user url/id>", "alias": None},
    "_steam games": {"desc": "Searches for all owned games in user'stm account.", "use": "Use: <command> <end of user url/id>", "alias": None},
    "_steam friends": {"desc": "Searches for all friends that the user has.", "use": "Use: <command> <end of user url/id>", "alias": None},
    "_mc": {"desc": "Searches for items and displays their details", "use": "Use: <command> <item name or id:meta>", "alias": "Alias: _minecraft"},
    "_minecraft": {"desc": "Searches for items and displays their details", "use": "Use: <command> <item name or id:meta>", "alias": "Alias: _mc"},
    "_tf": {"desc": "Gets item prices from backpack.tf (not perfect for items with unusual effects/shines)", "use": "Use: <command> <item name>", "alias": None},
    "_quote": {"desc": "Brightens your day with a random quote.", "use": None, "alias": None},
    "_notifydev": {"desc": "Sends a message to the developer", "use": "Use: <command> <message>", "alias": "Alias: _suggest"},
    "_suggest": {"desc": "Sends a message to the developer", "use": "Use: <command> <message>", "alias": "Alias: _notifydev"},
    "_remind": {"desc": "General module for timers\nSubcommands: remind me in, remind here in, remind list, remind remove", "use": None, "alias": None},
    "_remind me": {"desc": "Subcommands: remind me in, remind here in", "use": None, "alias": None},
    "_remind me in": {"desc": "Adds a reminder (reminds you in dm)", "use": "Use: <command> [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind here in": {"desc": "Adds a reminder (reminds everybody in current channel)", "use": "Use: <command> [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind list": {"desc": "Displays all ongoing timers.", "use": None, "alias": None},
    "_remind remove": {"desc": "Removes a timer with supplied description or time (or all timers with 'all')", "use": "Use: <command> [timer description or time in sec]", "alias": None},
}

commandhelpsadmin = {
    "_ban": {"desc": "Bans a member.", "use": "Use: <command> <mention>", "alias": "Alias: nano.ban"},
    "nano.ban": {"desc": "Bans a member.", "use": "User: <command> <mention>", "alias": "Alias: _ban"},
    "_kick": {"desc": "Kicks a member.", "use": "Use: <command> <mention>", "alias": "Alias: nano.kick"},
    "nano.kick": {"desc": "Kicks a member", "use": "Use: <command> <mention>", "alias": "Alias: _kick"},
    "_unban": {"desc": "Unbans a member.", "use": "Use: <command> <mention>", "alias": "Alias: nano.unban"},
    "nano.unban": {"desc": "Unbans a member.", "use": "Use: <command> <mention>", "alias": "Alias: _unban"},
    "_softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "Use: <command> <time> @mention", "alias": "Alias: nano.softban"},
    "nano.softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "Use: <command> <time> @mention", "alias": "Alias: _softban"},
    "_role add": {"desc": "Adds a role to the user.", "use": "Use: <command> <role name> <mention>", "alias": None},
    "_role remove": {"desc": "Removes a role from the user.", "use": "Use: <command> <role name> <mention>", "alias": None},
    "_role replacewith": {"desc": "Replace all roles with the specified one for a user.", "use": "Use: <command> <role name> <mention>", "alias": None},
    "_cmd add": {"desc": "Adds a command to the server.", "use": "Use: <command> command|response", "alias": None},
    "_cmd remove": {"desc": "Removes a command from the server.", "use": "Use: <command> command", "alias": None},
    "_invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "use": None, "alias": "Alias: nano.invite"},
    "_vote start": {"desc": "Starts a vote on the server.", "use": "Use: <command> \"question\" choice1|choice2|...", "alias": None},
    "_vote end": {"desc": "Simply ends the current vote on the server.", "use": None, "alias": None},
    "_getstarted": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "use": None, "alias": "Alias: nano.getstarted"},
    "_user": {"desc": "Gives info about the user", "use": "Use: <command> <mention or name>", "alias": None},
    "_reload": {"desc": "Restricted to owner, reloads all settings from config file.", "use": None, "alias": "Alias: nano.reload"},
    "nano.serversetup": {"desc": "(Re)sets all server related bot settings to default.", "use": None, "alias": "Alias: nano.server.setup"},
    "nano.server.setup": {"desc": "(Re)sets all server related bot settings to default.", "use": None, "alias": "Alias: nano.serversetup"},
    "nano.admins add": {"desc": "Adds a user to admins on the server.", "use": "Use: <command> <mention>", "alias": None},
    "nano.admins remove": {"desc": "Removes a user from admins on the server.", "use": "Use: <command> <mention>", "alias": None},
    "nano.admins list": {"desc": "Lists all admins on the server.", "use": None, "alias": None},
    "nano.sleep": {"desc": "Puts Nano to sleep. (per-server basis)", "use": None, "alias": None},
    "nano.wake": {"desc": "Wakes Nano up. (per-server basis)", "use": None, "alias": None},
    "nano.invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "use": None, "alias": "Alias: _invite"},
    "nano.settings": {"desc": "Sets server settings like word and spam filtering, enables or disables welcome message and ban announcement", "use": "Use: <command> <setting> True/False", "alias": None},
    "nano.displaysettings": {"desc": "Displays all server settings.", "use": None, "alias": None},
    "nano.blacklist add": {"desc": "Adds a channel to command blacklist.", "use": "Use: <command> <channel name>", "alias": None},
    "nano.blacklist remove": {"desc": "Removes a channel from command blacklist", "use": "Use: <command> <channel name>", "alias": None},
    "nano.getstarted": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "use": None, "alias": "Alias: _getstarted"},
    "nano.changeprefix": {"desc": "Changes the prefix on the server.", "use": "Use: <command> prefix", "alias": None},
    "_mute": {"desc": "Mutes the user - deletes all future messages from the user until he/she is un-muted.", "use": "Use: <command> <mention or name>", "alias": None},
    "_unmute": {"desc": "Un-mutes the user (see mute help for more info).", "use": "Use: <command> <mention or name>", "alias": None},
    "_muted": {"desc": "Displays a list of all members currently muted.", "use": None, "alias": None},
    "_purge": {"desc": "Deletes the messages from the specified user in the last x messages", "use": "Use: <command> <amount> <user name>", "alias": None},
    "_welcomemsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @userthatjoined, ':server' = server name", "use": "Use: <command> <content>", "alias": None},
    "_banmsg": {"desc": "Sets the message sent when a member is banned.\nFormatting: ':user' = user name", "use": "Use: <command> <content>", "alias": None},
    "_kickmsg": {"desc": "Sets the message sent when a member is kicked.\nFormatting: ':user' = user name", "use": "Use: <command> <content>", "alias": None},
    "_nuke": {"desc": "Nukes (deletes) last x messages.", "use": None, "alias": None},
}

commandhelpsowner = {
    "_playing": {"desc": "Restricted to owner(!), changes 'playing' status.", "use": "Use: <command> <status>", "alias": None},
    "nano.kill": {"desc": "Restricted to owner, shuts down the bot.", "use": "Use: <command>", "alias": None},
    "nano.restart": {"desc": "Restricted to owner, restarts down the bot.", "use": "Use: <command>", "alias": None},
    "nano.reload": {"desc": "Restricted to owner, reloads all settings from config file.", "use": None, "alias": "Alias: _reload"},
}



nanoinfo = """**Hey! My name is Nano!**
I have a GitHub repo! `!github`
My version is **<version>**.
I have been coded by *DefaltSimon*.
"""

githubinfo = """Nano is being maintained and updated on **GitHub**
Repo link: https://github.com/DefaltSimon/Nano
"""

appinfo = """You wanna invite Nano to your server, eh? Sure man.
**Here's the link:** <link>
"""


musichelp = """"**Music Help:**
```_music join <channel name> - joins the channel
_music play <yt url> - starts playing
_music pause/resume - pauses/resumes
_music skip/stop - skips the current song
_music playing - info
_music leave - leaves the voice channel if in one```"""""

bugreport = "Found a bug? Please report it to **DefaltSimon** on Discord.\n1. You may find him here: https://discord.gg/FZJB6UJ\n2. For small things you can simply use _notifydev [message]"

featurereq = "Got an idea for a feature? Submit it here: https://discord.gg/FZJB6UJ"


quotes = [
    "You miss 100% of the shots you don’t take. –Wayne Gretzky",
    "The most difficult thing is the decision to act, the rest is merely tenacity. –Amelia Earhart",
    "Twenty years from now you will be more disappointed by the things that you didn’t do than by the ones you did do, so throw off the bowlines, sail away from safe harbor, catch the trade winds in your sails.  Explore, Dream, Discover. –Mark Twain",
    "Life is 10% what happens to me and 90% of how I react to it. –Charles Swindoll",
    "Eighty percent of success is showing up. –Woody Allen",
    "The best time to plant a tree was 20 years ago. The second best time is now. –Chinese Proverb",
    "Winning isn’t everything, but wanting to win is. –Vince Lombardi",
    "I’ve learned that people will forget what you said, people will forget what you did, but people will never forget how you made them feel. –Maya Angelou",
    "The two most important days in your life are the day you are born and the day you find out why. –Mark Twain",
    "People often say that motivation doesn’t last. Well, neither does bathing.  That’stm why we recommend it daily. –Zig Ziglar",
    "Everything you’ve ever wanted is on the other side of fear. –George Addair",
    "We can easily forgive a child who is afraid of the dark; the real tragedy of life is when men are afraid of the light. –Plato",
    "When I was 5 years old, my mother always told me that happiness was the key to life.  When I went to school, they asked me what I wanted to be when I grew up.  I wrote down ‘happy’.  They told me I didn’t understand the assignment, and I told them they didn’t understand life. –John Lennon",
    "When one door of happiness closes, another opens, but often we look so long at the closed door that we do not see the one that has been opened for us. –Helen Keller",
    "Life is not measured by the number of breaths we take, but by the moments that take our breath away. –Maya Angelou",
    "Too many of us are not living our dreams because we are living our fears. –Les Brown",
    "I didn’t fail the test. I just found 100 ways to do it wrong. –Benjamin Franklin",
    "A person who never made a mistake never tried anything new. –Albert Einstein",
    "A truly rich man is one whose children run into his arms when his hands are empty. –Unknown",
    "If you want your children to turn out well, spend twice as much time with them, and half as much money. –Abigail Van Buren",
    "It does not matter how slowly you go as long as you do not stop. –Confucius",
    "You can’t use up creativity.  The more you use, the more you have. –Maya Angelou",
    "Do what you can, where you are, with what you have. –Teddy Roosevelt",
    "You may be disappointed if you fail, but you are doomed if you don’t try. –Beverly Sills",
]

eightball = [
    "It is certain", "It is surely so", "Without a doubt", "You may rely on it", "Most likely", "Yes",
    "Ask again later", "Cannot predict now", "Concentrate and ask again", "I would say yes", "JUST DO IT",
    "My reply is no", "My sources say no", "Signs point to yes"]