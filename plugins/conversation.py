# coding=utf-8
import logging
from random import randint
from discord import Message
from .help import help_nano

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Conversation:
    def __init__(self, *_, **kwargs):
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")

    async def on_message(self, message, **_):
        assert isinstance(message, Message)
        client = self.client

        if self.client.user not in message.mentions:
            return

        def has(*args):
            for arg in args:
                if arg in str(message.content).lower():
                    return True

            return False

        # RESPONSES

        if has("how are you", "whats up"):
            lst = ["I'm awesome!", "Doing great.",
                   "Doing awesome. Pumpin' dem messages out like it's christmas babyyy!",
                   "It's been a beautiful day so far."]

            # Choose random reply
            rn = randint(0, len(lst) - 1)

            await client.send_message(message.channel, str(lst[rn]))

        elif has("do you wanna build a snowman", "do you want to build a snowman"):
            await client.send_message(message.channel, "C'mon lets go out and play!")

        elif has("die"):
            await client.send_message(message.channel, "Nah :wink:")

        elif has("do you ever stop", "do you ever get tired", "do you even sleep", "do you sleep"):
            await client.send_message(message.channel, "Nope.")

        elif has("ayy"):
            await client.send_message(message.channel, "Ayy. Lmao.")

        elif has("rip"):
            await client.send_message(message.channel, "Rest in pepperoni indeed **pays respects**")

        elif has("do you have a master"):
            await client.send_message(message.channel, "Dobby has no master.")

        elif has("what is this"):
            await client.send_message(message.channel, "THIS IS SPARTA!")

        elif has("help"):
            await client.send_message(message.channel, help_nano)

        elif has("i love you", "<3"):
            await client.send_message(message.channel, "<3")

        elif has("fuck you"):
            await client.send_message(message.channel, "I cri everytiem.")


class NanoPlugin:
    _name = "Conversation Commands"
    _version = 0.1

    handler = Conversation
    events = {
        "on_message": 10
        # type : importance
    }
