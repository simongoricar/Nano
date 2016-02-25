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
   execute ```python ayybot.py```

**1.2** - Useful Commands:  
```
!help useful - displays available commands  
!help fun - funny commands 
!help meme
!hello - says hi  
!members - displays all members on the server  
!uptime - displays bot uptime  
!avatar @mention returns a link to mentioned person's avatar or yours if there is no mention  
!user @mention - returns info about the user  
!wiki or !define <word> - defines a word  
!urban <term> - like !wiki, but from urbandictionary.com  
*Owner/whitelisted users only:*  
!role add/remove/replacewith @mention - modifies roles  
!cmd add <trigger> <response>  - adds a command (into data/customcommands.txt)
!cmd list  
!cmd remove !<name>  
!credits - version, author, ...
ayybot.sleep/wake - pauses/resumes the bot  
ayybot.kill - stops the bot   
```
**1.3** - Fun Commands:  
```
!gif <name> - returns a gif from Giphy  
!roll <number> - random number  
!dice - 1 -> 6 random number  
!decide word word - decides between two words  
```
**1.4** - Meme Commands:
```
!ayy - ayy lmao  
!ayylmao - even more ayy lmao with lenny face  
!wot - u wot m8  
!allstar just try it ( ͡° ͜ʖ ͡°)  
!johncena dis too ( ͡° ͜ʖ ͡°)  
!thecakeisalie - want it?  
!cats - cuz they are cute  
!kappa - kappa
```
**1.4** - TO-DO:
```
!youtube
!join server
- plugins  (?)
```
Enjoy!
