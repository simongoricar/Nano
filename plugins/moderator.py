# coding=utf-8
import logging
import re
import asyncio
from pickle import load
from discord import Message, Client, Server, utils
from data.serverhandler import ServerHandler
from data.stats import SUPPRESS

#from .admin import valid_commands as admin_valid
#from .commons import valid_commands as commons_valid
#from .developer import valid_commands as dev_valid
#from .fun import valid_commands as fun_valid
#from .help import valid_commands as help_valid
#from .imdb import valid_commands as imdb_valid
#from .minecraft import valid_commands as 


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# CONSTANTS

accepted_chars = "abcdefghijklmnopqrstuvwxyz "


def normalize(line):
    # Ignores punctuation, new lines, etc...
    accepted = "".join([char for char in line if char in accepted_chars])

    return accepted


def two_chars(line):
    # Normalizes
    norm = normalize(line)
    # Yields two by two
    for rn in range(0, len(norm) - 1):
        yield norm[rn:rn + 1], norm[rn + 1:rn + 2]

def get_valid_commands(plugin):
        try:
            return plugin.valid_commands
        except AttributeError:
            return None

class NanoModerator:
    def __init__(self):

        # Other
        with open("plugins/banned_words.txt", "r") as file:
            self.word_list = [line.strip("\n") for line in file.readlines()]

        # Gibberish detector
        self.spam_model = load(open("plugins/spam_model.pki", "rb"))

        self.data = self.spam_model["data"]
        self.threshold = self.spam_model["threshold"]
        self.char_positions = self.spam_model["positions"]

        # Entropy calculator
        self.chars2 = "abcdefghijklmnopqrstuvwxyz,.-!?_;:|1234567890*=)(/&%$#\"~<> "
        self.pos2 = dict([(c, index) for index, c in enumerate(self.chars2)])

        self.invite_regex = re.compile(r'(http(s)?://)?discord.gg/\w+')

    def check_swearing(self, message):
        """Returns True if there is a banned word
        :param message: Discord Message content
        """
        if isinstance(message, Message):
            message = str(message.content)

        # Builds a list
        message = str(message).lower().split(" ")

        # Checks for matches
        # Each word is compared to each banned word
        for a_word in message:
            for b_word in self.word_list:

                if a_word.find(b_word) != -1:
                    return True

        return False

    def check_spam(self, message):
        """
        Does a set of checks.
        :param message: string to check
        :return: bool
        """
        if isinstance(message, Message):
            message = str(message.content)

        # 1. Should exclude links
        message = " ".join([word for word in message.split(" ") if
                            (not word.startswith("https://")) and (not word.startswith("http://"))])

        # 2. Should always ignore short sentences
        if len(message) < 10:
            return False

        result = self.detect_gib(message)
        # Currently uses only the gibberish detector since the other one
        # does not have a good detection of repeated chars

        return result

    def detect_gib(self, message):
        """Returns True if spam is found
        :param message: string
        """
        if not message:
            return

        th = len(message) / 2.4
        c = float(0)
        for ca, cb in two_chars(message):

            if self.data[self.char_positions[ca]][self.char_positions[cb]] < self.threshold[self.char_positions[ca]]:
                c += 1

        return bool(c >= th)

    def _detect_spam(self, message):
        """
        String entropy calculator.
        :param message: string
        :return: bool
        """

        counts = [[0 for _ in range(len(self.chars2))] for _ in range(len(self.chars2))]

        for o, t in two_chars(message):
            counts[self.pos2[o]][self.pos2[t]] += 1

        thr = 0
        for this in counts:
            for another in this:
                thr += another

        thr /= 3.5

        for this in counts:
            for another in this:
                if another > thr:
                    print("Threshold {}, got {}".format(thr, another))
                    return True

        return False

    def check_invite(self, message):
        """
        Checks for invites
        :param message: string
        :return: bool
        """
        if isinstance(message, Message):
            message = str(message.content)

        res = self.invite_regex.search(str(message))

        return res if res else None


