# coding=utf-8
import wikipedia
import logging
import configparser
import requests
from discord import Message
from bs4 import BeautifulSoup
from data.stats import MESSAGE
from data.utils import is_valid_command

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

valid_commands = [
    "_urban", "_wiki", "_define"
]


class Definitions:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        prefix = kwargs.get("prefix")
        client = self.client

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "wiki", prefix + "define"):
            if startswith(prefix + "wiki"):
                search = str(message.content)[len(prefix + "wiki "):]

            elif startswith(prefix + "define"):
                search = str(message.content)[len(prefix + "define "):]

            else:
                return

            if not search or search == " ":  # If empty args
                await client.send_message(message.channel, "Please include a word you want to define.")
                return

            try:
                answer = wikipedia.summary(search, sentences=parser.get("wiki", "sentences"), auto_suggest=True)
                await client.send_message(message.channel, "**{} :** \n".format(search) + answer)

            except wikipedia.exceptions.PageError:
                await client.send_message(message.channel, "No definitions found.")

            except wikipedia.exceptions.DisambiguationError:
                await client.send_message(message.channel,
                                          "Got multiple definitions of {}, please be more specific (somehow).".format(search))

        elif startswith(prefix + "urban"):
            search = str(message.content)[len(prefix + "urban "):]
            define = requests.get("http://www.urbandictionary.com/define.php?term={}".format(search))
            answer = BeautifulSoup(define.content, "html.parser").find("div", attrs={"class": "meaning"}).text

            # Check if there are no definitions
            if str(answer).startswith("\nThere aren't any"):
                await client.send_message(message.channel, "No definition found")

            else:
                await client.send_message(message.channel, "**" + message.content[7:] + "** *:*" + answer)


class NanoPlugin:
    _name = "Wiki/Urban Commands"
    _version = 0.1

    handler = Definitions
    events = {
        "on_message": 10
        # type : importance
    }
