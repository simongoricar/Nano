# coding=utf-8

import discord
import configparser
import asyncio
import time
import wikipedia
import requests
import giphypop
import logging
import threading
import os
import sys
import signal
import subprocess

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from random import randint
from yaml import load
from youtube_dl import utils as ut
from pickle import dump
from pickle import load as pickle_load
from discord.voice_client import StreamPlayer

# Nano modules
from utils import *
from plugins import voting, stats, mentions, moderator, minecraft, steam, bptf, playing, backup, imdb, timing
from bots_discord_pw import POSTServerCount
from data import serverhandler

__title__ = "Nano"
__author__ = 'DefaltSimon'
__version__ = '2.2.3dev'

# Logging setup
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARNING)

lg = logging.getLogger("discord")
lg.setLevel(logging.INFO)
h = logging.FileHandler(filename="data/debug.log", encoding="utf-8", mode="w")
h.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
lg.addHandler(h)

# Instances and loop initialization

loop = asyncio.get_event_loop()

client = discord.Client(loop=loop)

parser = configparser.ConfigParser()
parser.read("settings.ini")

giphy = giphypop.Giphy()  # Public beta key (default), available on Giphy's GitHub page

# Plugin instances

if os.path.isfile("cache/voting_state.cache"):
    with open("cache/voting_state.cache", "rb") as vt:
        vote = pickle_load(vt)
    os.remove("cache/voting_state.cache")
else:
    vote = voting.Vote()

rem = timing.Reminder(None, loop)
timebans = timing.TimedBan(None, loop)

handler = serverhandler.ServerHandler()
stat = stats.BotStats()
mention = mentions.MentionHandler()
mod = moderator.BotModerator()
mc = minecraft.Minecraft()
b = backup.BackupManager()
stm = steam.Steam(parser.get("ApiKeys", "steam"))
tf = bptf.CommunityPrices(parser.get("ApiKeys", "bptf"), max_age=7200, allow_cache=True)
idb = imdb.Imdb()

decide = serverhandler.get_decision

# Constants

DEFAULT_PREFIX = parser.get("Settings","defaultprefix")
first = True

# KeyboardInterrupt things


def keyboard_handler(*args):
    logger.critical("Exception: KeyboardInterrupt - Saving voting state to cache/voting_state.cache")
    # Quick state save
    if not os.path.isdir("cache"): os.mkdir("cache")

    with open("cache/voting_state.cache", "wb") as cache:
        dump(vote, cache)  # Save instance of Vote

    with open("cache/reminder_state.cache", "wb") as cache:
        dump(rem, cache)  # Save instance of Reminder

    sys.exit()

signal.signal(signal.SIGINT, keyboard_handler)

# 'Special' uncaught exception logger (for easy debugging)


def exc_logger(exctype, value, tb):
    with open("data/errors.log", "a") as log:
        data = """Exception: {}
Value: {}
Traceback: {}
""".format(exctype, value, tb)
        log.write(data)

sys.excepthook = exc_logger

# Decorator


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


@threaded
def save_submission(content):
    with open("data/submissions.txt", "a") as sf:
        sf.write(str(content))


@threaded
def log(content):
    with open("data/log.txt", "a") as file:
        date = datetime.now()
        cn = date.strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)
        logger.info(content)
        file.write(cn + "\n")

# Exception classes


class MessageNotFoundError(Exception):
    """
    Raised when the sender deleted the message so quickly that the bot can't even process it.
    """
    def __init__(self, *args, **kwargs):
        pass


class PrefixNotSet(Exception):
    """
    When a prefix for the server has not been set. Happens very rarely.
    """
    def __init__(self, *args, **kwargs):
        pass

# Main class


