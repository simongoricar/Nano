# coding=utf-8
import logging
import re
from enum import IntEnum
from pickle import load

from discord import Message, Embed, TextChannel

from core.stats import SUPPRESS
from core.utils import add_dots, get_valid_commands
from core.confparser import PLUGINS_DIR

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


class SpamType(IntEnum):
    REPEATED = 1
    GIBBERISH = 2
    CAPS = 3
    MENTIONS = 4


class ModBucket:
    """
    A Bucket item: maintains a history of booleans. If "limit" is reached, notice(...) returns True
    """
    __slots__ = ("threshold", "max_history", "history", "position")

    def __init__(self, limit: int=2, history: int=3):
        self.threshold = limit
        self.max_history = history

        self.history = [False] * history
        self.position = 0

    def next_position(self) -> int:
        if self.position >= self.max_history-1:
            self.position = 0
            return 0
        else:
            self.position += 1
            return self.position

    def threshold_reached(self) -> bool:
        return self.history.count(True) >= self.threshold


    def notice(self, is_offense=False) -> bool:
        pos = self.next_position()

        self.history[pos] = is_offense

        if self.threshold_reached():
            # Reset history and return True
            self.history = [False] * self.max_history
            return True


class GibberishDetector:
    """
    Detects "gibberish" (e.g. asdasdhadasda). Uses statistical occurences of two characters one after another.
    """
    __slots__ = ("data", "threshold", "char_positions", "chars2", "pos2")

    def __init__(self):
        # Gibberish detector
        with open("{}/spam_model.pki".format(PLUGINS_DIR), "rb") as spam_model:
            spam_model = load(spam_model)

        self.data = spam_model["data"]
        self.threshold = spam_model["threshold"]
        self.char_positions = spam_model["positions"]

        # Entropy calculator
        self.chars2 = "abcdefghijklmnopqrstuvwxyz,.-!?_;:|1234567890*=)(/&%$#\"~<> "
        self.pos2 = dict([(c, index) for index, c in enumerate(self.chars2)])


    def is_gibberish(self, message: str):
        """
        Method: spam_model.pki is a pickle file with statistical occurrences of two characters one after another.

        :param message: string
        :return bool
        """
        if not message:
            return

        th = len(message) / 1.8
        c = float(0)
        for ca, cb in two_chars(message):

            if self.data[self.char_positions[ca]][self.char_positions[cb]] < self.threshold[self.char_positions[ca]]:
                c += 1

        return bool(c >= th)


class SwearingDetector:
    """
    Detects blocked words from banned_words.txt. Makes some "permutations" to all words so detection quality is higher.
    """
    __slots__ = ("permutations", "word_list")

    def __init__(self):
        self.permutations = [
            dict(a="4"),
            dict(s="$"),
            dict(o="0"),
            dict(a="@"),
        ]

        with open("{}/banned_words.txt".format(PLUGINS_DIR)) as banned:
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

    def has_swearing(self, message: str) -> bool:
        """
        Returns True if there is a banned word

        :param message: Discord Message content
        """
        res = [a for a in self.word_list if a in message.split(" ")]
        return bool(res)


class RepeatingMessageDetector:
    __slots__ = ("user_buckets", "last_from_user")

    def __init__(self):
        self.last_from_user = {}
        self.user_buckets = {}

    def is_repeating(self, user_id: int, message: str):
        # Get bucket
        bucket = self.user_buckets.get(user_id)
        if not bucket:
            bucket = ModBucket()
            self.user_buckets[user_id] = bucket

        # See if message repeats
        last = self.last_from_user.get(user_id)

        self.last_from_user[user_id] = message
        # If first message
        if not last:
            return False

        return bucket.notice(message == last)



class NanoModerator:
    def __init__(self):
        self.gib_detect = GibberishDetector()
        self.swearing_detect = SwearingDetector()
        self.repeating_detect = RepeatingMessageDetector()

        self.invite_regex = re.compile(r'(http(s)?://)?discord.gg/\w+')


    def check_swearing(self, message: str) -> bool:
        """
        Checks whether a message includes words that are not allowed.

        :param message: str
        :return: bool
        """
        return self.swearing_detect.has_swearing(message.lower())


    def check_spam(self, author_id: int, message: str, raw_message):
        """
        Does a set of checks to know whether something is spam or not.

        :param author_id: int
        :param message: str
        :return: bool
        """
        # NOTE: If any of the detectors returns a positive result, the message is deleted

        #########
        # Repeating sentence detection
        #########

        is_repeating = self.repeating_detect.is_repeating(author_id, message)
        if is_repeating is True:
            return SpamType.REPEATED


        #########
        # Usage of caps
        #########
        caps_threshold = len(message) * 0.45

        up_count = sum([1 for c in message if c.isupper()])
        if len(message) > 5 and up_count > caps_threshold:
            return SpamType.CAPS


        #########
        # Mention spam
        #########
        mention_limit = 5
        if sum([len(raw_message.mentions), len(raw_message.role_mentions)]) > mention_limit:
            return SpamType.MENTIONS


        #########
        # Gibberish detection
        #########

        # Should exclude links
        message = " ".join([word for word in message.split(" ") if
                            (not word.startswith("https://")) and (not word.startswith("http://"))])

        # Should always ignore short sentences
        if len(message) < 10:
            return False

        if self.gib_detect.is_gibberish(message):
            return SpamType.GIBBERISH

        return False

    def check_invite(self, message: str) -> bool:
        """
        Matches a string against an invite regex
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

    async def resolve_plugin(self):
        self.getter = self.nano.get_plugin("server").instance

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

        self.valid_commands = set()

    async def on_plugins_loaded(self):
        # Collect all valid commands
        plugins = [a.plugin for a in self.nano.plugins.values() if a.plugin]

        temp = []
        for pl in plugins:
            commands = get_valid_commands(pl)
            if commands is not None:
                # Joins two lists
                temp += commands

        self.valid_commands = set(temp)

        await self.log.resolve_plugin()

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
        if message.content.startswith(prefix):
            np_text = message.content[len(prefix):]
        else:
            np_text = message.content

        np_text = "_" + np_text.split(" ", maxsplit=1)[0]
        if np_text in self.valid_commands:
            return

        # Spam, swearing and invite filter
        needs_spam_filter = handler.has_spam_filter(message.guild)
        needs_swearing_filter = handler.has_word_filter(message.guild)
        needs_invite_filter = handler.has_invite_filter(message.guild)

        if needs_spam_filter:
            spam_reason = self.checker.check_spam(message.author.id, message.content, message)
        else:
            spam_reason = False

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
        if any([spam_reason, swearing, invite]):
            await message.delete()
            logger.debug("Message filtered")

            # Check if current channel is the logging channel
            log_channel_name = self.handler.get_log_channel(message.guild)
            if log_channel_name == message.channel.name:
                return

            # Make correct messages
            if spam_reason:
                if spam_reason == SpamType.GIBBERISH:
                    await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SPAM_G", lang))
                elif spam_reason == SpamType.CAPS:
                    await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SPAM_C", lang))
                elif spam_reason == SpamType.REPEATED:
                    await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SPAM_R", lang))
                elif spam_reason == SpamType.MENTIONS:
                    await self.log.send_log(message, lang, self.trans.get("MSG_MOD_SPAM_M", lang))

                else:
                    raise NotImplementedError("This offense type is not implemented.")

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
