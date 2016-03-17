# AyyBot (python)
made by DefaltSimon, with [discord.py api](https://github.com/Rapptz/discord.py) .

**1** Features:
- Spam and swearing filter
- "many" commands ("easy to add your own" - config.py, also !cmd add <> <> to add commands on the fly)
- settings (see settings.ini)  
- logging with timestamp (data/logs.txt)  
- whitelist (data/whitelist.txt)
- status display (settings.ini and !playing command)

**1.1** Requirements and installing:
- Python 3.5+ (required for async def)
- [discord.py api](https://github.com/Rapptz/discord.py) (install with ```pip install git+https://github.com/Rapptz/discord.py@async```)
- giphypop - ```pip install giphypop```
- wordfilter - ```pip install wordfilter```

  *Starting the bot:*  
   1. first set up `settings.ini`  
   2. then execute ```python ayybot.py```

**1.2** - Useful Commands:  
```
!help useful - displays available commands
!help fun - funny commands
!help meme - memes
!help all - send all the commands to you via private message
!hello - says hi
!ping - Pong!
!members - displays all members on the server
!uptime - displays bot uptime
!avatar @mention returns a link to mentioned person's avatar or yours if there is no mention
!user @mention - returns info about the user
!games - tells you what games you played and how much
!wiki or !define <word> - defines a word
!urban <term> - like !wiki, but from urbandictionary.com
!credits - author, etc.
*Owner/whitelisted users only:*
!role add/remove/replacewith <role name> @mentions - modifies roles
!kick @mention - kicks users
!ban @mention - bans users
!unban @mention - unbans users
!playing <name> - changes status
!cmd add !<trigger> <response>
!cmd list
!cmd remove !<name>
ayybot.sleep/wake - pauses/resumes the bot
ayybot.config.reload
ayybot.kill - stops the bot  
```
**1.3** - Fun Commands:  
```
!gif <name> - returns a gif from Giphy
!roll <number> - random number
!dice - like !roll but 0 - 6
!decide word word - decides between two words
!quote - random quote
```
**1.4** - "Meme" Commands:
```
!kappa - kappa
!cats - catscatscats
!ayy - ayy lmao
!ayylmao - even more ayy lmao with lenny face
!wot - u wot m8
!allstar just try it ( ͡° ͜ʖ ͡°)
!johncena dis too ( ͡° ͜ʖ ͡°)
!thecakeisalie - want it?
```

Enjoy!