class Nano:
    def __init__(self, owner, debug=False):
        self.admins = {}
        self.prefixes = {}
        self.mutes = {}

        # Debug run
        self.debug = bool(debug)

        if self.debug:
            self.debug_server = str(parser.get("Debug", "debugserver"))

        self.update_prefixes()
        self.update_admins()
        self.update_mutes()

        self.boot_time = time.time()
        self.owner_id = int(owner)

        # TODO multi-server implementation and support for (redhat) linux
        self.vc = None
        self.yt_player = None
        self.yt_status = ""

        # Locks
        self.checking = False

        self.softbans = {}

    def update_admins(self):
        data = handler.get_all_data()
        for this in data.keys():
            # 'this' is id of the server
            # 'admin' is the admin on the server

            if not data[this]["admins"]:
                continue

            self.admins[this] = [admin for admin in data[this]["admins"]]

    def update_prefixes(self):
        data = handler.get_all_data()
        for this in data:

            try:
                self.prefixes[str(this)] = data[this]["prefix"]
            except KeyError:
                pass
            except TypeError:
                pass

    def update_mutes(self):
        data = handler.get_all_data()
        for this in data:
            try:
                self.mutes[this] = data[this]["muted"]  # list
            except KeyError:
                pass

    @staticmethod
    async def send_message(channel, content):
        await client.send_message(channel, content)

    @staticmethod
    async def unban(server, user):
        await client.unban(server, user)

    @staticmethod
    async def ban(server, member):
        await client.ban(member)

    @staticmethod
    def is_server_owner(uid, server):
        return str(uid) == str(server.owner.id)

    @staticmethod
    async def create_log_channel(server, name):
        # Creates a log channel that only 'Nano Admins' and the Nano itself can see
        logger.info("Creating a log channel for {} - {}".format(server.name, name))
        them = discord.PermissionOverwrite(read_messages=False, send_messages=False, read_message_history=False)
        us = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True,
                                         attach_files=True, embed_links=True, manage_messages=True)

        admins = discord.utils.find(lambda m: m.name == "Nano Admin", server.roles)

        th = discord.ChannelPermissions(target=server.default_role, overwrite=them)
        m = discord.ChannelPermissions(target=server.me, overwrite=us)
        ad = discord.ChannelPermissions(target=admins, overwrite=us)

        ln = handler.get_var(server.id, "logchannel")

        if ln:
            if not admins:
                return await client.create_channel(server, ln, th, m)
            else:
                return await client.create_channel(server, ln, th, m, ad)

    def is_muted(self, message):
        try:
            return bool(message.author.id in self.mutes[message.channel.server.id])
        except KeyError:
            return False

    def is_bot_owner(self, uid):
        return str(uid) == str(self.owner_id)

    def server_check(self, server, make_thread=True):
        if make_thread:
            threading.Thread(target=self.server_check, args=[server, False]).start()
            return

        self.checking = True

        if not handler.serverexists(server):
            return

        cname = handler.get_name(server.id)
        cown = handler.get_owner(server.id)

        if server.name != cname:
            handler.update_name(server.id, server.name)

        try:
            if server.owner.id != cown:
                handler.update_owner(server.id, server.owner.id)
        except AttributeError:
            pass

        handler.queue_modification(handler._check_server_vars, server.id)

        self.checking = False

    def remove_old_servers(self, threaded=True):
        if threaded:
            threading.Thread(target=self.server_check, args=[False]).start()
            return

        servers = [srv.id for srv in client.servers]
        handler._delete_old_servers(servers)

    def debug_blocked(self, sid):
        if self.debug:
            try:
                if str(sid) != str(self.debug_server):
                    return True
            except AttributeError:
                return False

            return False

    async def on_message(self, message):
        if message.channel.is_private:  # Ignore DMs
            return

        elif self.debug_blocked(message.channel.server.id):
            return

        elif handler.isblacklisted(message.channel.server.id, message.channel) or (message.author.id == client.user.id):
            return

        try:
            is_admin = bool(message.author.id in self.admins.get(message.channel.server.id))
        except TypeError:
            is_admin = False

        if not is_admin:
            for role in message.author.roles:
                if role.name == "Nano Admin":
                    is_admin = True
                    continue

        is_owner = self.is_bot_owner(message.author.id)

        is_server_owner = self.is_server_owner(message.author.id, message.channel.server)

        # For debugging purposes
        logger.debug("Owner: " + str(is_owner) + "\nServer owner: " + str(is_server_owner) + "\nAdmin: " + str(is_admin))

        # Delete message if the member is muted.
        if self.is_muted(message) and not self.is_bot_owner(message.author.id):
            try:
                await client.delete_message(message)
            except discord.NotFound:
                pass

            stat.plusonesupress()
            return

        # All commands
        # ALL THE SPEED

        normalcmds = ["_help", "_hello", "_uptime", "_randomgif", "_8ball", "_wiki", "_define", "_urban",
                      "_ping", "_cmd list", "_roll", "_nano", "nano.info", "_github", "_decide", "_cat", "_kappa",
                      "_prefix", "ayy lmao", "_vote", "_status", "nano.status", "_stats", "nano.stats", "_music join",
                      "_music leave", "_music volume", "_music pause", "_music resume", "_music playing", "_music help",
                      "_music play", "_music skip", "_music stop", "nano.bug", "_bug", "_vote", "nano.prefix", "_changes",
                      "_changelog", "_johncena", "_rip", "_steam", "_mc ", "_minecraft", "_tf", "_feature", "_quote", "_say",
                      "_members", "_notifydev", "_suggest", "_cmds", "_csgo", "_imdb", "_remind"]

        admincmds = ["nano.ban", "nano.unban", "nano.kick", "_ban", "_unban", "_kick", "_avatar", "_role add",
                     "_role replacewith", "_role remove", "_cmd add", "_cmd remove", "nano.restart",
                     "nano.serversetup", "nano.server.setup", "nano.admins add", "nano.admins remove",
                     "nano.admins list", "nano.sleep", "nano.wake", "_invite", "nano.invite", "nano.displaysettings",
                     "nano.settings", "_vote start", "_vote end", "nano.blacklist add", "nano.blacklist remove", "_getstarted",
                     "nano.getstarted", "nano.changeprefix", "_playing", "nano.kill", "_user", "_reload", "nano.reload", "_muted",
                     "_mute", "_unmute", "_purge", "_dev", "_welcomemsg", "_banmsg", "_kickmsg", "_nuke", "_softban", "nano.softban"]

        # To be implemented
        # privates = ["_help", "_uptime", "_randomgif", "_8ball", "_wiki", "_define", "_urban", "_github", "_bug", "_uptime", "_nano"]

        # Just so it cant be undefined
        is_a_command = False
        is_admin_command = False

        try:
            prefix = self.prefixes.get(message.channel.server.id)

            if not prefix:
                self.prefixes[message.channel.server.id] = DEFAULT_PREFIX
                prefix = DEFAULT_PREFIX
                log.info("Server '{}' has been given the default prefix".format(message.channel.server.name))
                handler.change_prefix(message.channel.server, DEFAULT_PREFIX)

                self.update_prefixes()

        except KeyError:
            handler.server_setup(message.channel.server)
            log("Server settings set up: {}".format(message.channel.server))
            prefix = DEFAULT_PREFIX
            log.info("Server '{}' has been given the default prefix".format(message.channel.server.name))
            handler.change_prefix(message.channel.server, DEFAULT_PREFIX)

            self.update_prefixes()

        # Better safe than sorry
        if not prefix:
            raise PrefixNotSet("prefix for {} could not be found.".format(message.channel.server))

        # Else used just because reasons
        else:
            if client.user in message.mentions:

                # MentionHandler processes the message and returns the answer
                response = mention.on_message(message)

                if not response:
                    return
                else:
                    await client.send_message(message.channel,response)
                    stat.plusmsg()

                    return

                pass

            else:

                sc = handler.returncommands(message.channel.server)

                # Checks for server specific commands
                for command in sc:
                    if str(message.content).startswith(command):
                        # Maybe same replacement logic in the future update?
                        await client.send_message(message.channel, sc[command])
                        stat.plusmsg()

                        return

                # Existing command check (two steps)

                # 1.
                for this in normalcmds:
                    this = this.replace("_", self.prefixes.get(message.channel.server.id))
                    if str(message.content).startswith(this):
                        stat.plusmsg()

                        is_a_command = True
                        break

                # 2.
                if not is_a_command:
                    for this in admincmds:
                        this = this.replace("_", self.prefixes.get(message.channel.server.id))
                        if str(message.content).startswith(this):
                            stat.plusmsg()

                            is_admin_command = True
                            is_a_command = False
                            break

                # APPLIES FILTERS and returns
                if not is_a_command and not is_admin_command:

                    issf = iswf = isinv = invt = False
                    # If it is not a command, apply filters
                    sf = handler.needspamfilter(message.channel.server)
                    wf = handler.needwordfilter(message.channel.server)
                    inf = handler.needinvitefiler(message.channel.server)

                    if sf:
                        issf = mod.checkspam(message.content)

                    if wf:
                        iswf = mod.checkfilter(message.content)

                    if inf:
                        isinv, invt = mod.checkinvite(message.content)

                    # If need filtering, apply
                    if issf:

                        # Attempt to catch errors (messages not being there)
                        try:
                            await client.delete_message(message)
                        except discord.errors.NotFound:
                            pass

                    elif iswf:

                        try:
                            await client.delete_message(message)
                        except discord.errors.NotFound:
                            pass

                    elif isinv and not (is_admin or is_owner or is_server_owner):
                        logchannel = discord.utils.find(lambda channel: channel.name == handler.get_var(message.channel.server.id, "logchannel"), message.channel.server.channels)
                        try:
                            await client.delete_message(message)
                        except discord.errors.NotFound:
                            pass

                        st = str(invt.string[invt.start():invt.end()]).strip("https://discord.gg/").strip("http://discord.gg/")
                        await client.send_message(logchannel, "**{}** posted an invite\nServer: `{}`".format(message.author.mention, st))

                    return

        # Just a quick shortcut
        def startswith(string):
            if not message:
                raise MessageNotFoundError

            return str(message.content).lower().startswith(str(string))

        # nano.wake command check
        if startswith("nano.wake"):
            if not (is_admin or is_owner or is_server_owner):
                await client.send_message(message.channel, "You are not allowed to use this command.")
                return

            # Don't do anything if already awake
            if not handler.issleeping(message.channel.server):
                return

            handler.setsleeping(message.channel.server, 0)
            await client.send_message(message.channel, "I am back.")
            stat.plusslept()

        # Before checking for commands checks for sleep state and server file existence
        if handler.issleeping(message.channel.server):
            return

        if not handler.serverexists(message.channel.server):
            handler.server_setup(message.channel.server)

            log("Server settings set up: {}".format(message.channel.server))

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
                # All simple(r) commands
                await client.send_message(message.channel, simples.replace("_", prefix))
                stat.plushelpcommand()

            else:
                search = str(message.content)[len(prefix + "help "):]

                # Allows for !help ping AND !help !ping
                if not search.startswith(prefix):
                    search = prefix + search

                cmd = commandhelpsnormal.get(str(search.replace(prefix, "_").strip(" ")))
                if cmd is not None:
                    cmdn = search.replace(prefix, "")  # Changeable
                    desc = cmd["desc"]
                    use = cmd["use"]
                    alias = cmd["alias"]

                    # Compiles proper message
                    if use and alias:
                        preset = """Command: **{}**

```css
Description: {}

{}
{}```""".format(cmdn, desc, use, alias)

                    elif alias and not use:
                        preset = """Command: **{}**

```css
Description: {}

{}```""".format(cmdn, desc, alias)

                    elif use and not alias:
                        preset = """Command: **{}**

```css
Description: {}

{}```""".format(cmdn, desc, use)

                    elif not use and not alias:
                        preset = """Command: **{}**

```css
Description: {}```""".format(cmdn, desc)
                    else:
                        print("How is this even possible?!")
                        return

                    await client.send_message(message.channel, preset)

                    stat.plushelpcommand()
                    return

                cmd = commandhelpsadmin.get(str(search.replace(prefix, "_").strip(" ")))
                if cmd is not None:
                    cmdn = search.replace(prefix, "")  # Changeable
                    desc = cmd["desc"]
                    use = cmd["use"]
                    alias = cmd["alias"]

                    # Compiles proper message
                    if use and alias:
                        preset = """Command: **{}** (admins only)

```css
Description: {}

{}
{}```""".format(cmdn, desc, use, alias)

                    elif alias and not use:
                        preset = """Command: **{}** (admins only)

```css
Description: {}

{}```""".format(cmdn, desc, alias)

                    elif use and not alias:
                        preset = """Command: **{}** (admins only)

```css
Description: {}

{}```""".format(cmdn, desc, use)

                    elif not use and not alias:
                        preset = """Command: **{}** (admins only)

```css
Description: {}```""".format(cmdn, desc)
                    else:
                        print("How is this even possible?!")
                        return

                    await client.send_message(message.channel, preset)

                    stat.plushelpcommand()
                    return

                cmd = commandhelpsowner.get(str(search.replace(prefix, "_").strip(" ")))
                if cmd is not None:
                    cmdn = search.replace(prefix, "")  # Changeable
                    desc = cmd["desc"]
                    use = cmd["use"]
                    alias = cmd["alias"]

                    # Compiles proper message
                    if use and alias:
                        preset = """Command: **{}** (owner only)

```css
Description: {}

{}
{}```""".format(cmdn, desc, use, alias)

                    elif alias and not use:
                        preset = """Command: **{}** (owner only)

```css
Description: {}

{}```""".format(cmdn, desc, alias)

                    elif use and not alias:
                        preset = """Command: **{}** (owner only)

```css
Description: {}

{}```""".format(cmdn, desc, use)

                    elif not use and not alias:
                        preset = """Command: **{}** (owner only)

```css
Description: {}```""".format(cmdn, desc)
                    else:
                        print("How is this even possible?!")
                        return

                    await client.send_message(message.channel, preset)

                    stat.plushelpcommand()
                    return

                if cmd is None:
                    await client.send_message(message.channel, "Command could not be found.\n**(Use: `>help command`)**".replace(">", prefix))
                    stat.pluswrongarg()
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
                await client.send_message(message.channel, "Hi " + message.mentions[0].mention)
            elif len(message.mentions) == 0:
                await client.send_message(message.channel, "Hi " + message.author.mention)

        # Calculates uptime
        elif startswith(prefix + "uptime"):
            sec = timedelta(seconds=time.time() - self.boot_time)
            d = datetime(1, 1, 1) + sec
            uptime = "I have been tirelessly answering people for\n**{} days, {} hours, {} minutes and {} seconds!**".format(d.day - 1, d.hour, d.minute, d.second)

            await client.send_message(message.channel, uptime)

        # Replies with a random quote
        elif startswith(prefix + "quote"):
            chosen = str(quotes[randint(0, len(quotes)-1)])
            place = chosen.rfind("–")
            await client.send_message(message.channel, chosen[:place] + "\n__*" + chosen[place:] + "*__")

        # Answers your question - 8ball style
        elif startswith(prefix + "8ball"):
            answer = eightball[randint(0, len(eightball)-1)]
            await client.send_message(message.channel, "The magic 8ball says: *" + str(answer) + "*.")

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
                await client.send_message(message.channel, "Got multiple definitions of {}, please be more specific (somehow).".format(search))

        # Gets a definition from Urban Dictionary
        elif startswith(prefix + "urban"):
            search = str(message.content)[len(prefix + "urban "):]
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(search))
            answer = BeautifulSoup(define.content, "html.parser").find("div", attrs={"class": "meaning"}).text

            if str(answer).startswith("\nThere aren't any"):
                await client.send_message(message.channel, "No definition found")
            else:
                await client.send_message(message.channel, "**" + message.content[7:] + "** *:*" + answer)

        # Simple info
        elif startswith(prefix + "nano") or startswith("nano.info"):
            await client.send_message(message.channel, nanoinfo.replace("<version>", __version__))

        # GitHub repo link
        elif startswith(prefix + "github"):
            await client.send_message(message.channel, githubinfo)

        # Replies with current (custom) commands on the server
        elif startswith(prefix + "cmd list"):
                cmds = handler.returncommands(message.server)
                final = ""

                for this in cmds.keys():
                    final += "\n{} : {}".format(this, cmds[this])

                if not final:
                    await client.send_message(message.channel, "No custom commands on this server. Add one with `_cmd add trigger|response`!".replace("_", prefix))
                    return
                await client.send_message(message.channel, "*Custom commands:*" + final)

        # Vote creation
        elif startswith(prefix + "vote start"):
            if not (is_owner or is_admin or is_server_owner):
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                stat.pluswrongperms()
                return

            if vote.inprogress(message.channel.server):
                await client.send_message(message.channel, "A vote is already in progress.")
                return

            content = message.content[len(prefix + "vote start "):]

            vote.create(message.author.name, message.channel.server, content)
            ch = []

            n = 1
            for this in vote.getcontent(message.channel.server):
                ch.append("{}. {}".format(n, this))
                n += 1

            ch = "\n".join(ch).strip("\n")

            await client.send_message(message.channel, "**{}**\n```{}```".format(vote.returnvoteheader(message.channel.server), ch))

        # Vote end
        elif startswith(prefix + "vote end"):
            if not (is_owner or is_admin or is_server_owner):
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                stat.pluswrongperms()
                return

            if not vote.inprogress(message.channel.server):
                await client.send_message(message.channel, "There are no votes currently open.")

            votes = vote.returnvotes(message.channel.server)
            header = vote.returnvoteheader(message.channel.server)
            content = vote.returncontent(message.channel.server)

            # Reset!
            vote.end_voting(message.channel.server)

            cn = []
            for this in content:
                cn.append("{} - `{} vote(stm)`".format(this, votes[this]))

            combined = "Vote ended:\n**{}**\n\n{}".format(header, "\n".join(cn))

            await client.send_message(message.channel, combined)

        # People can vote with vote <number>
        elif startswith(prefix + "vote "):
            # Ignore if no votes are going on
            if not vote.inprogress(message.channel.server):
                    return

            if not startswith(prefix + "vote start") and not startswith(prefix + "vote end"):
                try:
                    num = int(str(message.content)[len(prefix + "vote "):])
                except ValueError:
                    stat.pluswrongarg()
                    # Update: now ignoring no-choices, making chat more clean
                    # await client.send_message(message.channel, "Please select your choice and reply with it's number :upside_down:")
                    return

                gotit = vote.countone(num, message.author.id, message.channel.server)
                stat.plusonevote()

                if gotit == -1:
                    sm = await client.send_message(message.channel, "No, you can't change your mind :smile:")
                else:
                    sm = await client.send_message(message.channel, "All right :ballot_box_with_check:")

                await asyncio.sleep(2)
                await client.delete_message(sm)

        # Simple status (server, user count)
        elif startswith(prefix + "status") or startswith("nano.status"):
            server_count = 0
            members = 0
            channels = 0

            for server in client.servers:
                server_count += 1
                members += int(server.member_count)

                channels += len(server.channels)

            stats = "**Stats**```Servers: {}\nUsers: {}\nChannels: {}```".format(server_count, members, channels)

            await client.send_message(message.channel, stats)

        # Some interesting stats
        elif startswith(prefix + "stats") or startswith("nano.stats"):

            file = stat.get_data()

            mcount = file.get("msgcount")
            wrongargc = file.get("wrongargcount")
            timesslept = file.get("timesslept")
            wrongpermc = file.get("wrongpermscount")
            pplhelp = file.get("peoplehelped")
            imgc = file.get("imagessent")
            votesc = file.get("votesgot")
            pings = file.get("timespinged")

            to_send = "**Stats**\n```python\n{} messages sent\n{} people yelled at because of wrong args\n{} people denied because of wrong permissions\n{} people helped\n{} votes got\n{} times slept\n{} images uploaded\n{} times Pong!-ed```"\
                .format(mcount, wrongargc, wrongpermc, pplhelp, votesc, timesslept, imgc, pings)
            await client.send_message(message.channel, to_send)

        # MUSIC
        # Music commands! ALPHA, needs multi-server implementation; only the owner can use this set of commands
        elif startswith(prefix + "music join"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            cut = str(message.content)[len(prefix + "music join "):]
            ch = discord.utils.find(lambda m: m.name == str(cut), message.channel.server.channels)

            # Opus load
            if not discord.opus.is_loaded():
                discord.opus.load_opus("libopus-0.x64.dll")

            if not discord.opus.is_loaded():
                await client.send_message(message.channel, "Opus lib could not be loaded (this feature is still in beta)")

            try:
                self.vc = await client.join_voice_channel(ch)
                await client.send_message(message.channel, "Joined **{}**!".format(cut))
            except discord.errors.InvalidArgument:
                self.vc = None
                await client.send_message(message.channel, "Could not join, **{}** is not a voice channel.".format(cut))
                stat.pluswrongarg()
                return

        elif startswith(prefix + "music leave"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):
                try:
                    self.yt_player.stop()
                except AttributeError:
                    pass

                self.yt_player = None
                await client.send_message(message.channel, "Left **" + self.vc.channel.name + "**")

                await self.vc.disconnect()
                self.vc = None

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        elif startswith(prefix + "music playing"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):

                if self.yt_player:  # If used 'music play'
                    title = self.yt_player.title
                    uploader = self.yt_player.uploader
                    dur = str(int(self.yt_player.duration / 60)) + ":" + str(self.yt_player.duration % 60)
                    views = self.yt_player.views

                    formatted = "{}: **{}**```\nDuration: {}\nUploader: {}\nViews: {}```".format(self.yt_status, title, str(dur), uploader, views)
                    await client.send_message(message.channel, formatted)

                else:
                    await client.send_message(message.channel, "Not playing anything at the moment")
            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_",prefix))

        elif startswith(prefix + "music play"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient):

                # If the song is still playing, ask the user to use !music skip
                if self.yt_player:
                    if self.yt_player.is_playing or not self.yt_player.is_done:
                        await client.send_message(message.channel, "*{}* is already playing, please **wait** or **skip** the song with `{}music skip`.".format(self.yt_player.title, prefix))
                        return

                args = str(message.content)[len(prefix + "music play "):]
                await client.send_typing(message.channel)

                try:
                    self.yt_player = await self.vc.create_ytdl_player(args)
                except ut.DownloadError:
                    await client.send_message(message.channel, "Not a valid URL or incompatible video :x:")

                while self.yt_player is None:
                    await asyncio.sleep(0.1)

                try:
                    await self.yt_player.start()
                except TypeError:
                    pass

                self.yt_player.volume = 0.4

                duration = str(int(self.yt_player.duration / 60)) + ":" + str(self.yt_player.duration % 60)
                await client.send_message(message.channel, "Playing **{}**\n**Duration:** `{}`\n**Uploader:** `{}`\n**Views:** `{}`"
                                          .format(self.yt_player.title, duration, self.yt_player.uploader, self.yt_player.views))
                self.yt_status = "Playing"

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Skips (ytplayer.stop()) / stops the current song
        elif startswith(prefix + "music skip") or startswith(prefix + "music stop"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.yt_player, StreamPlayer):
                if self.yt_player.is_playing():
                    self.yt_player.stop()

                    self.yt_player = None

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Set or figure out the current volume (accepts 0 - 150)
        elif startswith(prefix + "music volume"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.yt_player, StreamPlayer):
                args = str(message.content)[len(prefix + "music volume "):]

                if args == "":
                    if self.yt_player is not None:
                        await client.send_message(message.channel, "Current volume is **" + str(self.yt_player.volume) + "**")
                    else:
                        await client.send_message(message.channel, "Not playing anything (default volume will be *40*)")

                else:

                    try:
                        if not (150 >= int(args) >= 0):
                            await client.send_message(message.channel,"Please use **0 - 150** (100 equals 100% - normal volume)")
                    except ValueError:
                        await client.send_message(message.channel, "Not a number :x:")

                    argss = round(int(args)/100,2)
                    self.yt_player.volume = argss

                    await client.send_message(message.channel, "Volume set to " + str(args))

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Pauses the curent song (if any)
        elif startswith(prefix + "music pause"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.yt_player, StreamPlayer):

                if self.yt_player.is_playing():
                    self.yt_player.pause()
                    self.yt_status = "Paused"
                else:
                    pass

            else:
                await client.send_message(message.channel, ":warning: Not connected, please use `_music join channelname` to continue".replace("_", prefix))

        # Resumes the current song (if any)
        elif startswith(prefix + "music resume"):
            if not is_owner:
                await client.send_message(message.channel, "This feature is not yet finished. Only the owner is permitted to use this command.")
                return

            # If self.vc exists
            if isinstance(self.vc, discord.VoiceClient) and isinstance(self.yt_player, StreamPlayer):

                if not self.yt_player.is_playing():
                    self.yt_player.resume()
                    self.yt_status = "Playing"
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
        elif startswith(prefix + "bug") or startswith("nano.bug"):
            await client.send_message(message.channel, bugreport.replace("_", prefix))

        elif startswith(prefix + "feature"):
            await client.send_message(message.channel, featurereq)

        elif startswith(prefix + "changes") or startswith(prefix + "changelog"):
            await client.send_message(message.channel, "Changes in the recent versions can be found here: https://github.com/DefaltSimon/Nano/blob/master/changes.txt")

        elif startswith(prefix + "steam"):
            if startswith(prefix + "steam friends "):
                uid = str(message.content)[len(prefix + "steam friends "):]

                # Friend search
                await client.send_typing(message.channel)
                username, friends = stm.get_friends(uid)

                friends = ["`" + friend + "`" for friend in friends]

                if not username:
                    await client.send_message(message.channel, "User **does not exist**.")
                    stat.pluswrongarg()
                    return

                await client.send_message(message.channel, "*User:* **{}**\n\n*Friends:* {}".format(username, ", ".join(friends)))

            elif startswith(prefix + "steam games"):
                uid = str(message.content)[len(prefix + "steam games "):]

                # Game search
                await client.send_typing(message.channel)
                username, games = stm.get_owned_games(uid)

                if not username:
                    await client.send_message(message.channel, "User **does not exist**.")
                    stat.pluswrongarg()
                    return

                games = ["`" + game + "`" for game in games]

                try:
                    await client.send_message(message.channel, "*User:* **{}**:\n\n*Owned games:* {}".format(username, ", ".join(games)))
                except discord.HTTPException:
                    await client.send_message(message.channel, "This message can not fit onto Discord: **user has too many games to display (lol)**")

            elif startswith(prefix + "steam user "):
                uid = str(message.content)[len(prefix + "steam user "):]

                # Basic search
                await client.send_typing(message.channel)
                steamuser = stm.get_user(uid)

                if not steamuser:
                    await client.send_message(message.channel, "User **does not exist**.")
                    stat.pluswrongarg()
                    return

                ms = """User: **{}**
```css
Status: {}
Level: {}
Games: {} owned (including free games)
Friends: {}```\nDirect link: http://steamcommunity.com/id/{}/""".format(steamuser.name, "Online" if steamuser.state else "Offline", steamuser.level, len(steamuser.games), len(steamuser.friends), uid)

                try:
                    await client.send_message(message.channel, ms)
                except discord.HTTPException:
                    await client.send_message(message.channel, "This message can not fit onto Discord: **user has too many friends to display (lol)**")

            elif startswith(prefix + "steam") or startswith(prefix + "steam help"):
                await client.send_message(message.channel, "**Steam commands:**\n`_steam user community_url`, `_steam friends community_url`, `_steam games community_url`")

        elif startswith(prefix + "mc") or startswith(prefix + "minecraft"):
            if startswith(prefix + "mc "):
                da = message.content[len(prefix + "mc "):]
            elif startswith(prefix + "minecraft "):
                da = message.content[len(prefix + "minecraft "):]

            else:
                # Help message
                await client.send_message(message.channel, "**Minecraft**\n```css\n_mc name/id:meta - search for items and display their details```".replace("_", prefix))
                return

            # Determines if arg is id or name
            if len(str(da).split(":")) > 1:
                typ = 1

            else:
                try:
                    int(da)
                    typ = 1
                except ValueError:
                    typ = 2

            # Requests item data from minecraft plugin
            if typ == 1:
                data = mc.id_to_data(da)
            else:
                # Group(ify)
                if str(da).lower() == "wool":
                    data = mc.group_to_list(35)
                elif str(da).lower() == "stone":
                    data = mc.group_to_list(1)
                elif str(da).lower() == "wood plank":
                    data = mc.group_to_list(5)
                elif str(da).lower() == "sapling":
                    data = mc.group_to_list(6)
                elif str(da).lower() == "sand":
                    data = mc.group_to_list(12)
                elif str(da).lower() == "wood":
                    data = mc.group_to_list(17)
                elif str(da).lower() == "leaves":
                    data = mc.group_to_list(18)
                elif str(da).lower() == "sponge":
                    data = mc.group_to_list(19)
                elif str(da).lower() == "sandstone":
                    data = mc.group_to_list(24)
                elif str(da).lower() == "flower":
                    data = mc.group_to_list(38)
                elif str(da).lower() == "double slab":
                    data = mc.group_to_list(43)
                elif str(da).lower() == "slab":
                    data = mc.group_to_list(44)
                elif str(da).lower() == "stained glass":
                    data = mc.group_to_list(95)
                elif str(da).lower() == "monster egg":
                    data = mc.group_to_list(97)
                elif str(da).lower() == "stone brick":
                    data = mc.group_to_list(98)
                elif str(da).lower() == "double wood slab":
                    data = mc.group_to_list(125)
                elif str(da).lower() == "wood slab":
                    data = mc.group_to_list(126)
                elif str(da).lower() == "quartz block":
                    data = mc.group_to_list(155)
                elif str(da).lower() == "stained clay":
                    data = mc.group_to_list(159)
                elif str(da).lower() == "stained glass pane":
                    data = mc.group_to_list(160)
                elif str(da).lower() == "prismarine":
                    data = mc.group_to_list(168)
                elif str(da).lower() == "carpet":
                    data = mc.group_to_list(171)
                elif str(da).lower() == "plant":
                    data = mc.group_to_list(175)
                elif str(da).lower() == "sandstone":
                    data = mc.group_to_list(179)
                elif str(da).lower() == "fish":
                    data = mc.group_to_list(349)
                elif str(da).lower() == "dye":
                    data = mc.group_to_list(351)
                elif str(da).lower() == "egg":
                    data = mc.group_to_list(383)
                elif str(da).lower() == "head":
                    data = mc.group_to_list(397)

                else:
                    data = mc.name_to_data(str(da))

            if not data:
                await client.send_message(message.channel, "**No item with that name/id**")
                stat.pluswrongarg()
                return

            if not isinstance(data, list):
                details = """**{}**
```css
Id: {}:{}```""".format(data.get("name"), data.get("type"), data.get("meta"))

                # Details are uploaded simultaneously with the picture
                with open("plugins/mc_item_png/{}-{}.png".format(data.get("type"), data.get("meta") or 0), "rb") as pic:
                    await client.send_file(message.channel, pic, content=details)
                    stat.plusimagesent()
            else:
                combined = []
                for item in data:
                    details = """**{}**
```css
Id: {}:{}```""".format(item.get("name"), item.get("type"), item.get("meta"))
                    combined.append(details)

                await client.send_message(message.channel, "".join(combined))

        elif startswith(prefix + "tf"):
            da = message.content[len(prefix + "tf "):]

            item = tf.get_item_by_name(str(da))

            if not item:
                await client.send_message(message.channel, "An item with that name *does not exist*.".format(da))
                stat.pluswrongarg()
                return

            ls = []
            for qu in item.get_all_qualities():
                down = qu.get(list(qu.keys())[0])
                dt = "__**{}**__: `{} {}`".format(bptf.get_quality_name(list(qu.keys())[0]), down.get("price").get("value"), "ref" if down.get("price").get("currency") == "metal" else down.get("price").get("currency"))
                ls.append(dt)

            det = """**{}** *(on bp.tf)*\n\n{}""".format(item.name, "\n".join(ls))
            await client.send_message(message.channel, det)

        elif startswith(prefix + "imdb"):
            await client.send_typing(message.channel)

            if startswith(prefix + "imdb plot") or startswith(prefix + "imdb story"):
                if startswith(prefix + "imdb plot"):
                    search = str(message.content[len(prefix + "imdb plot "):])
                else:
                    search = str(message.content[len(prefix + "imdb story "):])

                data = idb.get_page_by_name(search)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == imdb.PERSON:
                    return
                else:
                    await client.send_message(message.channel, "**{}**'s story\n```{}```".format(data.name, data.storyline))

            elif startswith(prefix + "imdb search"):
                search = str(message.content[len(prefix + "imdb search "):])
                data = idb.get_page_by_name(search)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == imdb.MOVIE:
                    st = """**{}** ({})

Length: `{}`
Genres: {}
Rating: **{}/10**

Director: *{}*
Summary:
```{}```""".format(data.name, data.year, data.length, str("`" + "`, `".join(data.genres) + "`"), data.rating, data.director, data.summary)
                elif data.type == imdb.SERIES:
                    st = """**{}** series

Genres: {}
Rating: **{}/10**

Director: *{}*
Summary:
```{}```""".format(data.name, str("`" + "`, `".join(data.genres) + "`"), data.rating, data.director, data.summary)

                elif data.type == imdb.PERSON:
                    st = """**{}**

Known for: {}
IMDB Rank: **{}**

Short bio:
```{}```""".format(data.name, str("`" + "`, `".join(data.known_for) + "`"), data.rank, data.short_bio)

                else:
                    return

                await client.send_message(message.channel, st)

            elif startswith(prefix + "imdb trailer"):
                search = str(message.content[len(prefix + "imdb trailer "):])
                data = idb.get_page_by_name(search)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == imdb.PERSON:
                    return

                await client.send_message(message.channel, "**{}**'s trailer on IMDB: {}".format(data.name, data.trailer))

            elif startswith(prefix + "imdb rating"):
                search = str(message.content[len(prefix + "imdb rating "):])
                data = idb.get_page_by_name(search)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if not data.type == imdb.MOVIE:
                    await client.send_message(message.channel, "Only movies have Metascores.")
                    return

                await client.send_message(message.channel,
                                          "**{}**'s ratings on IMDB\nUser ratings: __{} out of 10__\nMetascore: __{}__".format(data.name, data.rating, data.metascore))

            else:
                await client.send_message(message.channel, "**IMDB help**\n\n`_imdb search [name or title]`, `_imdb plot [title]`, `_imdb trailer [title]`, `_imdb rating [title]`".replace("_", prefix))

        elif startswith(prefix + "say"):
            da = message.content[len(prefix + "say "):]

            ok = False
            for roles in message.author.roles:
                if roles.permissions.mention_everyone:
                    ok = True

            if message.channel.server.owner == message.author:
                ok = True

            # Apply @ filters
            if not ok:
                da = da.replace("@", "")

            await client.send_message(message.channel, da)

        elif startswith(prefix + "members"):
            ls = []
            for member in message.channel.server.members:
                ls.append(member.name)

            if len(ls) > 150:
                await client.send_message(message.channel, ":warning: Too many members on this server! Don't wanna freeze!")
                return

            ls = ["`{}`".format(mem) for mem in ls]

            await client.send_message(message.channel, "*__Members__*:\n\n{}".format(", ".join(ls)))

        elif startswith(prefix + "notifydev") or startswith(prefix + "suggest"):
            if startswith(prefix + "notifydev"):
                report = message.content[len(prefix + "notifydev "):]
                typ = "Report"
            elif startswith(prefix + "suggest"):
                report = message.content[len(prefix + "suggest "):]
                typ = "Suggestion"
            else:
                return

            ownerserver = discord.utils.get(client.servers, id=parser.get("Dev", "serverid"))

            # Timestamp
            ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            # 'Compiled' report
            comp = """{} from {} ({}):
```{}```
**__Timestamp__**: `{}`
**__Server__**: `{}` ({} members)
**__Server Owner__**: {}
""".format(typ ,message.author.name, message.author.id, report, ts, message.channel.server.name, message.channel.server.member_count, "Yes" if message.author.id == message.channel.server.owner.id else message.channel.server.owner.id)

            # Saves the submission to disk
            if int(ownerserver.owner.id) != int(self.owner_id):
                save_submission("Should have sent report, but {} would receive it: {}".format(ownerserver.owner.name, comp.replace(message.author.mention, str(message.author.name + "(" + message.author.id + ")")) + "\n"))
            else:
                save_submission(comp.replace(message.author.mention, str(message.author.name + "(" + message.author.id + ")")) + "\n")

            await client.send_message(ownerserver.owner, comp)

            await client.send_message(message.channel, "**Thank you** for your *{}*.".format("submission" if typ == "Report" else "suggestion"))

            await asyncio.sleep(4)

        elif startswith(prefix + "remind me in "):
            st = [a.strip(" ") for a in str(message.content)[len(prefix + "remind me in "):].split(":")]

            if len(st) == 1:
                st = [a.strip(" ") for a in str(message.content)[len(prefix + "remind me in "):].split("about")]

            if len(st) < 2:
                await client.send_message("That is not the proper use of this command. Use `_remind` to get more info.".replace("_", prefix))
                stat.pluswrongarg()
                return

            try:
                s = rem.remind_in_sec(message.author, message.author, st[1], rem.convert_to_seconds(st[0]))
            except timing.ReminderLimitExceeded:
                await client.send_message(message.channel, "You have exceeded the max limit - **2 active reminders**")
                return

            if not s:
                await client.send_message(message.channel, "Allowed range: from 5 seconds to 3 days :alarm_clock:")

            await client.send_message(message.channel, "Reminder set.")

        elif startswith(prefix + "remind here in "):
            st = [a.strip(" ") for a in str(message.content)[len(prefix + "remind here in "):].split(":")]

            if len(st) == 1:
                st = [a.strip(" ") for a in str(message.content)[len(prefix + "remind here in "):].split("about")]

            try:
                s = rem.remind_in_sec(message.channel, message.author, st[1], rem.convert_to_seconds(st[0]))
            except timing.ReminderLimitExceeded:
                await client.send_message(message.channel, "You have exceeded the max limit - **2 active reminders**")
                return

            await client.send_message(message.channel, "Reminder set.")

        elif startswith(prefix + "remind list") or startswith(prefix + "reminder list"):
            ls = rem.get_reminders(message.author)

            if ls:
                st = """Your reminders:"""
                for things in ls:
                    tm = abs(time.time() - things[2] - things[0])
                    st += "\n{} - up in `{}`".format(things[1], timing.resolve_time(tm))

                await client.send_message(message.channel, st)

            else:
                await client.send_message(message.channel, "You have not set any **reminders**.")

        elif startswith(prefix + "remind remove") or startswith(prefix + "reminder remove"):

            if startswith(prefix + "remind remove"):
                st = str(message.content)[len(prefix + "remind remove "):]

            elif startswith(prefix + "reminder remove"):
                st = str(message.content)[len(prefix + "reminder remove "):]

            else:
                return

            if st == "all":
                rem.remove_all_reminders(message.author)

                await client.send_message(message.channel, "Removed **all** active reminders!")

            else:
                su = rem.remove_reminder(message.author, st)

                if su:
                    await client.send_message(message.channel, "Successfully removed the reminder.")
                else:
                    await client.send_message(message.channel, "Could not remove the reminder. Command usage: `_remind remove [time or content]`")

        elif startswith(prefix + "remind"):
            await client.send_message(message.channel, "**Remind help**\n`_remind me in [sometime]: [message]` - reminds you in your DM\n`_remind here in [sometime]: [message]` - reminds everyone in current channel".replace("_", prefix))

        #
        # Here start ADMIN ONLY commands
        #

        # If it does not fall under 'normal' commands, check for admin command before denying permission

        # If a command was already executed, return
        # If it is not an admin command, return before sending 'no permission' message
        if is_a_command and not is_admin_command:
            return

        if not (is_owner or is_server_owner):
            if not is_admin:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                stat.pluswrongperms()
                return

        if startswith(prefix + "welcomemsg"):
            msg = message.content[len(prefix + "welcomemsg "):]
            handler.update_var(message.channel.server.id, "welcomemsg", msg)
            await client.send_message(message.channel, "Welcome message has been updated :smile:")

        elif startswith(prefix + "banmsg"):
            msg = message.content[len(prefix + "banmsg "):]
            handler.update_var(message.channel.server.id, "banmsg", msg)
            await client.send_message(message.channel, "Ban message has been updated :smile:")

        elif startswith(prefix + "kickmsg"):
            msg = message.content[len(prefix + "kickmsg "):]
            handler.update_var(message.channel.server.id, "kickmsg", msg)
            await client.send_message(message.channel, "Kick message has been updated :smile:")

        elif startswith(prefix + "leavemsg"):
            msg = message.content[len(prefix + "leavemsg "):]
            handler.update_var(message.channel.server.id, "leavemsg", msg)
            await client.send_message(message.channel, "Leave message has been updated :smile:")

        # Simple ban with CONFIRM check
        elif startswith(prefix + "ban") or startswith("nano.ban"):
            name = None

            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:

                try:

                    if startswith(prefix + "ban"):
                        name = str(str(message.content)[len(prefix + "ban "):])
                    elif startswith("nano.ban"):
                        name = str(str(message.content)[len("nano.ban "):])
                    else:
                        return
                except IndexError:
                    return

                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            if not user:
                return

            await client.send_message(message.channel, "Are you sure you want to ban " + user.name + "? Confirm by replying with 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel, timeout=15, content="CONFIRM")
            if followup is None:
                await client.send_message(message.channel, "Confirmation not received, NOT banning :upside_down:")

            else:
                await client.ban(user)
                await client.send_message(message.channel, handler.get_var(message.channel.server.id, "banmsg").replace(":user", user.name))

        elif startswith(prefix + "softban") or startswith("nano.softban"):
            if startswith(prefix + "softban "):
                try:
                    cut = str(message.content)[len(prefix + "softban "):].rsplit("<")
                    name = cut[1]; cut = cut[0]
                except IndexError:
                    cut = str(message.content)[len(prefix + "softban "):].rsplit(" ")
                    name = cut[1]; cut = cut[0]
            else:
                try:
                    cut = str(message.content)[len("nano.softban "):].rsplit("<")
                    name = cut[1]; cut = cut[0]
                except IndexError:
                    cut = str(message.content)[len("nano.softban "):].rsplit(" ")
                    name = cut[1]; cut = cut[0]

            if len(message.mentions) >= 1:
                usr = message.mentions[0]
            else:
                await client.send_message(message.channel, "Please mention a person to softban.")
                return
                #usr = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            if not usr:
                await client.send_message(message.channel, "User not found.")
                return

            md = timing.Reminder.convert_to_seconds(cut)
            a = timebans.time_ban(message.channel.server, usr, md)

            if a:

                if not self.softbans.get(message.server.id):
                    self.softbans.update(
                        {message.server.id: {usr.id: timing.resolve_time(md)}}
                        )
                else:
                    self.softbans[message.server.id].update(
                        {usr.id: timing.resolve_time(md)}
                        )

                await client.send_message(message.channel, "**{}** has been softbanned for `{}`".format(usr.name, timing.resolve_time(md)))

        # Simple unban with CONFIRM check
        elif startswith(prefix + "unban") or startswith("nano.unban"):
            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:

                try:
                    if startswith(prefix + "unban"):
                        name = str(str(message.content)[len(prefix + "unban "):])
                    elif startswith("nano.unban"):
                        name = str(str(message.content)[len("nano.unban "):])
                    else:
                        return
                except IndexError:
                    return

                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            if not user:
                return

            await client.send_message(message.channel,"Are you sure you want to unban " + user.name + "? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel, timeout=15, content="CONFIRM")
            if followup is None:
                await client.send_message(message.channel, "Confirmation not received, NOT banning :upside_down:")

            else:
                await client.unban(user)
                await client.send_message(message.channel, "**{}** has been unbanned. woot!".format(user.name))

        # Simple kick WITHOUT double check
        elif startswith(prefix + "kick") or startswith("nano.kick"):
            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:

                try:
                    if startswith(prefix + "kick"):
                        name = str(str(message.content)[len(prefix + "kick "):])
                    elif startswith("nano.kick"):
                        name = str(str(message.content)[len("nano.kick "):])
                    else:
                        return

                except IndexError:
                    return

                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            if not user:
                return

            await client.kick(user)
            await client.send_message(message.channel, handler.get_var(message.channel.server.id, "kickmsg").replace(":user", user.name))

        # Sleep command
        elif startswith("nano.sleep"):
            handler.setsleeping(message.channel.server, 1)
            await client.send_message(message.channel, "Going to sleep... :zipper_mouth:")

        # Wake command is defined at the beginning

        # Avatar
        elif startswith(prefix + "avatar"):
            # Selects the proper user
            if len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "avatar "):])
                member = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)
            else:
                member = message.mentions[0]

            if not member:
                member = message.author

            url = member.avatar_url

            if not url:
                await client.send_message(message.channel, "**{}** does not have an avatar. :expressionless:".format(member.name))
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
                a_role = str(message.content[len(prefix + "role " + "add "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == a_role, message.channel.server.roles)

                await client.add_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "remove "):
                a_role = str(message.content[len(prefix + "role " + "remove "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == a_role, message.channel.server.roles)

                await client.remove_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "replacewith "):
                a_role = str(message.content[len(prefix + "role replacewith "):]).split("<")[0].strip()
                role = discord.utils.find(lambda role: role.name == a_role, message.channel.server.roles)

                await client.replace_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

        # Server setup should be automatic, but if you want to reset settings, here ya go
        elif startswith("nano.serversetup") or startswith("nano.server.setup"):
            handler.server_setup(message.channel.server)
            log("Server settings set up: {}".format(message.channel.server))
            await client.send_message(message.channel, "Server settings reset :upside_down:")

            self.update_admins()
            self.update_prefixes()
            self.update_mutes()

        # Command management
        elif startswith(prefix + "cmd"):

            if startswith(prefix + "cmd add"):
                try:
                    cut = str(message.content)[len(prefix + "cmd add "):].split("|")
                    handler.update_command(message.server, cut[0], cut[1])
                    await client.send_message(message.channel, "Command '{}' added.".format(cut[0]))

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
                handler.remove_command(message.server, cut)
                await client.send_message(message.channel, "Ok :white_check_mark: ")

            # Cmd list does not require admin permission so it was moved under normal commands

        elif startswith("nano.admins"):

            if startswith("nano.admins add"):
                if len(message.mentions) > 20:
                    await client.send_message(message.channel, "Too muchhh!\nSeriously, up to 20 at a time")
                    stat.pluswrongarg()
                    return
                elif len(message.mentions) == 0:
                    await client.send_message(message.channel, "Please mention someone to make them admins")
                    stat.pluswrongarg()
                    return

                count = 0
                for ment in message.mentions:
                    handler.add_admin(message.server, ment)
                    count += 1

                if count == 1:
                    await client.send_message(message.channel, "Added **{}** to admins :white_check_mark: ".format(message.mentions[0].name))
                else:
                    await client.send_message(message.channel, "Added **{}** people to admins :white_check_mark: ".format(count))

                self.update_admins()

            elif startswith("nano.admins remove"):
                if len(message.mentions) > 20:
                    await client.send_message(message.channel, "Too muchhh!\nSeriously, up to 20 at a time")
                    stat.pluswrongarg()
                    return
                elif len(message.mentions) == 0:
                    await client.send_message(message.channel, "Please mention someone to remove them from admin position")
                    stat.pluswrongarg()
                    return

                count = 0
                for ment in message.mentions:
                    handler.remove_admin(message.server, ment)
                    count += 1

                if count == 1:
                    await client.send_message(message.channel, "Removed **{}** from admins :white_check_mark: ".format(message.mentions[0].name))
                else:
                    await client.send_message(message.channel, "Removed **{}** people from admins :white_check_mark: ".format(count))

                self.update_admins()

            elif startswith("nano.admins list"):
                self.update_admins()
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

        # A link to invite nano to your server
        elif startswith(prefix + "invite") or startswith("nano.invite"):
            clientappid = await client.application_info()

            # Most of the permissions that Nano uses
            perms = str("0x510917638")
            url = 'https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions={}'.format(clientappid.id, perms)

            await client.send_message(message.channel, appinfo.replace("<link>", url))

        # Displays current settings, including the prefix
        elif startswith("nano.displaysettings"):
                    settings = handler.get_server_data(message.server.id)
                    bchan = ",".join(settings["blacklisted"])

                    if not bchan:
                        bchan = "None"

                    spam = "On" if settings["filterspam"] else "Off"

                    wfilter = "On" if settings["filterwords"] else "Off"

                    invrem = "On" if settings["filterinvite"] else "Off"

                    await client.send_message(message.channel, """**Settings for current server:**
```css
Blacklisted channels: {}
Spam filter: {}
Word filter: {}
Invite removal: {}
Log channel: {}
Prefix: {}```
Messages:
➤ Join: `{}`
➤ Leave: `{}`
➤ Ban: `{}`
➤ Kick: `{}`""".format(bchan, spam, wfilter, invrem, settings.get("logchannel") if settings.get("logchannel") else "None", settings.get("prefix"), settings.get("welcomemsg"), settings.get("leavemsg"), settings.get("banmsg"), settings.get("kickmsg")))

        elif startswith("nano.settings"):
            try:
                cut = str(message.content)[len("nano.settings "):].rsplit(" ", 1)
            except IndexError:
                return
            try:
                value = handler.update_moderation_settings(message.channel.server, cut[0], decide(cut[1]))
            except IndexError:
                stat.pluswrongarg()
                return

            if decide(cut[0], ("word filter", "filter words", "wordfilter")):
                if value:
                    await client.send_message(message.channel, "Word filter :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Word filter :negative_squared_cross_mark:")

            elif decide(cut[0], ("spam filter", "spamfilter", "filter spam")):
                if value:
                    await client.send_message(message.channel, "Spam filter :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Spam filter :negative_squared_cross_mark:")

            elif decide(cut[0], ("filterinvite", "filterinvites", "invite removal", "invite filter")):
                if value:
                    await client.send_message(message.channel, "Invite filter :white_check_mark:")
                else:
                    await client.send_message(message.channel, "Invite filter :negative_squared_cross_mark:")

        # Blacklists individual channels
        elif startswith("nano.blacklist"):
            if startswith("nano.blacklist add"):
                cut = str(str(message.content)[len("nano.blacklist add "):])
                handler.add_channel_blacklist(message.channel.server, cut)

                await client.send_message(message.channel, "**{}** has been blacklisted!".format(cut))

            elif startswith("nano.blacklist remove "):
                cut = str(str(message.content)[len("nano.blacklist remove "):])
                handler.remove_channel_blacklist(message.channel.server, cut)

                await client.send_message(message.channel, "No worries, **{}** has been removed from the blacklist!".format(cut))

        # GET STARTED
        elif startswith(prefix + "getstarted") or startswith("nano.getstarted"):

            auth = message.author

            async def timeout(msg):
                await client.send_message(msg.channel, "You ran out of time :upside_down: (FYI: the timeout is 20 seconds)")
                return

            answers = {}

            msg_intro = """**SERVER SETUP**
You have started the server setup. It consists of a few steps, where you will be prompted to answer.
**Let's get started, shall we?**"""""
            await client.send_message(message.channel, msg_intro)
            await asyncio.sleep(2)

            # FIRST MESSAGE
            msg_one = """Do you want to reset all bot-related settings for this server?
(this includes spam and swearing protection, admin list, blacklisted channels, log channel, prefix, welcome, ban and kick message). yes/no"""
            await client.send_message(message.channel, msg_one)

            # First check

            def check_yes1(msg):
                global choice1
                # yes or no
                if str(msg.content).lower().strip(" ") == "yes":
                    answers["reset"] = True
                    return True
                else:
                    answers["reset"] = False
                    return True

            ch1 = await client.wait_for_message(timeout=35, author=auth, check=check_yes1)
            if ch1 is None:
                timeout(message)
                return

            if answers["reset"]:
                handler.server_setup(message.channel.server)

            # SECOND MESSAGE
            msg_two = """What prefix would you like to use for all commands?
Type that prefix.\n(prefix example: **!** 'translates to' `!help`)"""
            await client.send_message(message.channel,msg_two)

            # Second check, does not need yes/no filter
            ch2 = await client.wait_for_message(timeout=35, author=auth)
            if ch2 is None:
                timeout(message)

            if ch2.content:
                handler.change_prefix(message.channel.server, ch2.content)

            # THIRD MESSAGE
            msg_three = """What would you like me to say when a person joins your server?
Reply with that message or with None if you want to disable welcome messages."""
            await client.send_message(message.channel, msg_three)

            ch3 = await client.wait_for_message(timeout=35, author=auth)
            if ch3 is None:
                timeout(message)

            if ch3.content.strip(" ") == "None":
                handler.update_var(message.server.id, "welcomemsg", None)
            else:
                handler.update_var(message.server.id, "welcomemsg", str(ch3.content))

            # FOURTH MESSAGE
            msg_four = """Would you like me to filter spam? yes/no"""
            await client.send_message(message.channel, msg_four)

            # Fourth check

            def check_yes3(msg):
                # yes or no
                if str(msg.content).lower().strip(" ") == "yes":
                    answers["spam"] = True
                    return True
                else:
                    answers["spam"] = False
                    return True

            ch3 = await client.wait_for_message(timeout=35, author=auth, check=check_yes3)
            if ch3 is None:
                timeout(message)

            if answers["spam"]:
                handler.update_moderation_settings(message.channel.server, "filterspam", True)
            else:
                handler.update_moderation_settings(message.channel.server, "filterspam", False)

            # FIFTH MESSAGE
            msg_five = """Would you like me to filter swearing? yes/no"""
            await client.send_message(message.channel, msg_five)

            # Fifth check check

            def check_yes4(msg):
                # yes or no
                if str(msg.content).lower().strip(" ") == "yes":
                    answers["words"] = True
                    return True
                else:
                    answers["words"] = False
                    return True

            ch4 = await client.wait_for_message(timeout=35, author=auth, check=check_yes4)
            if ch4 is None:
                timeout(message)

            if answers["words"]:
                handler.update_moderation_settings(message.channel.server, "filterwords", True)
            else:
                handler.update_moderation_settings(message.channel.server, "filterwords", False)

            msg_final = """**This concludes the basic server setup.**
But there are a few more settings to set up if you need'em:
➤ channel blacklisting - `nano.blacklist add/remove channel_name`
➤ kick message - `_kickmsg message`
➤ ban message - `_banmsg message`

The prefix can simply be changed again with `nano.changeprefix prefix`.

You and all admins can also add/remove/list custom commands with `_cmd add/remove/list command|response`.
For more detailed descriptions about all commands, type `_cmds`.
""".replace("_", str(ch2.content))

            await client.send_message(message.channel, msg_final)

            self.update_admins()
            self.update_prefixes()

        elif startswith("nano.changeprefix"):
            cut = str(message.content)[len("nano.changeprefix "):]
            handler.change_prefix(message.channel.server, str(cut))

            await client.send_message(message.channel, "Prefix has been changed :heavy_check_mark:")

            self.update_prefixes()

        # Shuts the bot down
        elif startswith("nano.kill"):
            # Restricted to owner
            if not is_owner:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            m = await client.send_message(message.channel, "Staving state...")

            if not os.path.isdir("cache"): os.mkdir("cache")

            with open("cache/voting_state.cache", "wb") as cache:
                dump(vote, cache)  # Save instance of Vote

            # with open("cache/reminder_state.cache", "wb") as cache:
            #    dump(rem, cache)  # Save instance of Reminder

            await client.send_message(message.channel, "**DED**")
            await client.delete_message(m)

            await client.logout()
            exit(0)

        # Restarts the bot
        elif startswith("nano.restart"):
            # Restricted to owner
            if not is_owner:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            m = await client.send_message(message.channel, "Staving state and restarting...")

            if not os.path.isdir("cache"): os.mkdir("cache")

            with open("cache/voting_state.cache", "wb") as cache:
                dump(vote, cache)  # Save instance of Vote

            # with open("cache/reminder_state.cache", "wb") as cache:
            #     dump(rem, cache)  # Save instance of Reminder

            await client.send_message(message.channel, "**DED**")
            await client.delete_message(m)

            await client.logout()

            if sys.platform == "win32":
                p = subprocess.Popen("startbot.bat")
            else:
                p = subprocess.Popen(os.path.abspath("startbot.sh"), shell=True)

            sys.exit(0)

        # Changes 'playing' status
        elif startswith(prefix + "playing"):
            # Restricted to owner
            if not is_owner:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            cut = str(message.content)[len(prefix + "playing "):]
            await client.change_status(game=discord.Game(name=cut))

            await client.send_message(message.channel, "Status set :white_check_mark:")

        # Reloads settings.ini, prefixes and admins
        elif startswith(prefix + "reload") + startswith("nano.reload"):
            # Restricted to owner
            if not is_owner:
                await client.send_message(message.channel, "You are not permitted to use this command. :x:")
                return

            handler.reload()

            # Dependant on handler.reload()
            self.update_admins()
            self.update_prefixes()
            self.update_mutes()

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
            avatar = str(member.avatar_url)

            bott = ":robot" if member.bot else ""

            role = member.top_role
            create_date = member.created_at
            st = "ONLINE" if member.status.online or member.status.idle else "OFFLINE"

            # 'Compiles' info
            mixed = """User: **{}** {} {}
➤ Status: {}
➤ Id: {}
➤ Avatar: {}

➤ Top role_: {}
➤ Created at: {}""".format(name, member.discriminator, bott, st, mid, avatar, role, create_date)

            await client.send_message(message.channel, mixed)

        # Muting system
        elif startswith(prefix + "muted"):
            self.update_mutes()
            lst = handler.mutelist(message.channel.server)

            for c, el in enumerate(lst):
                lst[c] = discord.utils.find(lambda m: m.id == el, message.channel.server.members).name

            if not lst:
                await client.send_message(message.channel, "No muted members.")
                return

            cp = "**Muted members:**\n```" + ", ".join(lst) + "```"
            await client.send_message(message.channel, cp)

        elif startswith(prefix + "mute"):
            if len(message.mentions) == 1:
                user = message.mentions[0]

            elif len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "mute "):])
                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            else:
                await client.send_message(message.channel, "Please mention somebody to mute him/her.")
                return

            if not user:
                return

            if user.id == self.owner_id:
                return

            handler.mute(user)
            await client.send_message(message.channel, "{} has been muted :no_bell:".format(user.name))
            self.update_mutes()

        elif startswith(prefix + "unmute"):
            if len(message.mentions) == 1:
                user = message.mentions[0]

            elif len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "mute "):])
                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            else:
                await client.send_message(message.channel, "Please mention somebody to mute him/her.")
                return

            if not user:
                return

            handler.unmute(user)
            await client.send_message(message.channel, "{} has been unmuted :bell:".format(user.name))
            self.update_mutes()

        elif startswith(prefix + "purge"):
            cut = str(message.content)[len(prefix + "purge "):]

            try:
                amount = int(cut.split(" ")[0])
            except ValueError:
                return

            if len(message.mentions) >= 1:
                user = message.mentions[0]

            elif len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "purge  " + str(amount)):])
                user = discord.utils.find(lambda m: m.name == str(name), message.channel.server.members)

            else:
                await client.send_message(message.channel, "Please mention somebody to purge his/her messages.")
                return

            if not user:
                return

            def isauthor(m):
                return m.author.id == user.id

            dl = await client.purge_from(channel=message.channel, limit=amount, check=isauthor)

            msg = await client.send_message(message.channel, "Purged **{}** messages from **{}** in the last {} messages :)".format(len(dl), user.name, amount))
            await asyncio.sleep(5)
            await client.delete_message(msg)

        elif startswith(prefix + "nuke"):
            cut = str(message.content)[len(prefix + "nuke "):]

            try:
                cut = int(cut) + 1 # Includes the sender's message
            except ValueError:
                await client.send_message(message.channel, "Must be a number.")
                return

            await client.delete_message(message)

            await client.send_message(message.channel, "Purging last {} messages... :boom:".format(cut - 1))
            await client.purge_from(message.channel, limit=cut)

            m = await client.send_message(message.channel, "Purged {} messages :white_check_mark:".format(cut - 1))
            await asyncio.sleep(1.5)
            await client.delete_message(m)

        elif startswith(prefix + "dev"):
            if not is_owner:
                return

            if startswith(prefix + "dev get_all_servers"):
                ls = ["{} ({} u) - {}".format(srv.name, srv.member_count, srv.id) for srv in client.servers]
                await client.send_message(message.channel, "Servers:\n```\n{}```".format("\n".join(ls)))

            elif startswith(prefix + "dev server_info"):
                sid = str(message.content)[len(prefix + "dev server_info "):]
                srv = discord.utils.find(lambda s: s.id == sid, client.servers)

                if not srv:
                    await client.send_message(message.channel, "Error. :x:")
                    return

                nano_data = handler.get_server_data(srv.id)
                to_send = "{}\n```css\nMember count: {}\nChannels: {}\nOwner: {}```\nNano settings: ```{}```".format(srv.name, srv.member_count, ",".join([ch.name for ch in srv.channels]), srv.owner.name, nano_data)

                await client.send_message(message.channel, to_send)

            elif startswith(prefix + "dev create_logchannel"):
                await self.create_log_channel(message.channel.server, handler.get_var(message.channel.server.id, "logchannel"))

            elif startswith(prefix + "dev sm"):
                sid = str(message.content)[len(prefix + "dev sm "):]
                uid = str(int(sid[:18]))  # Check for id
                msg = sid[18 + 1:]

                reporter = discord.utils.find(lambda u: u.id == uid, client.get_all_members())
                await client.send_message(reporter, msg)

            elif startswith(prefix + "dev imdb clean"):
                idb._clean_cache()
                await client.send_message(message.channel, "Imdb cache cleaned :clapper:")

            elif startswith(prefix + "dev servers clean"):
                logger.info("Checking server data integrity")
                await client.send_message(message.channel, "Checking...")

                for server in client.servers:
                    self.server_check(server, make_thread=False)

                await client.send_message(message.channel, "Server integrity check :ok:")

            # Work in progress
            elif startswith(prefix + "dev user_info"):
                sid = str(message.content)[len(prefix + "dev server_info "):].split("|")

                srv = discord.utils.find(lambda a: a.id == sid[0], client.servers)
                usr = discord.utils.find(lambda s: s.id == sid[1], srv.members)

                await client.send_message(message.channel, "**{}**\nAvatar: {}\n".format(usr.name, usr.avatar_url))


