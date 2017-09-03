# coding=utf-8
import asyncio
import configparser
import logging
import os
import aiohttp

try:
    from ujson import loads
except ImportError:
    from json import loads

from discord import Message, Embed, Colour, File

from data.stats import PRAYER, MESSAGE, IMAGE_SENT
from data.utils import is_valid_command, build_url
from data.confparser import get_config_parser

# plugins/config.ini
parser = get_config_parser()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Giphy's green color thingie
GIPHY_GREEN = 0x00C073


commands = {
    "_kappa": {"desc": "I couldn't resist it."},
    "_rip": {"desc": "Rest in peperoni, man.", "use": "[command] [mention]"},
    "_meme": {"desc": "Captions a meme with your text. Take a look at <https://imgflip.com/memegenerator>'s list of memes if you want.", "use": "[command] [meme name]|[top text]|[bottom text]", "alias": "_caption"},
    "_caption": {"desc": "Captions a meme with your text. Take a look at <https://imgflip.com/memegenerator>'s list of memes if you want.", "use": "[command] [meme name]|[top text]|[bottom text]", "alias": "_meme"},
    "_randomgif": {"desc": "Sends a random gif from Giphy. Optionally, specify a tag after the command.", "use": "[command] (optional: tag)"},
}

valid_commands = commands.keys()


