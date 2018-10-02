# coding=utf-8
import logging
from random import randint
from fuzzywuzzy import fuzz, process


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Conversation:
    def __init__(self, *_, **kwargs):
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.trans = kwargs.get("trans")
        self.loop = kwargs.get("loop")


    def _safe_get(self, lang, lst):
        return self.trans.get(lst, lang) or []

    @staticmethod
    def matches(query: str, possibilities: list):
        highest, score = process.extractOne(query, possibilities, scorer=fuzz.token_set_ratio)

        if score > 80:
            return True
        else:
            return False

    async def on_message(self, message, **kwargs):
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
            await message.channel.send(msg)

        extracted = message.content.replace("<@{}>".format(self.client.user.id), "").strip(" ")

        # RESPONSES

        # If it is just a raw mention, send the help message
        if extracted == "":
            await message.channel.send(trans.get("MSG_HELP", lang).format(prefix=prefix))

        elif has(trans.get("INFO_PREFIX_LITERAL", lang)):
            await message.channel.send(trans.get("INFO_PREFIX", lang).format(prefix))

        elif self.matches(extracted, trans.get("CONV_Q_HOW", lang)):
            lst = trans.get("CONV_MOOD_LIST", lang)

            # Choose random reply
            rn = randint(0, len(lst) - 1)

            await reply(str(lst[rn]))

        elif self.matches(extracted, trans.get("CONV_Q_SNOW", lang)):
            await reply(trans.get("CONV_SNOW", lang))

        elif has(trans.get("CONV_Q_DIE", lang)):
            await reply(trans.get("CONV_NAH", lang))

        elif self.matches(extracted, trans.get("CONV_Q_SLEEP", lang)):
            await reply(trans.get("CONV_NOPE", lang))

        elif self.matches(extracted, trans.get("CONV_Q_AYY", lang)):
            await reply(trans.get("CONV_AYYLMAO", lang))

        elif self.matches(extracted, trans.get("CONV_Q_RIP", lang)):
            await reply(trans.get("CONV_RIP", lang))

        elif self.matches(extracted, trans.get("CONV_Q_MASTER", lang)):
            await reply(trans.get("CONV_MASTER", lang))

        elif has(trans.get("CONV_Q_WHAT", lang)):
            await reply(trans.get("CONV_SPARTA", lang))

        elif self.matches(extracted, trans.get("INFO_HELP", lang)):
            await reply(trans.get("MSG_HELP", lang).format(prefix=prefix))

        elif self.matches(extracted, trans.get("CONV_Q_LOVE", lang)):
            await reply(trans.get("CONV_LOVE", lang))

        elif self.matches(extracted, trans.get("CONV_Q_HELLO", lang)):
            await reply(trans.get("CONV_HI", lang))

        elif self.matches(extracted, trans.get("CONV_Q_BIRTH", lang)):
            await reply(trans.get("CONV_BEGINDATE", lang))

        elif self.matches(extracted, trans.get("CONV_Q_MAKER", lang)):
            await reply(trans.get("CONV_OWNER", lang))


class NanoPlugin:
    name = "Conversation Commands"
    version = "8"

    handler = Conversation
    events = {
        "on_message": 10
        # type : importance
    }