# When a member joins the server
@client.event
async def on_member_join(member):
    if nano.debug_blocked(member.server.id):
            return

    if handler.issleeping(member.server):
        return

    msg = handler.get_var(member.server.id, "welcomemsg").replace(":user", member.mention).replace(":server", member.server.name)
    if msg is None or msg is False:
        return

    await client.send_message(member.server.default_channel, msg)

# When somebody gets banned


@client.event
async def on_member_ban(member):
    if nano.debug_blocked(member.server.id):
            return

    if handler.issleeping(member.server):
        return

    if nano.softbans.get(member.server.id):
        if (member.id in nano.softbans.get(member.server.id).keys()) and handler.haslogging(member.server):
                log_channel = discord.utils.find(lambda channel: channel.name == handler.get_var(member.server.id, "logchannel"), member.server.channels)

                msg = "**{}** has been softbanned for `{}`".format(member.name, nano.softbans[member.server.id].get(member.id))

                if log_channel:
                    await client.send_message(log_channel, msg)
                elif handler.get_var(member.server.id, "logchannel") is not None:
                    log_channel = await nano.create_log_channel(member.server, handler.get_var(member.server.id, "logchannel"))
                    await client.send_message(log_channel, msg)

    else:

        msg = handler.get_var(member.server.id, "banmsg").replace(":user", member.name)
        if msg is None or msg is False:
            return

        if handler.haslogging(member.server):
            log_channel = discord.utils.find(lambda channel: channel.name == handler.get_var(member.server.id, "logchannel"), member.server.channels)

            if log_channel:
                await client.send_message(log_channel, msg)
            elif handler.get_var(member.server.id, "logchannel") is not None:
                log_channel = await nano.create_log_channel(member.server, handler.get_var(member.server.id, "logchannel"))
                await client.send_message(log_channel, msg)


