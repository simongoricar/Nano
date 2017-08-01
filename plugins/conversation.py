# coding=utf-8
import time
import logging
from random import randint
from fuzzywuzzy import fuzz, process

from discord import Message

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

strings_to_split = [
    "conv_q_sleep",
    "conv_mood_list",
    "conv_q_how",
    "conv_q_hello",
    "conv_q_ayy",
    "conv_q_rip",
    "conv_q_master",
    "conv_q_maker"

]


class Conversation:
    def __init__(self, *_, **kwargs):
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.trans = kwargs.get("trans")
        self.loop = kwargs.get("loop")

        self.lists = {}

        # Parse all language stuff
        self.loop.create_task(self._parse_languages())


    async def _parse_languages(self):
        """
        Caches random answers so they don't have to be split every time
        """
        langs = {l : self.trans.translations[l] for l in self.trans.meta.keys()}

        for lang, trans_list in langs.items():
            self.lists[lang] = {}

            for name in strings_to_split:
                if name in trans_list.keys():
                    self.lists[lang][name] = [a.strip(" ") for a in trans_list.get(name).split("|")]

    def _safe_get(self, lang, lst):
        return self.lists[lang].get(lst) or []

    @staticmethod
    def matches(query, *possibilities):
        if not possibilities:
            return False

        highest, score = process.extractOne(query, possibilities, scorer=fuzz.token_set_ratio)

        if score > 80:
            return True
        else:
            return False

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        client = self.client
        prefix = kwargs.get("prefix")

        trans = self.trans
        lang = kwargs.get("lang")

        if self.client.user not in message.mentions:
            return

        def has(*args):
            for arg in args:
                if arg in message.content.lower():
                    return True

            return False

        async def reply(msg: str):
            await client.send_message(message.channel, msg)

        extracted = message.content.replace("<@{}>".format(self.client.user.id), "").strip(" ")

        # RESPONSES

        # If it is just a raw mention, send the help message
        if extracted == "":
            await client.send_message(message.channel, trans.get("MSG_HELP", lang).replace("_", prefix))

        elif has(trans.get("INFO_PREFIX_LITERAL", lang)):
            await client.send_message(message.channel, trans.get("INFO_PREFIX", lang).format(prefix))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_how")):
            lst = self.lists[lang].get("conv_mood_list")

            # Choose random reply
            rn = randint(0, len(lst) - 1)

            await reply(str(lst[rn]))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_snow")):
            await reply(trans.get("CONV_SNOW", lang))

        elif has(trans.get("CONV_Q_DIE", lang)):
            await reply(trans.get("CONV_NAH", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_sleep")):
            await reply(trans.get("CONV_NOPE", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_ayy")):
            await reply(trans.get("CONV_AYYLMAO", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_rip")):
            await reply(trans.get("CONV_RIP", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_master")):
            await reply(trans.get("CONV_MASTER", lang))

        elif has(trans.get("CONV_Q_WHAT", lang)):
            await reply(trans.get("CONV_SPARTA", lang))

        elif self.matches(extracted, trans.get("INFO_HELP", lang)):
            await reply(trans.get("MSG_HELP", lang).replace("_", prefix))

        elif self.matches(extracted, trans.get("CONV_Q_LOVE", lang)):
            await reply(trans.get("CONV_LOVE", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_hello")):
            await reply(trans.get("CONV_HI", lang))

        elif self.matches(extracted, trans.get("CONV_Q_BIRTH", lang)):
            await reply(trans.get("CONV_BEGINDATE", lang))

        elif self.matches(extracted, *self._safe_get(lang, "conv_q_maker")):
            await reply(trans.get("CONV_OWNER", lang))


class NanoPlugin:
    name = "Conversation Commands"
    version = "7"

    handler = Conversation
    events = {
        "on_message": 10
        # type : importance
    }
