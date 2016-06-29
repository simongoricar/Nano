import discord
import configparser
import asyncio
import time
import wikipedia
import requests
import giphypop
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from random import randint
from yaml import load
from youtube_dl import utils as ut
from discord.voice_client import StreamPlayer

# AyyBot module imports
from utils import helpmsg, messagelist, quotes, eightball, ayybotinfo, githubinfo, appinfo, musichelp, bugreport, commandhelpsadmin, commandhelpsnormal
from plugins import voting, stats, mentions, moderator
from data import serverhandler

__author__ = 'DefaltSimon'
__version__ = '2.0'


# Declarations

client = discord.Client()
parser = configparser.ConfigParser()
giphy = giphypop.Giphy(api_key="dc6zaTOxFJmzC")  # Public beta key, available on their github
handler = serverhandler.ServerHandler()
vote = voting.Vote()
stat = stats.BotStats()
mention = mentions.MentionHandler()
mod = moderator.BotModerator()

parser.read("settings.ini")

# Constants

DEFAULT_PREFIX = parser.get("Settings","defaultprefix")

# Exception classes


class MessageNotFoundError(Exception):
    def __init__(self):
        pass


class PrefixNotSet(Exception):
    def __init__(self):
        pass


# Changes 'playing' status
class StatusHandler:
    def __init__(self):
        pass

    async def set(self,content):
        game = discord.Game(name=str(content))
        loop.create_task(client.change_status(game=game))

# Main class