@client.event
async def on_member_remove(member):
    if nano.debug_blocked(member.server.id):
            return

    if handler.issleeping(member.server):
        return

    msg = handler.get_var(member.server.id, "leavemsg").replace(":user", member.name)
    if msg is None or msg is False:
        return

    if nano.softbans.get(member.server.id):
        if not member.id in nano.softbans[member.server.id].keys():
            return

    else:
        if handler.haslogging(member.server):
            log_channel = discord.utils.find(lambda channel: channel.name == handler.get_var(member.server.id, "logchannel"), member.server.channels)

            if log_channel:
                await client.send_message(log_channel, "**{}** left".format(member.name))
            elif handler.get_var(member.server.id, "logchannel") is not None:
                log_channel = await nano.create_log_channel(member.server, handler.get_var(member.server.id, "logchannel"))
                await client.send_message(log_channel, "**{}** left".format(member.name))


@client.event
async def on_server_join(server):
    await client.send_message(server.default_channel, "**Hi!** I'm Nano!\nNow that you have invited me to your server, you might want to set up some things."
                                                      "Right now only the server owner can use my restricted commands. But no worries, you can add admin permissions to others using `nano.admins add @mention` or by assigning them a role named **Nano Admin**!"
                                                      "\nTo get started, type `!getstarted` as the server owner. It will help you set up most of the things. After that, you might want to see `!cmds` to get familiar with my commands.")

    log("Joined server with {} members : {}".format(server.member_count, server.name))
    handler.server_setup(server)

    POSTServerCount.upload(len(client.servers))

    log("POSTed server count to bots.discord.pw : {}".format(len(client.servers)))


