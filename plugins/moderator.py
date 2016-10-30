# coding=utf-8
import logging
import re
from pickle import load

from data.serverhandler import ServerHandler
from discord import Message, Client

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


class NanoModerator:
    def __init__(self):
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

        result = bool(self._detect_gib(message))  # Currently uses only the gibberish detector since the other one does not have much (or enough) better detection of repeated chars

        return result

    def _detect_gib(self, message):
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

    @staticmethod
    def check_invite(message):
        """
        Checks for invites
        :param message: string
        :return: bool
        """
        if isinstance(message, Message):
            message = str(message.content)

        rg = re.compile(r'(http(s)?://)?discord.gg/\w+')

        res = rg.search(str(message))

        return res if res else None


class Moderator:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.checker = NanoModerator()

    async def on_message(self, message, **_):
        handler = self.handler
        client = self.client
        assert isinstance(client, Client)
        assert isinstance(handler, ServerHandler)

        # Muting
        if handler.is_muted(message.author):
            await client.delete_message(message)
            return "return"

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

            return "return"


class NanoPlugin:
    _name = "Moderator"
    _version = 0.1

    handler = Moderator
    events = {
        "on_message": 6
        # type : importance
    }