class AyyBot:
    def __init__(self, ownerid=0):
        self.admins = {}
        self.prefixes = {}

        self.updateprefixes()
        self.updateadmins()

        self.boottime = time.time()
        self.ownerid = int(ownerid)

        self.vc = None
        self.ytplayer = None
        self.ytstatus = ""

    def updateadmins(self):
        with open("data/servers.yml", "r") as file:
            if not file:
                return

            data = load(file)
            for this in data.keys():
                # 'this' is id of the server
                # 'admin' is the admin on the server

                if not data[this]["admins"]:
                    continue

                self.admins[this] = []

                for admin in data[this]["admins"]:
                    self.admins[this].append(admin)

    def updateprefixes(self):
        with open("data/servers.yml", "r") as file:
            if not file:
                return

            data = load(file)
            for this in data:
                try:
                    self.prefixes[str(this)] = data[this]["prefix"]
                except KeyError:
                    pass

    async def on_message(self, message):

        if message.author.id == client.user.id:
            return

        # Import code here

        normalcmds = ["_help", "_hello", "_uptime", "_randomgif", "_8ball", "_wiki", "_define", "_urban", "_avatar",
                      "_ping", "_cmd list", "_roll", "_ayybot", "ayybot.info", "_github", "_decide", "_cat", "_kappa",
                      "_prefix", "ayy lmao", "_vote", "_status", "ayybot.status", "_stats", "ayybot.stats", "_music join",
                      "_music leave", "_music volume", "_music pause", "_music resume", "_music playing", "_music help",
                      "_music play", "_music skip", "_music stop", "ayybot.bug", "_bug", "_vote", "ayybot.prefix"]

        admincmds = ["ayybot.ban", "ayybot.unban", "ayybot.kick", "_ban", "_unban", "_kick", "_avatar", "_role add",
                     "_role replacewith", "_role remove", "_cmd add", "_cmd remove",
                     "ayybot.serversetup", "ayybot.server.setup", "ayybot.admins add", "ayybot.admins remove",
                     "ayybot.admins list", "ayybot.sleep", "ayybot.wake", "_invite", "ayybot.invite", "ayybot.displaysettings",
                     "ayybot.settings", "_vote start", "_vote end", "ayybot.blacklist add", "ayybot.blacklist remove", "_getstarted",
                     "ayybot.getstarted", "ayybot.changeprefix", "_playing", "ayybot.kill", "_user", "_reload", "ayybot.reload"]

        privates = ["_help", "_uptime", "_randomgif", "_8ball", "_wiki", "_define", "_urban"]


        # Just so it cant be undefined
        prefix = None
        isacommand = False
        isadmincommand = False

        try:
            prefix = self.prefixes.get(message.channel.server.id)

            if not prefix:
                self.prefixes[message.channel.server.id] = DEFAULT_PREFIX
                prefix = DEFAULT_PREFIX
                print("Server '{}' has been given the default prefix".format(message.channel.server.name))
                handler.changeprefix(message.channel.server, DEFAULT_PREFIX)

                self.updateprefixes()

        except KeyError:
            handler.serversetup(message.channel.server)
            prefix = DEFAULT_PREFIX
            print("Server '{}' has been given the default prefix".format(message.channel.server.name))
            handler.changeprefix(message.channel.server, DEFAULT_PREFIX)

            self.updateprefixes()

        # Better safe than sorry
        if not prefix:
            raise PrefixNotSet

        # Checks for private channel
        if isinstance(message.channel, discord.PrivateChannel):
            for this in privates:
                this = this.replace("_", DEFAULT_PREFIX)
                if str(message.content).startswith(this):
                    break
            else:
                return

        # When it is not a private channel, check if a command even exists
        else:
            if client.user in message.mentions:

                # MentionHandler processes the message and returns the answer
                response = mention.respond(message)

                if not response:
                    pass
                else:
                    await client.send_message(message.channel,response)
                    stat.plusmsg()

                    return

                pass

            else:

                servercmd = handler.returncommands(message.channel.server)

                # Checks for server specific commands
                for command in servercmd:
                    if str(message.content).startswith(command):
                        # Maybe same replacement logic in the future update?
                        await client.send_message(message.channel, servercmd[command])

                        return

                # Existing command check (two steps)
                for this in normalcmds:
                    this = this.replace("_", self.prefixes.get(message.channel.server.id))
                    if str(message.content).startswith(this):
                        stat.plusmsg()

                        isacommand = True
                        break

                if not isacommand:
                    for this in admincmds:
                        this = this.replace("_", self.prefixes.get(message.channel.server.id))
                        if str(message.content).startswith(this):
                            stat.plusmsg()

                            isadmincommand = True
                            isacommand = False
                            break

                # APPLIES FILTERS and returns
                if not isacommand and not isadmincommand:

                    issf = iswf = False
                    # If it is not a command, apply filters
                    sf = handler.needspamfilter(message.channel.server)
                    wf = handler.needwordfilter(message.channel.server)

                    if sf:
                        issf = mod.checkspam(message.content)

                    if wf:
                        iswf = mod.checkfilter(message.content)

                    if sf or wf:
                        # Apply
                        if issf:

                            # Attempt to catch errors (messages not being there)
                            try:
                                await client.delete_message(message)
                            except discord.errors.NotFound:
                                pass

                        if iswf:

                            try:
                                await client.delete_message(message)
                            except discord.errors.NotFound:
                                pass

                    return
        # Just a quick shortcut

        def startswith(cmd):
            if not message:
                raise MessageNotFoundError

            if str(message.content).lower().startswith(str(cmd).lower()):
                return True
            else:
                return False

        # ayybot.wake command check

        # Wake command
        if startswith("ayybot.wake"):
            # Don't do anything if already awake
            if not handler.issleeping(message.channel.server):
                return

            isadmin = False
            try:
                isadmin = bool(message.author.id in self.admins.get(message.channel.server.id))
            except TypeError:
                isadmin = False

            if isadmin or bool(str(message.author.id) == str(self.ownerid)):
                handler.setsleeping(message.channel.server, 0)
                await client.send_message(message.channel, "I am back.")
                stat.plusslept()


        # Before checking for commands checks for sleep state and server file existence

        if handler.issleeping(message.channel.server):
            return

        if not handler.serverexists(message.channel.server):
            handler.serversetup(message.channel.server)
            print("Automatically set up server data ({})".format(message.channel.server.name))

        # The command declarations begin here

        # FYI: Server specific command have been checked before

        # Checks for commands that have simple responses and are imported from utils.py
        for command in messagelist:
            if startswith(command.replace("_", prefix)):
                # Replaces stuff
                try:
                    response = str(messagelist[command]).replace("<mentioned>", message.mentions[0].name).replace("_", self.prefixes.get(message.channel.server.id))
                except IndexError:
                    response = str(messagelist[command]).replace("_", self.prefixes.get(message.channel.server.id))

                await client.send_message(message.channel, response)
                stat.plusmsg()

        # Help
        if startswith(prefix + "help"):
            # Branches out

            if str(message.content) == "_help".replace("_", prefix):
                await client.send_message(message.channel, str(helpmsg).replace(">", prefix))

                stat.plushelpcommand()
                return

            elif startswith(prefix + "help simple"):
                # Combines all simple commands
                pass

            else:
                search = str(message.content)[len(prefix + "help "):]
                for key in commandhelpsnormal.keys():
                    if search.startswith(str(key).replace("_", prefix)):
                        cmd = str(key).replace("_", prefix)
                        desc = commandhelpsnormal[str(key)]["desc"]
                        use = commandhelpsnormal[str(key)]["use"]
                        alias = commandhelpsnormal[str(key)]["alias"]

                        # Compiles proper message
                        if use and alias:
                            preset = """Command: **{}**
```css
Description: {}

{}
{}```
""".format(cmd, desc, use, alias)

                        elif alias and not use:
                            preset = """Command: **{}**
```css
Description: {}

{}```
""".format(cmd, desc, alias)

                        elif use and not alias:
                            preset = """Command: **{}**
```css
Description: {}

{}```
""".format(cmd, desc, use)

                        elif not use and not alias:
                            preset = """Command: **{}**
```css
Description: {}```
""".format(cmd, desc)
                        else:
                            print("How is this even possible?!")
                            return


                        await client.send_message(message.channel, preset)


                        stat.plushelpcommand()
                        return

                for key in commandhelpsadmin.keys():
                    if search.startswith(str(key).replace("_", prefix)):
                        cmd = str(key).replace("_", prefix)
                        desc = commandhelpsadmin[str(key)]["desc"]
                        use = commandhelpsadmin[str(key)]["use"]
                        alias = commandhelpsadmin[str(key)]["alias"]

                        # Compiles proper message
                        if use and alias:
                            preset = """Command: **{}** (admins only)
```css
Description: {}

{}
{}```
""".format(cmd, desc, use, alias)

                        elif alias and not use:
                            preset = """Command: **{}** (admins only)
```css
Description: {}

{}```
""".format(cmd, desc, alias)

                        elif use and not alias:
                            preset = """Command: **{}** (admins only)
```css
Description: {}

{}```
""".format(cmd, desc, use)

                        elif not use and not alias:
                            preset = """Command: **{}** (admins only)
```css
Description: {}```
""".format(cmd, desc)
                        else:
                            print("How is this even possible?!")
                            return


                        await client.send_message(message.channel, preset)


                        stat.plushelpcommand()
                        return

        # Ping
        elif startswith(prefix + "ping"):
            await client.send_message(message.channel, "**Pong!**")
            stat.plusoneping()

        # Throw a dice
        elif startswith(prefix + "dice"):
            rnum = randint(1, 6)
            if rnum == 6:
                rnum = str(rnum) + ". Woot!"
            else:
                rnum = str(rnum) + "."
            await client.send_message(message.channel, "**{}** rolled {}".format(message.author.name, rnum))

        # Simple roll da number
        elif startswith(prefix + "roll"):
            try:
                num = int(str(message.content)[len(prefix + "roll "):])
            except ValueError:
                await client.send_message(message.channel, "Please use a number.")
                return

            rn = randint(0, num)

            if num == rn:
                result = "*{}*. **WOWOWOWOW!**".format(rn)
            else:
                result = "*" + str(rn) + "*."

            await client.send_message(message.channel, "**{}** just rolled {}".format(message.author.name, result))

        elif startswith(prefix + "decide"):
            beforesplit = str(message.content)[len(prefix + "decide "):]
            items = beforesplit.split("|")

            if beforesplit == items[0]:
                await client.send_message(message.channel, "Guess what? It's " + str(items[0]) + ". **ba dum tss.**")
                return

            rn = randint(0, len(items)-1)
            await client.send_message(message.channel, "**drum roll**... I have decided: {}".format(items[rn]))

        # Says hello to you or the mentioned person
        elif startswith(prefix + "hello"):
            if len(message.mentions) >= 1:
                await client.send_message(message.channel, "Hi <@" + message.mentions[0].id + ">")
            elif len(message.mentions) == 0:
                await client.send_message(message.channel, "Hi <@" + message.author.id + ">")

        # Calculates uptime
        elif startswith(prefix + "uptime"):
            sec = timedelta(seconds=time.time()-self.boottime)
            d = datetime(1, 1, 1) + sec
            uptime = "I have been tirelessly answering people without sleep for **{} days, {} hours, {} minutes and {} seconds!**".format(d.day - 1, d.hour, d.minute, d.second)

            await client.send_message(message.channel, uptime)

        # Replies with a random quote
        elif startswith(prefix + "quote"):
            chosen = str(quotes[randint(0,len(quotes)-1)])
            place = chosen.rfind("–")
            await client.send_message(message.channel, chosen[:place] + "\n**" + chosen[place:] + "**")

        # Answers your question - 8ball style
        elif startswith(prefix + "8ball"):
            answer = eightball[randint(0, len(eightball)-1)]
            await client.send_message(message.channel, "The 8ball tells me: " + str(answer) + ".")

        # Finds a totally random gif
        elif startswith(prefix + "randomgif"):
            gif = giphy.screensaver().media_url
            await client.send_message(message.channel, str(gif))

        # Fetches a definition from Wikipedia
        elif startswith(prefix + "wiki") or startswith(prefix + "define"):
            search = None
            if startswith(prefix + "wiki"):
                search = str(message.content)[len(prefix + "wiki "):]
            elif startswith(prefix + "define"):
                search = str(message.content)[len(prefix + "define "):]

            if not search or search == " ":  # If empty args
                await client.send_message(message.channel, "Please include a word you want to define.")
                return

            try:
                answer = wikipedia.summary(search, sentences=parser.get("Settings", "wikisentences"), auto_suggest=True)
                await client.send_message(message.channel, "**{} :** \n".format(search) + answer)
            except wikipedia.exceptions.PageError:
                await client.send_message(message.channel, "No definitions found.")
            except wikipedia.exceptions.DisambiguationError:
                await client.send_message(message.channel,
                                          "I found multiple definitions of {}, please be more specific (somehow).".format(search))

        # Fetches a definition from Urban Dictionary
        elif startswith(prefix + "urban"):
            search = str(message.content)[len(prefix + "urban "):]
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(search))
            answer = BeautifulSoup(define.content, "html.parser").find("div", attrs={"class": "meaning"}).text

            if str(answer).startswith("\nThere aren't any"):
                await client.send_message(message.channel, "No definition found")
            else:
                await client.send_message(message.channel, "**" + message.content[7:] + "** *:*" + answer)

        # Simple info
        elif startswith(prefix + "ayybot") or startswith("ayybot.info"):
            await client.send_message(message.channel, ayybotinfo.replace("<version>", __version__))

        # Github repo link
        elif startswith(prefix + "github"):
            await client.send_message(message.channel, githubinfo)

        # Replies with current (custom) commands on the server
        elif startswith(prefix + "cmd list"):
                cmds = handler.returncommands(message.server)
                final = ""

                for this in cmds.keys():
                    final += "\n{} : {}".format(this, cmds[this])

                if not final:
                    await client.send_message(message.channel, "No commands registered for this server ")
                    return
                await client.send_message(message.channel, "*Command list:*" + final)

        # People can vote with vote <number>
        elif startswith(prefix + "vote"):
            if not startswith(prefix + "vote start") and not startswith(prefix + "vote end"):
                try:
                    num = int(str(message.content)[len(prefix + "vote "):])
                except ValueError:
                    await client.send_message(message.channel, "Please select your choice and reply with it's number :upside_down:")
                    return

                try:
                    vote.countone(num, message.author.id, message.channel.server)
                    stat.plusonevote()
                except voting.AlreadVoted:
                    await client.send_message(message.channel, "Cheater :smile:")

        # Simple status (server, user count)
        elif startswith(prefix + "status") or startswith("ayybot.status"):
            servercount = 0
            for server in client.servers:
                servercount += 1

            members = 0
            for member in client.get_all_members():
                members += 1

            channels = 0
            for channel in client.get_all_channels():
                channels += 1

            stats = "**Quick Stats**```Servers: {}\nUsers: {}\nChannels: {}```".format(servercount, members, channels)

            await client.send_message(message.channel,stats)

        # Some interesting stats
        elif startswith(prefix + "stats") or startswith("ayybot.stats"):
            with open("plugins/stats.yml", "r+") as file:
                file = load(file)

                downsize = str(round(int(stat.sizeofdown()) / 1024 / 1024 / 1024, 3))

                mcount = file["msgcount"]
                wrongargc = file["wrongargcount"]
                timesleft = file["serversleft"]
                timesslept = file["timesslept"]
                wrongpermc = file["wrongpermscount"]
                pplhelp = file["peoplehelped"]
                imgc = file["imagessent"]
                votesc = file["votesgot"]
                pings = file["timespinged"]

            onetosend = "**Stats**\n```python\n{} messages sent\n{} people yelled at because of wrong args\n{} people denied because of wrong permissions\n{} people helped\n{} votes got\n{} times slept\n{} servers left\n{} images sent\n{} mb of pictures downloaded\n{} times Pong!-ed```".format(
                mcount, wrongargc, wrongpermc, pplhelp, votesc, timesslept, timesleft, imgc, downsize, pings)
            await client.send_message(message.channel, onetosend)


        # MUSIC
        # Music commands!
        elif startswith(prefix + "music join"):
            cut = str(message.content)[len(prefix + "music join "):]
            ch = discord.utils.find(lambda m: m.name == str(cut), message.channel.server.channels)

            # Opus load
            discord.opus.load_opus("libopus-0.x64.dll")

            if not discord.opus.is_loaded():
                await client.send_message(message.channel, "Opus lib could not be loaded, please contact owner.")

            try:
                self.vc = await client.join_voice_channel(ch)
                await client.send_message(message.channel, "Joined **{}**!".format(cut))
            except discord.errors.InvalidArgument:
                self.vc = None
                await client.send_message(message.channel, "Could not join, **{}** is not a voice channel.".format(cut))
                return

        elif startswith(prefix + "music leave"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):
                try:
                    self.ytplayer.stop()
                except AttributeError:
                    pass

                self.ytplayer = None
                await client.send_message(message.channel, "Left **" + self.vc.channel.name + "**")

                await self.vc.disconnect()
                self.vc = None

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        elif startswith(prefix + "music playing"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):

                if self.ytplayer:  # If used 'music play'
                    title = self.ytplayer.title
                    uploader = self.ytplayer.uploader
                    dur = str(int(self.ytplayer.duration/60)) + ":" + str(self.ytplayer.duration % 60)
                    views = self.ytplayer.views

                    formatted = "{}: **{}**```\nDuration: {}\nUploader: {}\nViews: {}```".format(self.ytstatus, title, str(dur), uploader, views)
                    await client.send_message(message.channel, formatted)

                else:
                    await client.send_message(message.channel, "Not playing anything at the moment")
            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_",prefix))

        elif startswith(prefix + "music play"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):

                # If the song is still playing, ask the user to use !music skip
                if self.ytplayer:
                    if self.ytplayer.is_playing or not self.ytplayer.is_done:
                        await client.send_message(message.channel, "*{}* is already playing, please **wait** or **skip** the song with `{}music skip`.".format(self.ytplayer.title, prefix))
                        return

                args = str(message.content)[len(prefix + "music play "):]
                await client.send_typing(message.channel)

                try:
                    self.ytplayer = await self.vc.create_ytdl_player(args)
                except ut.DownloadError:
                    await client.send_message(message.channel, "Not a valid URL or incompatible video :x:")

                while self.ytplayer is None:
                    time.sleep(0.1)

                try:
                    await self.ytplayer.start()
                except TypeError:
                    pass

                self.ytplayer.volume = 0.4

                duration = str(int(self.ytplayer.duration/60)) + ":" +  str(self.ytplayer.duration % 60 )
                await client.send_message(message.channel, "Playing **{}**\n**Duration:** `{}`\n**Uploader:** `{}`\n**Views:** `{}`"
                                                           .format(self.ytplayer.title, duration, self.ytplayer.uploader, self.ytplayer.views))
                self.ytstatus = "Playing"

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Skips (ytplayer.stop()) / stops the current song
        elif startswith(prefix + "music skip") or startswith(prefix + "music stop"):
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.ytplayer, StreamPlayer):
                if self.ytplayer.is_playing():
                    self.ytplayer.stop()

                    self.ytplayer = None

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))


        # Set or figure out the current volume (accepts 0 - 150)
        elif startswith(prefix + "music volume"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.ytplayer, StreamPlayer):
                args = str(message.content)[len(prefix + "music volume "):]

                if args == "":
                    if self.ytplayer is not None:
                        await client.send_message(message.channel, "Current volume is **" + str(self.ytplayer.volume) + "**")
                    else:
                        await client.send_message(message.channel, "Not playing anything (default volume will be *40*)")

                else:

                    try:
                        if not (150 >= int(args) >= 0):
                            await client.send_message(message.channel,"Please use **0 - 150** (100 equals 100% - normal volume)")
                    except ValueError:
                        await client.send_message(message.channel, "Not a number :x:")

                    argss = round(int(args)/100,2)
                    self.ytplayer.volume = argss

                    await client.send_message(message.channel, "Volume set to " + str(args))

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Pauses the curent song (if any)
        elif startswith(prefix + "music pause"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.ytplayer, StreamPlayer):

                if self.ytplayer.is_playing():
                    self.ytplayer.pause()
                    self.ytstatus = "Paused"
                else:
                    pass

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Resumes the current song (if any)
        elif startswith(prefix + "music resume"):
            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.ytplayer, StreamPlayer):

                if not self.ytplayer.is_playing():
                    self.ytplayer.resume()
                    self.ytstatus = "Playing"
                else:
                    pass

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Music help message
        elif startswith(prefix + "music help"):
            await client.send_message(message.channel, musichelp.replace("_", prefix))


        # PICTURE COMMANDS

        elif startswith(prefix + "kappa"):
            await client.send_file(message.channel, "data/images/kappasmall.png")


        # BUG REPORT
        elif startswith(prefix + "bug") or startswith("ayybot.bug"):
            await client.send_message(message.channel, bugreport)

        #
        # Here start ADMIN ONLY commands
        #

        # If it does not fall under 'normal' commands, check for admin command before denying permission

        # If a command was already executed, return
        if isacommand:
            return

        isk = False

        # If it is not an admin command, return before sending 'no permission' message
        if not isadmincommand:
            return

        isadmin = False
        try:
            isadmin = bool(message.author.id in self.admins.get(message.channel.server.id))
        except TypeError:
            isadmin = False

        isowner = bool(str(message.author.id) == str(self.ownerid))

        if not isowner:
            if not isadmin:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                stat.pluswrongperms()
                return


        # Simple ban with CONFIRM check
        if startswith(prefix + "ban") or startswith("ayybot.ban"):
            user = message.mentions[0]

            await client.send_message(message.channel, "Are you sure you want to ban " + user.name + "? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel, timeout=15, content="CONFIRM")
            if followup is None:
                await client.send_message(message.channel, "You ran out of time :upside_down:")

            else:
                await client.ban(user)
                await client.send_message(message.channel, "**{}** has been banned. rip".format(user.name))

        # Simple unban with CONFIRM check
        elif startswith(prefix + "unban") or startswith("ayybot.unban"):
            user = message.mentions[0]

            await client.send_message(message.channel,"Are you sure you want to unban " + user.name + "? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel, timeout=15, content="CONFIRM")
            if followup is None:
                await client.send_message(message.channel, "You ran out of time :upside_down:")

            else:
                await client.unban(user)
                await client.send_message(message.channel, "**{}** has been unbanned. woot!".format(user.name))

        # Simple kick WITHOUT double check
        elif startswith(prefix + "kick") or startswith("ayybot.kick"):
            user = message.mentions[0]

            await client.kick(user)
            await client.send_message(message.channel, "**{}** has been kicked. rest in peperoni".format(user.name))

        # Sleep command
        elif startswith("ayybot.sleep"):
            handler.setsleeping(message.channel.server, 1)
            await client.send_message(message.channel, "Going to sleep... :zipper_mouth:")

        # Wake command is defined at the beginning

        # Avatar
        elif startswith(prefix + "avatar"):
            # Selects the proper user
            if len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "user "):])
                member = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)
            else:
                member = message.mentions[0]

            url = member.avatar_url

            if not url:
                await client.send_message(message.channel, "**{}** does not have an avatar. shame :P".format())
            else:
                await client.send_message(message.channel, "**{}**'s avatar: {}".format(member.name, url))

        # Role management
        elif startswith(prefix + "role"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention someone.")
                return
            elif len(message.mentions) >= 2:
                await client.send_message(message.channel, "Please mention only one person at a time.")
                return
            user = message.mentions[0]

            if startswith(prefix + "role " + "add "):
                gotrole = str(message.content[len(prefix + "role " + "add "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)

                await client.add_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "remove "):
                gotrole = str(message.content[len(prefix + "role " + "remove "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)

                await client.remove_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "replacewith "):
                gotrole = str(message.content[len(prefix + "role replacewith "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == gotrole, message.channel.server.roles)

                await client.replace_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

        # Server setup should be automatic, but if you want to reset settings, here ya go
        elif startswith("ayybot.serversetup") or startswith("ayybot.server.setup"):
            handler.serversetup(message.channel.server)
            await client.send_message(message.channel, "Server settings reset :upside_down:")

            self.updateadmins()
            self.updateprefixes()

        # Command management
        elif startswith(prefix + "cmd"):

            if startswith(prefix + "cmd add"):
                try:
                    cut = str(message.content)[len(prefix + "cmd add "):].split("|")
                    handler.updatecommand(message.server, cut[0], cut[1])
                    await client.send_message(message.channel, "Command has been added.")

                except KeyError:
                    await client.send_message(message.channel,
                                              ":no_entry_sign: Wrong args, separate command and response with |")
                    stat.pluswrongarg()

                except IndexError:
                    await client.send_message(message.channel,
                                              ":no_entry_sign: Wrong args, separate command and response with |")
                    stat.pluswrongarg()

            elif startswith(prefix + "cmd remove"):
                cut = str(message.content)[len(prefix + "cmd remove "):]
                handler.removecommand(message.server, cut)
                await client.send_message(message.channel, "Ok :white_check_mark: ")

            # Cmd list does not require admin permission so it was moved up

        elif startswith("ayybot.admins"):

            if startswith("ayybot.admins add"):
                if len(message.mentions) > 20:
                    await client.send_message(message.channel, "Too muchhh!\nSeriously, up to 20 at a time")
                    stat.pluswrongarg()
                    return
                elif len(message.mentions) == 0:
                    await client.send_message(message.channel, "Please mention someone to make them admins")
                    stat.pluswrongarg()
                    return

                count = 0
                usern = None
                for ment in message.mentions:
                    handler.addadmin(message.server, ment)
                    count += 1

                if count == 1:
                    await client.send_message(message.channel, "Added **{}** to admins :white_check_mark: ".format(message.mentions[0].name))
                else:
                    await client.send_message(message.channel, "Added **{}** people to admins :white_check_mark: ".format(count))

                self.updateadmins()

            elif startswith("ayybot.admins remove"):
                if len(message.mentions) > 20:
                    await client.send_message(message.channel, "Too muchhh!\nSeriously, up to 20 at a time")
                    stat.pluswrongarg()
                    return
                elif len(message.mentions) == 0:
                    await client.send_message(message.channel, "Please mention someone to remove them from admin position")
                    stat.pluswrongarg()
                    return

                count = 0
                usern = None
                for ment in message.mentions:
                    handler.removeadmin(message.server, ment)
                    count += 1

                if count == 1:
                    await client.send_message(message.channel, "Removed **{}** from admins :white_check_mark: ".format(message.mentions[0].name))
                else:
                    await client.send_message(message.channel, "Removed **{}** people from admins :white_check_mark: ".format(count))

                self.updateadmins()

            elif startswith("ayybot.admins list"):
                self.updateadmins()
                admins = handler.returnadmins(message.server)

                final = ""

                if len(admins) == 0:
                    await client.send_message(message.channel,"Nobody is my admin.\nI am my own admin.\n**DEAL WITH IT**")

                else:
                    for this1 in admins:
                        user = discord.utils.find(lambda user: user.id == this1, message.channel.server.members)
                        final += "{}, ".format(user.name)
                    # Cut by 2 char to remove last , and space
                    final = final[:-2]

                    if len(admins) == 1:
                        await client.send_message(message.channel, "**" + final + "** is the only admin here.")
                    else:
                        await client.send_message(message.channel, "**Admins:** " + final)

        # A link to invite AyyBot to your server
        elif startswith(prefix + "invite") or startswith("ayybot.invite"):
            clientappid = await client.application_info()

            # Most permissions that AyyBot uses
            perms = str("0x22325206")
            url = 'https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions={}'.format(clientappid.id,perms)

            await client.send_message(message.channel, appinfo.replace("<link>", url))

        # Displays current settings, including the prefix
        elif startswith("ayybot.displaysettings"):
                    settings = handler.returnsettings(message.server)
                    bchan = ",".join(settings["blacklisted"])
                    cmds = ",".join(settings["customcmds"])

                    if not cmds:
                        cmds = "None"

                    if bool(settings["filterspam"]):
                        spam = "On"
                    else:
                        spam = "Off"

                    if bool(settings["filterwords"]):
                        wfilter = "On"
                    else:
                        wfilter = "Off"

                    await client.send_message(message.channel, """**Settings for current server:**
```css
Blacklisted channels: {}
Commands: {}
Spam filter: {}
Word filter: {}
Log channel: {}
Number of admins: {}
Prefix: {}```""".format(bchan, cmds, spam, wfilter, settings["logchannel"], len(settings["admins"]), settings["prefix"]))

        elif startswith("ayybot.settings"):
            cut = str(message.content)[len("ayybot.settings "):].split(" ")
            value = handler.updatesettings(message.channel.server, cut[0], cut[1])

            if str(cut[0]) == "filterwords" or str(cut[0]) == "wordfilter" or str(cut[0]).lower() == "word filter":
                if value:
                    await client.send_message(message.channel, "Word filter :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Word filter :negative_squared_cross_mark:")

            elif str(cut[0]) == "filterspam" or str(cut[0]) == "spamfilter" or str(cut[0]).lower() == "spam filter":
                if value:
                    await client.send_message(message.channel, "Spam filter :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Spam filter :negative_squared_cross_mark:")

            elif str(cut[0]) == "welcome" or str(cut[0]) == "sayhi" or str(cut[0]).lower() == "welcome message":
                if value:
                    await client.send_message(message.channel, "Welcome message :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Welcome message :negative_squared_cross_mark:")

            elif str(cut[0]) == "announceban" or str(cut[0]) == "onban" or str(cut[0]).lower() == "announce ban":
                if value:
                    await client.send_message(message.channel, "Ban announcement :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Ban announcement :negative_squared_cross_mark:")

        # Blacklists individual channels
        elif startswith("ayybot.blacklist"):
            if startswith("ayybot.blacklist add"):
                cut = str(str(message.content)[len("ayybot.blacklist add "):])
                handler.updatechannels(message.channel.server, cut)

                await client.send_message(message.channel, "**{}** has been blacklisted!".format(cut))

            elif startswith("ayybot.blacklist remove "):
                cut = str(str(message.content)[len("ayybot.blacklist remove "):])
                handler.removechannels(message.channel.server, cut)

                await client.send_message(message.channel, "No worries, **{}** has been removed from the blacklist!".format(cut))


        # Vote creation
        elif startswith(prefix + "vote start"):
            if vote.inprogress(message.channel.server):
                await client.send_message(message.channel, "A vote is already in progress.")
                return

            content = str(str(message.content)[len(prefix + "vote start "):])

            vote.create(message.author.name,message.channel.server,content)
            ch = ""

            n = 1
            for this in vote.getcontent(message.channel.server):
                ch += "{}. {}\n".format(n,this)
                n += 1
            ch.strip("\n")

            await client.send_message(message.channel, "**{}**\n\n{}".format(vote.returnvoteheader(message.channel.server),ch))

        # Vote end
        elif startswith(prefix + "vote end"):

            if not vote.inprogress(message.channel.server):
                await client.send_message(message.channel, "There are no votes currently open.")

            votes = vote.returnvotes(message.channel.server)
            header = vote.returnvoteheader(message.channel.server)
            content = vote.returncontent(message.channel.server)

            # Reset!
            vote.__init__()

            cn = ""
            for this in content:
                cn += "{} - `{} vote(s)`\n".format(this,votes[this])

            combined = "**{}**\n\n{}".format(header,cn)

            await client.send_message(message.channel, combined)

        # GET STARTED
        elif startswith(prefix + "getstarted") or startswith("ayybot.getstarted"):

            auth = message.author

            stmsg = """**Hey!** I see you want to set up your server? Sure man.
The setup consists of a few steps, where you will be prompted to answer.
Since you started, I will only listen to your replies.
**Let's get started, shall we?**"""""
            await client.send_message(message.channel, stmsg)
            time.sleep(2)

            # FIRST MESSAGE
            frmsg = """*1/4* It is recommended that you reset all **bot-related** server settings before continuing.
Do you want to do that? (this includes spam and swearing protection, admin list, blacklisted channels, logchannel, prefix and welcome message)
Reply with `YES` or `NO` after you decide."""
            await client.send_message(message.channel,frmsg)

            async def timeout(message):
                await client.send_message(message.channel, "You ran out of time :upside_down: (FYI: the timeout is 20 seconds)")
                return

            # First check
            choice1 = None

            def whatisit(msg):
                global choice1
                # yes or no
                if str(msg).lower().strip(" ") == "yes":
                    choice1 = True
                    return True
                else:
                    choice1 = False
                    return True

            ch1 = await client.wait_for_message(timeout=20, author=auth, check=whatisit)
            if ch1 is None:
                timeout(message)

            if choice1:
                handler.serversetup(message.channel.server)
            else:
                pass

            # SECOND MESSAGE
            secmsg = """*2/4* What prefix would you like to use for all commands?
**Reply** only with that prefix.
"""
            await client.send_message(message.channel,secmsg)

            # Second check
            ch2 = await client.wait_for_message(timeout=20, author=auth)
            if ch2 is None:
                timeout(message)

            if str(ch2.content):
                handler.changeprefix(message.channel.server,str(ch2.content))

            # THIRD MESSAGE
            thrmsg = """*3/4* Would you like me to say hello to every person that joins the server?
Reply with `YES` or `NO` after you decide.
"""
            await client.send_message(message.channel,thrmsg)

            # Third check
            choice3 = None

            def whatisit2(msg):
                global choice3
                # yes or no
                if str(msg).lower().strip(" ") == "yes":
                    choice3 = True
                    return True
                else:
                    choice3 = False
                    return True

            ch3 = await client.wait_for_message(timeout=20,author=auth,check=whatisit2)
            if ch3 is None:
                timeout(message)

            if choice3:
                handler.updatesettings(message.channel.server, "sayhi", True)
            else:
                handler.updatesettings(message.channel.server, "sayhi", False)

            # FOURTH MESSAGE
            fourmsg = """*4/4* Would you like me to filter spam?
Reply with `YES` or `NO` after you decide.
"""
            await client.send_message(message.channel, fourmsg)

            # Foutrth check
            choice4 = None

            def whatisit3(msg):
                global choice4
                # yes or no
                if str(msg).lower().strip(" ") == "yes":
                    choice4 = True
                    return True
                else:
                    choice4 = False
                    return True

            ch3 = await client.wait_for_message(timeout=20,author=auth,check=whatisit3)
            if ch3 is None:
                timeout(message)

            if choice3:
                handler.updatesettings(message.channel.server, "filterspam", True)
            else:
                handler.updatesettings(message.channel.server, "filterspam", False)


            finalmsg = """**This concludes the basic server setup.**

There are more settings, filtering swearing for example (use `ayybot.config filterwords True`).

You can also manage admins with `ayybot.admins add/remove/list @mention`.

The prefix can be changed again with `ayybot.changeprefix prefix` and channels can be blacklisted with `ayybot.blacklist add/remove channel`.

Don't forget, you can also add/remove/list custom commands with `_cmd add/remove/list command|response`.
""".replace("_", str(ch2.content))

            await client.send_message(message.channel, finalmsg)

            self.updateadmins()
            self.updateprefixes()


        elif startswith("ayybot.changeprefix"):
            cut = str(message.content)[len("ayybot.changeprefix "):]
            handler.changeprefix(message.channel.server, str(cut))

            await client.send_message(message.channel, "Prefix has been changed :heavy_check_mark:")

            self.updateprefixes()

        # Shuts the bot down
        elif startswith("ayybot.kill"):
            # Restricted to owner
            if not message.author.id == self.ownerid:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            if message.author.id == self.ownerid:
                await client.send_message(message.channel, "**DED**")
                exit(0)

        # Changes 'playing' status
        elif startswith(prefix + "playing"):
            # Restricted to owner
            if not message.author.id == self.ownerid:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            cut = str(message.content)[len(prefix + "playing "):]
            await status.set(cut)

            await client.send_message(message.channel, "Status set :white_check_mark:")

        # Reloads settings.ini, prefixes and admins
        elif startswith(prefix + "reload") + startswith("ayybot.reload"):
            # Restricted to owner
            if not message.author.id == self.ownerid:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            self.updateadmins()
            self.updateprefixes()
            parser.read("settings.ini")

            await client.send_message(message.channel, "**Settings refreshed!** :muscle:")

        # Displays user info
        elif startswith(prefix + "user"):

            # Selects the proper user
            if len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "user "):])
                member = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)
            else:
                member = message.mentions[0]

            # If the member does not exist
            if not member:
                await client.send_message(message.channel, ":warning: User does not exist.")
                return

            # Gets info
            name = member.name
            mid = member.id
            avatar = member.avatar_url

            isbot = member.bot
            if isbot:
                bott = "`(BOT)`"
            else:
                bott = ""

            role = member.top_role
            createdate = member.created_at
            joindate = member.joined_at

            # 'Compiles' info
            mixed = """User: **{}** {}
```python
ID: {}
Avatar url: {}

Top role: {}

Joined at: {}
Created at: {}```
""".format(name,bott,mid,avatar,role,joindate,createdate)

            await client.send_message(message.channel, mixed)





# When a member joins the server
@client.event
async def on_member_join(member):
    server = member.server

    if handler.sayhi(server):
        await client.send_message(member.server.default_channel, "<@" + member.id + ">, to **{}!**")


# When somebody gets banned
@client.event
async def on_member_ban(member):
    if handler.onban(member.server):
        await client.send_message(member.server.default_channel, "**{}** has been banned")

    if handler.haslogging(member.server):
        logchannel = discord.utils.find(lambda channel: channel.name == handler.returnlogch(member.server),member.server.channels)
        if logchannel:
            await client.send_message(logchannel, "**{}** has been banned.".format(member.name))

# Events and stuff

ayybot = AyyBot(ownerid=parser.getint("Settings","ownerid"))
status = StatusHandler()

@client.event
async def on_ready():
    print("done")
    print("Username: " + str(client.user.name))
    print("ID: " + str(client.user.id))

    # Sets the status on startup
    name = parser.get("Settings", "initialstatus")
    if bool(name):
        await status.set(name)


@client.event
async def on_message(message):
    # Passes message on to the AyyBot class
    await ayybot.on_message(message)

@asyncio.coroutine
def start():
    # Will accept both forms of auth (token vs mail/pass)
    if parser.has_option("Credentials", "token"):
        token = parser.get("Credentials", "token")

        yield from client.login(token)
        yield from client.connect()

    elif parser.has_option("Credentials", "mail") and parser.has_option("Credentials", "password"):
        mail = parser.get("Credentials", "mail")
        password = parser.get("Credentials", "password")

        yield from client.login(mail, password)
        yield from client.connect()

    else:
        print("[ERROR] Some credentials are missing.")
        exit(-1)

# Loop initialization

loop = asyncio.get_event_loop()

try:
    print("Connecting...", end="")

    loop.run_until_complete(start())
except:
    loop.run_until_complete(client.logout())
finally:
    loop.close()