class LogManager:
    def __init__(self, client, loop, handler):
        self.client = client
        self.loop = loop
        self.handler = handler

        self.running = True

        self.logs = {}
        self.servers = {}

    def add_entry(self, server, message):
        if not isinstance(server, Server):
            return False

        self.servers[server.id] = server

        # Create a new list if one does not exist
        if not self.logs.get(server.id):
            self.logs[server.id] = [message]

        else:
            self.logs[server.id].append(message)

    async def send_combined(self, channel, message):
        await self.client.send_message(channel, message)

    async def send_logs(self):
        # /todo/ think about this shit first
        for server_id, logs in self.logs.items():

            log_channel_name = self.handler.get_log_channel(self.servers.get(server_id))
            log_channel = utils.find(lambda m: m.name == log_channel_name, self.servers.get(server_id).channels)

            # Keep in this iteration until all messages have been taken care of
            while logs:

                batch = []
                for log in list(logs):
                    # Keep adding to the batch until messages total 1000 characters
                    if sum([len(l) for l in batch]) < 1000:
                        batch.append(log)
                        logs.remove(log)

                    else:
                        break
                print("Sending logs for {}".format(self.servers.get(server_id)))
                await self.send_combined(log_channel, "\n".join(batch))


    async def start(self):
        while self.running:
            await asyncio.sleep(60)

            await self.send_logs()


class Moderator:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.checker = NanoModerator()
        self.log = LogManager(self.client, self.loop, self.handler)

        self.loop.create_task(self.log.start())

    async def on_message(self, message, **kwargs):
        handler = self.handler
        client = self.client
        prefix = kwargs.get("prefix")
        assert isinstance(client, Client)
        assert isinstance(handler, ServerHandler)

        # Muting
        if handler.is_muted(message.author):
            await client.delete_message(message)

            self.stats.add(SUPPRESS)
            return "return"

        # Ignore existing commands
        plugins = [a.get("plugin") for a in self.nano.plugins.values() if a.get("plugin")]
        valid_commands = [item for sub in [get_valid_commands(b) for b in plugins if get_valid_commands(b)] for item in sub]

        def is_command(msg, valids):
            for a in valids:
                if str(msg).startswith(a.replace("_", prefix)):
                    return True

            return False

        # Ignore the filter if user is executing a command
        if is_command(message.content, valid_commands):
            return

        # Spam, swearing and invite filter
        needs_spam_filter = handler.has_spam_filter(message.channel.server)
        needs_swearing_filter = handler.has_word_filter(message.channel.server)
        needs_invite_filter = handler.has_invite_filter(message.channel.server)

        if needs_spam_filter:
            spam = self.checker.check_spam(message)
        else:
            spam = False

        if needs_swearing_filter:
            swearing = self.checker.check_swearing(message)
        else:
            swearing = False

        if needs_invite_filter:

            if not handler.can_use_restricted_commands(message.author, message.channel.server):
                invite = self.checker.check_invite(message)

            else:
                invite = False

        else:
            invite = False

        # Delete if necessary
        if any([spam, swearing, invite]):
            await client.delete_message(message)
            logger.debug("Deleting message, sending return message.")

            # Check if current channel is the logging channel
            log_channel_name = self.handler.get_log_channel(message.server)
            if log_channel_name == message.channel.name:
                return

            # Make correct messages
            if spam:
                msg = "{}'s message was deleted: spam\n```{}```\n".format(message.author.name, message.content)

            elif swearing:
                msg = "{}'s message was deleted: banned words\n```{}```\n".format(message.author.name, message.content)

            elif invite:
                msg = "{}'s message was deleted: invite link\n```{}```\n".format(message.author.name, message.content)

            else:  pass # Lolwat

            # Add them to the queue
            self.log.add_entry(message.server, msg)

            return "return"


class NanoPlugin:
    _name = "Moderator"
    _version = "0.2.2"

    handler = Moderator
    events = {
        "on_message": 6
        # type : importance
    }