class MemeGenerator:
    MEME_ENDPOINT = "https://api.imgflip.com/get_memes"
    CAPTION_ENDPOINT = "https://api.imgflip.com/caption_image"

    def __init__(self, username, password, loop=asyncio.get_event_loop()):

        self.loop = loop

        self.username = str(username)
        self.password = str(password)

        self.meme_list = []
        self.meme_name_id = {}

        self.session = aiohttp.ClientSession()

        loop.create_task(self.prepare())

    async def prepare(self):
        raw = await self.get_memes()

        if raw.get("success") is not True:
            raise LookupError("could not get meme list")

        self.meme_list = list(raw.get("data").get("memes"))

        for m_dict in self.meme_list:
            self.meme_name_id[str(m_dict.get("name")).lower()] = m_dict.get("id")

        log.info("Ready to make memes")

    async def get_memes(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(MemeGenerator.MEME_ENDPOINT) as resp:
                return await resp.json()

    async def caption_meme(self, name, top, bottom):
        meme_id = self.meme_name_id.get(str(name).lower())

        if not meme_id:
            return None

        resp = await self._caption_meme(meme_id, top, bottom)

        if resp.get("success") is not True:
            raise LookupError("failed: {}".format(resp.get("error_message")))

        return str(resp.get("data").get("url"))

    async def _caption_meme(self, meme_id, top, bottom):
        payload = dict(
            username=self.username,
            password=self.password,
            text0=top,
            text1=bottom,
            template_id=meme_id,
        )

        async with self.session.post(MemeGenerator.CAPTION_ENDPOINT, data=payload) as resp:
            return await resp.json(loads=loads, content_type=None)


class GiphyApiError(Exception):
    pass


class GiphyApi:
    RANDOM_GIF = "https://api.giphy.com/v1/gifs/random"

    def __init__(self, api_key: str):
        self.key = str(api_key)
        self.session = aiohttp.ClientSession()

    async def _parse_response(self, response):
        meta = response.get("meta").get("msg")

        if meta != "OK":
            raise GiphyApiError("Not ok: {}".format(meta))

        data = response.get("data")
        return data.get("image_original_url")

    async def get_random_gif(self, optional_tag=None):
        """
        Gets a random gif (optionally with a tag)
        :param optional_tag: str or None

        :return:

            -1   : HTTP 429
        :raises GiphyApiError
        """
        payload = {
            "api_key": self.key,
            "fmt": "json"
        }

        if optional_tag is not None:
            payload["tag"] = str(optional_tag)

        full_url = build_url(GiphyApi.RANDOM_GIF, **payload)

        async with self.session.get(full_url) as resp:

            if resp.status == 429:
                return -1

            if 200 < resp.status <= 300:
                # Anything other than 200 is not good
                raise ConnectionError("GiphyApi status code: {}".format(resp.status))

            data = await resp.json(loads=loads, content_type=None)

            return await self._parse_response(data)


class Fun:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        try:
            api_key = parser.get("giphy", "api-key")
            self.gif = GiphyApi(api_key)
        except configparser.Error:
            log.critical("Missing api key for giphy, disabling command...")
            self.giphy_enabled = False

        try:
            username = parser.get("imgflip", "username")
            password = parser.get("imgflip", "password")
            self.generator = MemeGenerator(username, password, loop=self.loop)
            self.imgflip_enabled = True
        except configparser.Error:
            log.critical("Missing credentials for imgflip, disabling command...")
            self.imgflip_enabled = False

        self.everyone_filter = None

    async def on_plugins_loaded(self):
        self.everyone_filter = self.nano.get_plugin("commons").get("instance").at_everyone_filter

    async def on_message(self, message, **kwargs):
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(message, Message)

        simple_commands = {
            "( ͡° ͜ʖ ͡°)": trans.get("MSG_WHOKNOWS", lang)
        }

        # Loop over simple commands
        for k, v in simple_commands.items():
            if message.content.startswith(k):
                await message.channel.send(v)
                self.stats.add(MESSAGE)
                return

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # Other commands
        if startswith(prefix + "kappa"):
            await message.channel.send(file=File("data/images/kappasmall.png", "kappa.png"))

            self.stats.add(IMAGE_SENT)

        # !randomgif (optional_tag)
        elif startswith(prefix + "randomgif"):
            tags = message.content[len(prefix + "randomgif "):]

            gif = await self.gif.get_random_gif(tags or None)

            if gif == -1:
                await message.channel.send(trans.get("MSG_GIPHY_TOOFAST", lang))
                return

            embed = Embed(colour=Colour(GIPHY_GREEN))
            embed.set_image(url=gif)
            embed.set_footer(text=trans.get("MSG_GIPHY_POWEREDBY", lang))

            await message.channel.send(embed=embed)

            self.stats.add(IMAGE_SENT)

        # !meme [meme name]|[top text]|[bottom text]
        elif startswith(prefix + "meme"):
            query = message.content[len(prefix + "meme "):]

            if not query:
                await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            middle = [a.strip(" ") for a in query.split("|")]

            # If only two arguments are passed, assume no bottom text
            if len(middle) == 2:
                name = middle[0]
                top = middle[1]
                bottom = ""

            # 0, 1 or more than 3 arguments - error
            elif len(middle) < 2 or len(middle) > 3:
                await message.channel.send(trans.get("MSG_MEME_USAGE", lang).replace("_", prefix))
                return

            # Normal
            else:
                name = middle[0]
                top = middle[1]
                bottom = middle[2]

            meme = await self.generator.caption_meme(name, top, bottom)

            if not meme:
                await message.channel.send(trans.get("MSG_MEME_NONEXISTENT", lang))
            else:
                embed = Embed(colour=Colour(0x607D8B))
                embed.set_image(url=meme)
                embed.set_footer(text=trans.get("MSG_MEME_FOOTER", lang))

                await message.channel.send(embed=embed)

        elif startswith(prefix + "rip"):
            if len(message.mentions) == 1:
                ripperoni = " " + message.mentions[0].name

            elif len(message.mentions) == 0:
                ripperoni = " " + message.content[len(prefix + "rip "):]

            else:
                ripperoni = ""

            ripperoni = self.everyone_filter(ripperoni, message.author, force_remove=True)

            prays = self.stats.get_amount(PRAYER)
            await message.channel.send(trans.get("MSG_RIP", lang).format(ripperoni, prays))

            self.stats.add(PRAYER)


class NanoPlugin:
    name = "Admin Commands"
    version = "13"

    handler = Fun
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
