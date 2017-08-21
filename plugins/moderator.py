# coding=utf-8
import logging
import re
from pickle import load

from discord import Message, Embed, TextChannel

from data.stats import SUPPRESS
from data.utils import add_dots

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
            return list(plugin.commands.keys())
        except AttributeError:
            return None


class NanoModerator:
    def __init__(self):
        self.permutations = [
            dict(a="4"),
            dict(s="$"),
            dict(o="0"),
            dict(a="@"),
        ]

        with open("plugins/banned_words.txt") as banned:
            self.word_list = [line.strip("\n") for line in banned.readlines()]

        # Builds a more sophisticated list
        before = len(self.word_list)
        for word in self.word_list:
            initial = str(word)

            for perm in self.permutations:
                (k, v), = perm.items()
                changed = initial.replace(k, v)
                if initial != changed:
                    self.word_list.append(changed)

        logger.info("Processed word list: added {} entries ({} total)".format(len(self.word_list) - before, len(self.word_list)))


        # Gibberish detector
        with open("plugins/spam_model.pki", "rb") as spam_model:
            self.spam_model = load(spam_model)

        self.data = self.spam_model["data"]
        self.threshold = self.spam_model["threshold"]
        self.char_positions = self.spam_model["positions"]

        # Entropy calculator
        self.chars2 = "abcdefghijklmnopqrstuvwxyz,.-!?_;:|1234567890*=)(/&%$#\"~<> "
        self.pos2 = dict([(c, index) for index, c in enumerate(self.chars2)])

        self.invite_regex = re.compile(r'(http(s)?://)?discord.gg/\w+')

    def check_swearing(self, message: str) -> bool:
        """Returns True if there is a banned word
        :param message: Discord Message content
        """
        message = message.lower()

        # Massive speed improvement in 0.3
        res = [a for a in self.word_list if a in message]
        return bool(res)

    def check_spam(self, message: str) -> bool:
        """
        Does a set of checks.
        :param message: string to check
        :return: bool
        """
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
                    return True

        return False

    def check_invite(self, message: str) -> bool:
        """
        Checks for invites
        :param message: string
        :return: bool
        """
        res = self.invite_regex.search(message)

        return bool(res) if res else False


class LogManager:
    def __init__(self, client, nano, loop, handler, trans):
        self.client = client
        self.nano = nano
        self.loop = loop
        self.handler = handler
        self.trans = trans

        self.getter = None
        self.running = True

    async def get_plugin(self):
        self.getter = self.nano.get_plugin("server").get("instance")

    async def send_log(self, message: Message, lang, reason=""):
        if not self.getter:
            self.loop.call_later(5, self.send_log(message, lang, reason))
            logger.warning("Getter is not set, calling in 5 seconds...")
            return

        log_channel = await self.getter.handle_log_channel(message.guild)

        if not log_channel:
            return

        author = message.author

        embed_title = self.trans.get("MSG_MOD_MSG_DELETED", lang).format(reason)

        embed = Embed(title=embed_title, description=add_dots(message.content))
        embed.set_author(name="{} ({})".format(author.name, author.id), icon_url=author.avatar_url)
        embed.add_field(name=self.trans.get("INFO_CHANNEL", lang), value=message.channel.mention)

        logger.debug("Sending logs for {}".format(message.guild.name))
        await log_channel.send(embed=embed)


class Moderator:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.checker = NanoModerator()
        self.log = LogManager(self.client, self.nano, self.loop, self.handler, self.trans)

        self.valid_commands = []

    async def on_plugins_loaded(self):
        # Collect all valid commands
        plugins = [a.get("plugin") for a in self.nano.plugins.values() if a.get("plugin")]

        for pl in plugins:
            commands = get_valid_commands(pl)
            if commands is not None:
                # Joins two lists
                self.valid_commands += commands

        await self.log.get_plugin()

    async def on_message(self, message, **kwargs):
        handler = self.handler

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        if not isinstance(message.channel, TextChannel):
            return "return"

        # Muting
        if handler.is_muted(message.guild, message.author.id):
            await message.delete()

            self.stats.add(SUPPRESS)
            return "return"

        # Channel blacklisting
        if handler.is_blacklisted(message.guild.id, message.channel.id):
            return "return"

        # Ignore the filter if user is executing a command
        prless_command = message.content.replace(prefix, "_").split(" ")[0]
        if prless_command in self.valid_commands:
            return

        # Spam, swearing and invite filter
        needs_spam_filter = handler.has_spam_filter(message.guild)
        needs_swearing_filter = handler.has_word_filter(message.guild)
        needs_invite_filter = handler.has_invite_filter(message.guild)

        if needs_spam_filter:
            spam = self.checker.check_spam(message.content)
        else:
            spam = False

        if needs_swearing_filter:
            swearing = self.checker.check_swearing(message.content)
        else:
            swearing = False

        if needs_invite_filter:
            # Ignore invites from admins
            if not handler.is_admin(message.author, message.guild):
                invite = self.checker.check_invite(message.content)

            else:
                invite = False

        else:
            invite = False


        # Delete if necessary
        if any([spam, swearing, invite]):
            await message.delete()
            logger.debug("Message filtered")

            # Check if current channel is the logging channel
            log_channel_name = self.handler.get_log_channel(message.guild)
            if log_channel_name == message.channel.name:
                return

            # Make correct messages
            if spam:
                await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SPAM", lang))

            elif swearing:
                await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SWEARING", lang))

            elif invite:
                await self.log.send_log(message, lang, self.trans.get("MSG_MOD_INVITE", lang))

            else:
                # Lol wat
                return

            return "return"


class NanoPlugin:
    name = "Moderator"
    version = "31"

    handler = Moderator
    events = {
        "on_plugins_loaded": 5,
        "on_message": 6
        # type : importance
    }
