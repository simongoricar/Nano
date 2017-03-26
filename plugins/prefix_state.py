# coding=utf-8
import logging
import configparser
from discord import Message
from data.serverhandler import RedisServerHandler, LegacyServerHandler
from data.utils import StandardEmoji
from data.stats import SLEPT


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

DEFAULT_PREFIX = parser.get("Servers", "defaultprefix")

# Prefix getter plugin

common_bots = [
    159985870458322944,  # Mee6
    150300454708838401,  # Aethex
    116275390695079945,  # Nadeko
    195244363339530240,  # KawaiiBot
    172002275412279296,  # Tatsumaki
]

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

    async def on_message(self, message, **_):
        assert isinstance(self.handler, (LegacyServerHandler, RedisServerHandler))
        assert isinstance(message, Message)

        # Ignore your own messages
        if message.author == self.client.user:
            return "return"

        if message.channel.is_private:
            return "return"
            # return "add_var", parser.get("Servers", "defaultprefix")

        if message.author.id in common_bots:
            # Ignore commands from common bots
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

        # SLEEP/WAKE Commands!
        # nano.sleep
        if startswith("nano.sleep"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                return

            self.handler.set_sleeping(message.server, 1)
            await self.client.send_message(message.channel, "G'night! " + StandardEmoji.SLEEP)

        # nano.wake
        elif startswith("nano.wake"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                return

            self.handler.set_sleeping(message.server, 0)
            await self.client.send_message(message.channel, ":wave:")

            self.stats.add(SLEPT)

        # Quit if the bot is sleeping
        if self.handler.is_sleeping(message.server):
            return "return"

        # Add prefix to kwargs for future plugins
        pref = self.handler.get_prefix(message.channel.server)
        if pref is None:
            pref = DEFAULT_PREFIX

        return "add_var", dict(prefix=pref)

    async def on_member_join(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

    async def on_member_ban(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

    async def on_member_remove(self, member, **_):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"


class NanoPlugin:
    name = "Prefix and state handler"
    version = "0.1.1"

    handler = PrefixState
    events = {
        "on_message": 4,
        "on_member_join": 5,
        "on_member_ban": 5,
        "on_member_remove": 5,
        # type : importance
    }
