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

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        client = self.client
        prefix = kwargs.get("prefix")

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
            await client.send_message(message.channel, help_nano.replace(">", prefix))

        elif has("prefix"):
            await client.send_message(message.channel, "The prefix for this server is **{}**".format(prefix))

        elif has("how are you", "whats up"):
            lst = ["I'm awesome!", "Doing great.",
                   "Doing awesome. Pumpin' dem messages out like it's christmas babyyy!",
                   "It's been a beautiful day so far."]

            # Choose random reply
            rn = randint(0, len(lst) - 1)

            await reply(str(lst[rn]))

        elif has("do you wanna build a snowman", "do you want to build a snowman"):
            await reply("C'mon lets go out and play!")

        elif has("die"):
            await reply("Nah :wink:")

        elif has("do you ever stop", "do you ever get tired", "do you even sleep", "do you sleep"):
            await reply("Nope.")

        elif has("ayy"):
            await reply("Ayy. Lmao.")

        elif has("rip"):
            await reply("Rest in pepperoni indeed **pays respects**")

        elif has("do you have a master"):
            await reply("Dobby has no master.")

        elif has("what is this"):
            await reply("THIS IS SPARTA!")

        elif has("help"):
            await reply(help_nano.replace(">", prefix))

        elif has("i love you", "<3"):
            await reply("<3")

        elif has("fuck you"):
            await reply("I cri everytiem.")

        elif has("hi", "hello"):
            await reply("Hi there!")


class NanoPlugin:
    name = "Conversation Commands"
    version = "0.2.1"

    handler = Conversation
    events = {
        "on_message": 10
        # type : importance
    }
