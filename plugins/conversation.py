# coding=utf-8
import logging
from random import randint

from discord import Message

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Conversation:
    def __init__(self, *_, **kwargs):
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.trans = kwargs.get("trans")

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
                if arg in str(message.content).lower():
                    return True

            return False

        async def reply(msg: str):
            await client.send_message(message.channel, msg)

        # RESPONSES

        # If it is just a raw mention, send the help message
        if str(message.content).replace("<@{}>".format(self.client.user.id), "").strip(" ") == "":
            await client.send_message(message.channel, trans.get("MSG_HELP", lang).replace("_", prefix))

        elif has("prefix"):
            await client.send_message(message.channel, trans.get("INFO_PREFIX", lang).format(prefix))

        elif has(trans.get("CONV_Q_HOW", lang), trans.get("CONV_Q_WUP", lang)):
            lst = [a.strip(" ") for a in trans.get("CONV_MOOD_LIST", lang).split("|")]

            # Choose random reply
            rn = randint(0, len(lst) - 1)

            await reply(str(lst[rn]))

        elif has(trans.get("CONV_Q_SNOW", lang)):
            await reply(trans.get("CONV_SNOW", lang))

        elif has(trans.get("CONV_Q_DIE", lang)):
            await reply(trans.get("CONV_NAH", lang))

        elif has(*[a.strip(" ") for a in trans.get("CONV_Q_SLEEP", lang).split(" ")]):
            await reply(trans.get("CONV_NOPE", lang))

        elif has(trans.get("CONV_Q_AYY", lang)):
            await reply(trans.get("CONV_AYYLMAO", lang))

        elif has(trans.get("CONV_Q_RIP", lang)):
            await reply(trans.get("CONV_RIP", lang))

        elif has(trans.get("CONV_Q_MASTER", lang)):
            await reply(trans.get("CONV_MASTER", lang))

        elif has(trans.get("CONV_Q_WHAT", lang)):
            await reply(trans.get("CONV_SPARTA", lang))

        elif has(trans.get("INFO_HELP", lang)):
            await reply(trans.get("MSG_HELP", lang).replace("_", prefix))

        elif has(trans.get("CONV_Q_LOVE", lang)):
            await reply(trans.get("CONV_LOVE", lang))

        elif has(*[a.strip(" ") for a in trans.get("CONV_Q_HELLO", lang)]):
            await reply(trans.get("CONV_HI", lang))


class NanoPlugin:
    name = "Conversation Commands"
    version = "0.2.1"

    handler = Conversation
    events = {
        "on_message": 10
        # type : importance
    }