@client.event
async def on_server_remove(server):
    log("Removed from server: {}".format(server.name))
    stat.plusleftserver()

    nano.remove_old_servers(threaded=True)

# Events and stuff

nano = Nano(owner=parser.getint("Settings", "ownerid"), debug=parser.getboolean("Debug", "debug"))

#@client.event
#async def on_error(event, *args, **kwargs):
#    typ, value, traceback = sys.exc_info()
#
#    if typ == discord.Forbidden:
#        pass
#
#    else:
#        exc_logger(typ, value, traceback)


@client.event
async def on_ready():
    rem._update_client(nano)
    timebans._set_client(nano)
    rem.wait()

    def check_all_servers():
        for server in client.servers:
            nano.server_check(server, make_thread=False)
        logger.info("Checked server data")

    global first
    if not first:
        log("Resumed connection (on_ready event)")
        check_all_servers()
        return
    first = False

    print("done")
    print("Username: " + str(client.user.name))
    print("ID: " + str(client.user.id))

    if nano.debug:
        print("Mode: DEBUG (server: {})".format(discord.utils.get(client.servers, id=parser.get("Debug", "debugserver")).name))

    # Sets the status on startup
    name = parser.get("Settings", "initialstatus")
    roller = parser.get("Settings", "rollstatus")
    if name and roller:
        await client.change_status(game=discord.Game(name=name))

    await client.wait_until_ready()
    check_all_servers()

    nano.remove_old_servers(threaded=False)
    logger.info("Removed old servers")

    log("Started as {} with id {}".format(client.user.name, client.user.id))

    rem.wait_release()


@client.event
async def on_message(message):
    await nano.on_message(message)


async def start():
    # Will accept both forms of auth (token vs mail/pass)
    if parser.has_option("Credentials", "token"):
        token = parser.get("Credentials", "token")

        await client.login(token)
        await client.connect()

    elif parser.has_option("Credentials", "mail") and parser.has_option("Credentials", "password"):
        mail = parser.get("Credentials", "mail")
        password = parser.get("Credentials", "password")

        await client.login(mail, password)
        await client.connect()

    else:
        print("[ERROR] Credentials are missing.")
        sys.exit()

def main():
    try:
        print("Connecting...", end="")

        # Playing status changer (1800 - twice an hour)
        roll = parser.get("Settings", "rollstatus")
        if roll and not nano.debug:
            loop.create_task(playing.roll_statuses(client, time=1800))

        # Runs scheduled backups (once a day)
        backup2 = parser.get("Backup", "enable")
        if backup2:
            loop.create_task(b.run_forever())

        loop.run_until_complete(start())

    except:
        #b.backup()
        b.stop()  # Stops backups if active
        logger.warn("Exception raised, logging out")
        loop.run_until_complete(client.logout())
    finally:
        logger.warn("Closing the loop")
        loop.close()

if __name__ == '__main__':
    main()