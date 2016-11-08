# coding=utf-8
import giphypop
from discord import Message
from data.utils import is_valid_command
from data.stats import NanoStats, PRAYER, MESSAGE, IMAGE_SENT

simple_commands = {
    "_johncena": "ITS JOHN CENA",
    "ayy lmao": "My inspiration in the world of memes.",
    "( ͡° ͜ʖ ͡°)": "¯\_(ツ)_/¯ indeed"
}

valid_commands = [
    "_kappa", "_cat", "_randomgif", "_rip"
]


class Fun:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        self.gif = giphypop.Giphy()

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)
        assert isinstance(self.stats, NanoStats)

        prefix = kwargs.get("prefix")
        client = self.client

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # Loop over simple commands
        for trigger, response in simple_commands.items():
            if message.content.startswith(trigger.replace("_", prefix)):
                await client.send_message(message.channel, response)
                self.stats.add(MESSAGE)

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        # Other commands
        if startswith(prefix + "kappa"):
            await client.send_file(message.channel, "data/images/kappasmall.png")

            self.stats.add(IMAGE_SENT)

        elif startswith(prefix + "cat"):
            await client.send_file(message.channel, "data/images/cattypo.gif")

            self.stats.add(IMAGE_SENT)

        elif startswith(prefix + "randomgif"):
            random_gif = self.gif.screensaver().media_url
            await client.send_message(message.channel, str(random_gif))

            self.stats.add(IMAGE_SENT)

        elif startswith(prefix + "rip"):
            if len(message.mentions) == 1:
                ripperoni = message.mentions[0].mention

            elif len(message.mentions) == 0:
                ripperoni = message.content[len(prefix + "rip "):]

            else:
                ripperoni = ""

            prays = self.stats.get_amount(PRAYER)
            await client.send_message(message.channel, "Rest in pepperoni{}{}.\n`{}` *prayers said so far*...".format(", " if ripperoni else "", ripperoni, prays))

            self.stats.add(PRAYER)


class NanoPlugin:
    _name = "Admin Commands"
    _version = 0.1

    handler = Fun
    events = {
        "on_message": 10
        # type : importance
    }
