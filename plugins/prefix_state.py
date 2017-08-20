# coding=utf-8
import configparser
import logging

from discord import TextChannel

from data.stats import SLEPT

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

DEFAULT_PREFIX = parser.get("Servers", "defaultprefix")

# Prefix getter plugin

commands = {
    "nano.sleep": {"desc": "Puts Nano to sleep. (per-server basis)", "use": None, "alias": None},
    "nano.wake": {"desc": "Wakes Nano up. (per-server basis)", "use": None, "alias": None},
}

valid_commands = commands.keys()


class PrefixState:
    def __init__(self, *_, **kwargs):
        self.client = kwargs.get("client")
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

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

        # Set up the server if it is not present in redis db
        if not self.handler.server_exists(message.guild.id):
            self.handler.server_setup(message.guild)

        # Ah, the shortcuts
        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # Add prefix to kwargs for future plugins
        pref = self.handler.get_prefix(message.guild)
        if pref is None:
            pref = str(DEFAULT_PREFIX)

        # Parse language
        lang = self.handler.get_lang(message.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        # SLEEP/WAKE Commands!
        # nano.sleep
        if startswith("nano.sleep"):
            if not self.handler.can_use_admin_commands(message.author, message.guild):
                await message.channel.send(trans.get("PERM_ADMIN", lang))
                return "return"

            self.handler.set_sleeping(message.guild, True)
            await message.channel.send(self.trans.get("MSG_NANO_SLEEP", lang))
            return "return"

        # nano.wake
        elif startswith("nano.wake"):
            if not self.handler.can_use_admin_commands(message.author, message.guild):
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

        return [("add_var", dict(lang=lang))]

    async def on_member_ban(self, guild, _, **__):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(guild.id):
            return "return"

        lang = self.handler.get_lang(guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_member_remove(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.guild.id):
            return "return"

        lang = self.handler.get_lang(member.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_guild_join(self, _, **__):
        lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_reaction_add(self, reaction, user, **__):
        # Ignore private messages
        if not isinstance(reaction.message.channel, TextChannel):
            return "return"

        lang = self.handler.get_lang(user.guild.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]




class NanoPlugin:
    name = "Prefix and state handler"
    version = "22"

    handler = PrefixState
    events = {
        "on_message": 4,
        "on_member_join": 5,
        "on_member_ban": 5,
        "on_member_remove": 5,
        "on_reaction_add": 5,
        "on_guild_join": 5,
        # type : importance
    }
