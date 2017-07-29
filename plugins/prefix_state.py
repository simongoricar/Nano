# coding=utf-8
import configparser
import logging

from discord import Message, Member

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
        assert isinstance(message, Message)


        # Ignore your own messages
        if message.author == self.client.user:
            return "return"

        if message.channel.is_private:
            return "return"

        if message.author.bot:
            # Ignore commands from bots
            return "return"

        # Set up the server if it is not present in servers.yml
        if not self.handler.server_exists(message.server.id):
            self.handler.server_setup(message.server, wait=True)

        # Ah, the shortcuts
        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # Add prefix to kwargs for future plugins
        pref = self.handler.get_prefix(message.server)
        if pref is None:
            pref = str(DEFAULT_PREFIX)

        lang = self.handler.get_lang(message.server.id)
        if not lang:
            lang = str(self.trans.default_lang)

        # SLEEP/WAKE Commands!
        # nano.sleep
        if startswith("nano.sleep"):
            if not self.handler.can_use_admin_commands(message.author, message.server):
                return

            self.handler.set_sleeping(message.server, 1)
            await self.client.send_message(message.channel, self.trans.get("MSG_NANO_SLEEP", lang))
            return "return"

        # nano.wake
        elif startswith("nano.wake"):
            if not self.handler.can_use_admin_commands(message.author, message.server):
                return

            self.handler.set_sleeping(message.server, 0)
            await self.client.send_message(message.channel, self.trans.get("MSG_NANO_WAKE", lang))

            self.stats.add(SLEPT)
            return "return"

        # Quit if the bot is sleeping
        if self.handler.is_sleeping(message.server):
            return "return"

        if not isinstance(message.author, Member):
            user = message.server.get_member(message.author.id)

            if user:
                # Sometimes monkeypatching is needed
                message.author = user
                return [("add_var", dict(prefix=pref, lang=lang)),
                        ("set_arg", {0: message})]

        return "add_var", dict(prefix=pref, lang=lang)

    async def on_member_join(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

        lang = self.handler.get_lang(member.server.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_member_ban(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

        lang = self.handler.get_lang(member.server.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_member_remove(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

        lang = self.handler.get_lang(member.server.id)
        if not lang:
            lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_server_join(self, _, **__):
        lang = str(self.trans.default_lang)

        return [("add_var", dict(lang=lang))]

    async def on_reaction_add(self, _, user, **__):
        try:
            lang = self.handler.get_lang(user.server.id)
            if not lang:
                lang = str(self.trans.default_lang)

            return [("add_var", dict(lang=lang))]
        except AttributeError:
            pass




class NanoPlugin:
    name = "Prefix and state handler"
    version = "0.1.2"

    handler = PrefixState
    events = {
        "on_message": 4,
        "on_member_join": 5,
        "on_member_ban": 5,
        "on_member_remove": 5,
        "on_reaction_add": 5,
        "on_server_join": 5,
        # type : importance
    }
