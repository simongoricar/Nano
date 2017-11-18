# coding=utf-8
import logging
import time

from discord import TextChannel

from data.stats import SLEPT
from data.confparser import get_config_parser
from data.utils import get_valid_commands

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = get_config_parser()

DEFAULT_PREFIX = parser.get("Servers", "defaultprefix")

# Prefix getter plugin

commands = {
    "nano.sleep": {"desc": "Puts Nano to sleep. (per-server basis)"},
    "nano.wake": {"desc": "Wakes Nano up. (per-server basis)"},
}

valid_commands = commands.keys()


class Bucket:
    __slots__ = ("last_cooldown", "_size", "_cooldown", "current_bucket", "was_warned")

    def __init__(self, limit: int=2, per: int=5):
        self.last_cooldown = time.time()

        self._size = limit
        self._cooldown = per
        self.was_warned = False
        self.current_bucket = 0

    def action(self):
        current_time = time.time()

        # If bucket cooldown is reached, reset the bucket
        if current_time - self.last_cooldown > self._cooldown:
            self.last_cooldown = current_time
            self.current_bucket = 0
            self.was_warned = False
            return True

        if self.current_bucket >= self._size:
            return False
        else:
            self.current_bucket += 1
            return True



class Observer:
    def __init__(self, *_, **kwargs):
        self.client = kwargs.get("client")
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")
        self.nano = kwargs.get("nano")

        self.buckets = {}
        self.valid_commands = set()

    async def on_plugins_loaded(self):
        # Collect all valid commands
        plugins = [a.get("plugin") for a in self.nano.plugins.values() if a.get("plugin")]

        temp = []
        for pl in plugins:
            cmds = get_valid_commands(pl)
            if cmds is not None:
                # Joins two lists
                temp += cmds

        self.valid_commands = set(temp)

    async def on_message(self, message, **_):
        trans = self.trans

        # Ignore your own messages
        if message.author == self.client.user:
            return "return"
        # Ignore private messages
        if not isinstance(message.channel, TextChannel):
            return "return"
        # Ignore bot messages
        if message.author.bot:
            return "return"

        # Add prefix to kwargs for future plugins
        pref = self.handler.get_prefix(message.guild)
        if pref is None:
            pref = str(DEFAULT_PREFIX)
        else:
            pref = pref

        # Parse language
        lang = self.handler.get_lang(message.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        # Ignore the filter if user is not executing a command
        np_text = "_" + message.content.lstrip(pref).split(" ")[0]
        if np_text in self.valid_commands:
            # Check rate-limits
            # If user was silent until now, create a new bucket
            if message.author.id not in self.buckets.keys():
                b = Bucket()
                b.action()
                self.buckets[message.author.id] = b
            # Otherwise, check bucket size
            else:
                bucket = self.buckets[message.author.id]
                if not bucket.action():
                    if not bucket.was_warned:
                        # Do not send additional warnings in the same time period
                        bucket.was_warned = True
                        await message.channel.send(trans.get("MSG_RATELIMIT", lang))

                    return "return"


        # Set up the server if it is not present in redis db
        self.handler.auto_setup_server(message.guild)

        # Ah, the shortcuts
        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # SLEEP/WAKE Commands!
        # nano.sleep
        if startswith("nano.sleep"):
            if not self.handler.is_admin(message.author, message.guild):
                await message.channel.send(trans.get("PERM_ADMIN", lang))
                return "return"

            self.handler.set_sleeping(message.guild, True)
            await message.channel.send(self.trans.get("MSG_NANO_SLEEP", lang))
            return "return"

        # nano.wake
        elif startswith("nano.wake"):
            if not self.handler.is_admin(message.author, message.guild):
                await message.channel.send(trans.get("PERM_ADMIN", lang))
                return "return"

            if not self.handler.is_sleeping(message.guild.id):
                await message.channel.send(trans.get("MSG_NANO_WASNT_SLEEPING", lang))
                return "return"

            self.handler.set_sleeping(message.guild, False)
            await message.channel.send(self.trans.get("MSG_NANO_WAKE", lang))

            self.stats.add(SLEPT)
            return "return"

        # Quit if the bot is sleeping
        if self.handler.is_sleeping(message.guild.id):
            return "return"

        return "add_var", dict(prefix=pref, lang=lang)

    async def on_member_join(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.guild.id):
            return "return"

        lang = self.handler.get_lang(member.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return "add_var", dict(lang=lang)

    async def on_member_ban(self, guild, _, **__):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(guild.id):
            return "return"

        lang = self.handler.get_lang(guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return "add_var", dict(lang=lang)

    async def on_member_remove(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.guild.id):
            return "return"

        lang = self.handler.get_lang(member.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return "add_var", dict(lang=lang)

    async def on_guild_join(self, _, **__):
        lang = str(self.trans.default_lang)

        return "add_var", dict(lang=lang)

    async def on_reaction_add(self, reaction, user, **__):
        # Ignore private messages
        if not isinstance(reaction.message.channel, TextChannel):
            return "return"

        lang = self.handler.get_lang(user.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return "add_var", dict(lang=lang)




class NanoPlugin:
    name = "Prefix and state handler"
    version = "23"

    handler = Observer
    events = {
        "on_message": 4,
        "on_plugins_loaded": 4,
        "on_member_join": 5,
        "on_member_ban": 5,
        "on_member_remove": 5,
        "on_reaction_add": 5,
        "on_guild_join": 5,
        # type : importance
    }
