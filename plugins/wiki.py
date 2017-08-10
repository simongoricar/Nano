# coding=utf-8
import configparser
import logging

import aiohttp
from typing import Union
from discord import Message

try:
    from ujson import loads
except ImportError:
    from json import loads

from data.stats import MESSAGE
from data.utils import is_valid_command, add_dots

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

MAX_WIKI_LENGTH = parser.getint("wiki", "max-length")
MAX_URBAN_LENGTH = parser.getint("urban", "max-length")


commands = {
    "_wiki": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "[command] [word]", "alias": "_define"},
    "_define": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "[command] [word]", "alias": "_wiki"},
    "_urban": {"desc": "Gives you the definition of a word from Urban Dictionary.", "use": "[command] [word]", "alias": None},
}

valid_commands = commands.keys()


def build_url(url, **fields):
    if not url.endswith("?"):
        url += "?"

    field_list = ["{}={}".format(key, value) for key, value in fields.items()]
    return str(url) + "&".join(field_list)


class WikipediaParser:
    def __init__(self, loop):
        self.session = aiohttp.ClientSession(loop=loop)
        self.endpoint = "https://en.wikipedia.org/w/api.php"
    async def get_definition(self, query: str) -> Union[str, None]:
        data = await self._get_definition(query)

        pages = data.get("query").get("pages")
        # No results
        if "-1" in pages.keys():
            return None

        # Get first (only, due to rvlimit) page
        f_page = pages[list(pages.keys())[0]]
        return f_page.get("extract")

    async def _get_definition(self, query: str):
        # Reference
        # https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro=&explaintext=&titles=Bicycle
        payload = {
            "format": "json",
            "action": "query",
            "titles": query,
            "prop": "extracts",
            "exintro": "",
            "explaintext": "",
            "redirects": 1,
            "exlimit": 1
        }

        async with self.session.get(build_url(self.endpoint, **payload)) as resp:
            if 200 < resp.status <= 300:
                # Anything other than 200 is not good
                raise ConnectionError("WikipediaParser status code: {}".format(resp.status))

            # Converts to json format
            return await resp.json(loads=loads)


class UrbanDictionary:
    def __init__(self, loop):
        self.session = aiohttp.ClientSession(loop=loop)
        self.endpoint = "http://api.urbandictionary.com/v0/define"

    async def urban_dictionary(self, query: str) -> Union[str, None]:
        data = await self._get_definition(query)

        items = data.get("list")
        if not items:
            return None

        return items[0].get("definition")

    async def _get_definition(self, query: str):
        payload = {
            "term": query
        }

        async with self.session.get(build_url(self.endpoint, **payload)) as resp:
            if 200 < resp.status <= 300:
                # Anything other than 200 is not good
                raise ConnectionError("UrbanDictionary status code: {}".format(resp.status))

            # Converts to json format
            return await resp.json(loads=loads)

class Definitions:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")
        self.loop = kwargs.get("loop")

        self.wiki = WikipediaParser(self.loop)
        self.urban = UrbanDictionary(self.loop)

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        prefix = kwargs.get("prefix")
        client = self.client

        trans = self.trans
        lang = kwargs.get("lang")

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
                search = str(message.content)[len(prefix + "wiki "):].strip(" ")
            elif startswith(prefix + "define"):
                search = str(message.content)[len(prefix + "define "):].strip(" ")
            else:
                # Not possible, but k
                return

            if not search:
                await message.channel.send(trans.get("MSG_WIKI_NO_QUERY", lang))
                return

            summary = await self.wiki.get_definition(search)

            if not summary:
                await message.channel.send(trans.get("MSG_WIKI_NO_DEF", lang))
                return

            await client.send_message(message.channel,
                                      trans.get("MSG_WIKI_DEFINITION", lang).format(search,
                                                                                    add_dots(summary, max_len=MAX_WIKI_LENGTH)))

        elif startswith(prefix + "urban"):
            search = str(message.content)[len(prefix + "urban "):].strip(" ")

            if not search:
                await message.channel.send(trans.get("MSG_URBAN_NO_QUERY", lang))
                return

            description = await self.urban.urban_dictionary(search)

            if not description:
                await message.channel.send(trans.get("MSG_URBAN_NO_DEF", lang))
                return

            await client.send_message(message.channel,
                                      trans.get("MSG_URBAN_DEFINITION", lang).format(search, add_dots(description, max_len=MAX_URBAN_LENGTH)))


class NanoPlugin:
    name = "Wiki/Urban Commands"
    version = "7"

    handler = Definitions
    events = {
        "on_message": 10
        # type : importance
    }
