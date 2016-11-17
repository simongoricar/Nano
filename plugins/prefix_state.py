# coding=utf-8
import logging
import configparser
from discord import Message
from data.serverhandler import ServerHandler
from data.stats import SLEPT


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

# Prefix getter plugin


class PrefixState:
    def __init__(self, *_, **kwargs):
        self.client = kwargs.get("client")
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")

    async def on_message(self, message, **_):
        assert isinstance(self.handler, ServerHandler)
        assert isinstance(message, Message)

        # Ignore your own messages
        if message.author == self.client.user:
            return "return"

        if message.channel.is_private:
            return "add_var", parser.get("Servers", "defaultprefix")


        # Set up the server if it is not present in servers.yml
        if not self.handler.server_exists(message.server):
            self.handler.server_setup(message.server)


        # Ah, the shortcuts
        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # SLEEP/WAKE Commands!
        # nano.sleep
        if startswith("nano.sleep"):
            if not self.handler.is_bot_owner(message.author.id):
                return

            self.handler.set_sleep_state(message.server, 1)
            await self.client.send_message(message.channel, "G'night! :sleeping:")

        # nano.wake
        elif startswith("nano.wake"):
            if not self.handler.is_bot_owner(message.author.id):
                return

            self.handler.set_sleep_state(message.server, 0)
            await self.client.send_message(message.channel, ":wave:")

            self.stats.add(SLEPT)


        # Quit if the bot is sleeping
        if self.handler.is_sleeping(message.server):
            return "return"


        # Add prefix to kwargs for future plugins
        pref = self.handler.get_prefix(message.channel.server)
        return "add_var", dict(prefix=pref)

    async def on_member_join(self, member, **kwargs):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

    async def on_member_ban(self, member, **kwargs):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"

    async def on_member_remove(self, member, **kwargs):
        # Quit if the bot is sleeping
        if self.handler.is_sleeping(member.server):
            return "return"


class NanoPlugin:
    _name = "Prefix and state handler"
    _version = 0.1

    handler = PrefixState
    events = {
        "on_message": 5,
        "on_member_join": 5,
        "on_member_ban": 5,
        "on_member_remove": 5,
        # type : importance
    }
