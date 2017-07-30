# coding=utf-8
import asyncio
import configparser
import logging

import aiohttp
import giphypop
from discord import Message, Embed, Colour

from data.stats import PRAYER, MESSAGE, IMAGE_SENT
from data.utils import is_valid_command

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

commands = {
    "_kappa": {"desc": "I couldn't resist it.", "use": None, "alias": None},
    "_rip": {"desc": "Rest in peperoni, man.", "use": "[command] [mention]", "alias": None},
    "ayy lmao": {"desc": "Yes, it's the ayy lmao meme.", "use": None, "alias": None},
    "_meme": {"desc": "Captions a meme with your text. Take a look at <https://imgflip.com/memegenerator>'s list of memes if you want.", "use": "[command] [meme name]|[top text]|[bottom text]", "alias": "_caption"},
    "_caption": {"desc": "Captions a meme with your text. Take a look at <https://imgflip.com/memegenerator>'s list of memes if you want.", "use": "[command] [meme name]|[top text]|[bottom text]", "alias": "_meme"},
    "_randomgif": {"desc": "Sends a random gif from Giphy.", "use": None, "alias": None},
}

valid_commands = commands.keys()


class MemeGenerator:
    def __init__(self, username, password, loop=asyncio.get_event_loop()):
        self.meme_endpoint = "https://api.imgflip.com/get_memes"
        self.caption_endpoint = "https://api.imgflip.com/caption_image"

        self.loop = loop

        self.username = str(username)
        self.password = str(password)

        self.meme_list = []
        self.meme_name_id = {}

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
            async with session.get(self.meme_endpoint) as resp:
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

        async with aiohttp.ClientSession() as session:
            async with session.post(self.caption_endpoint, data=payload) as req:
                return await req.json()


class Fun:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        try:
            key = parser.get("giphy", "api-key")
            self.gif = giphypop.Giphy(api_key=key if key else giphypop.GIPHY_PUBLIC_KEY)
            self.giphy_enabled = True

        except (configparser.NoSectionError, configparser.NoOptionError):
            log.critical("Missing api key for giphy, disabling command...")
            self.giphy_enabled = False

            raise RuntimeError

        try:
            username = parser.get("imgflip", "username")
            password = parser.get("imgflip", "password")
            self.generator = MemeGenerator(username, password, loop=self.loop)
            self.imgflip_enabled = True

        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Missing api key for imgflip, disabling command...")
            self.imgflip_enabled = False

            raise RuntimeError

        self.everyone_filter = None

    async def on_plugins_loaded(self):
        self.everyone_filter = self.nano.get_plugin("commons").get("instance").at_everyone_filter

    async def on_message(self, message, **kwargs):
        client = self.client
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(message, Message)

        simple_commands = {
            "ayy lmao": trans.get("MSG_AYYLMAO", lang),
            "( ͡° ͜ʖ ͡°)": trans.get("MSG_WHOKNOWS", lang)
        }

        # Loop over simple commands
        for k, v in simple_commands.items():
            if message.content.startswith(k):
                await client.send_message(message.channel, v)
                self.stats.add(MESSAGE)
                return

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix=prefix):
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
            await client.send_file(message.channel, "data/images/kappasmall.png")

            self.stats.add(IMAGE_SENT)

        elif startswith(prefix + "randomgif"):
            random_gif = self.gif.screensaver().media_url
            await client.send_message(message.channel, str(random_gif))

            self.stats.add(IMAGE_SENT)

        # !meme [meme name]|[top text]|[bottom text]
        elif startswith(prefix + "meme"):
            query = message.content[len(prefix + "meme "):]

            if not query:
                await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            middle = [a.strip(" ") for a in query.split("|")]

            # If only two arguments are passed, assume no bottom text
            if len(middle) == 2:
                name = middle[0]
                top = middle[1]
                bottom = ""

            # 0, 1 or more than 3 arguments - error
            elif len(middle) < 2 or len(middle) > 3:
                await client.send_message(message.channel, trans.get("MSG_MEME_USAGE", lang).replace("_", prefix))
                return

            # Normal
            else:
                name = middle[0]
                top = middle[1]
                bottom = middle[2]

            meme = await self.generator.caption_meme(name, top, bottom)

            if not meme:
                await client.send_message(message.channel, trans.get("MSG_MEME_NONEXISTENT", lang))
            else:
                embed = Embed(colour=Colour(0x607D8B))
                embed.set_image(url=meme)
                embed.set_footer(text=trans.get("MSG_MEME_FOOTER", lang))

                await client.send_message(message.channel, embed=embed)

        elif startswith(prefix + "rip"):
            if len(message.mentions) == 1:
                ripperoni = " " + message.mentions[0].name

            elif len(message.mentions) == 0:
                ripperoni = " " + message.content[len(prefix + "rip "):]

            else:
                ripperoni = ""

            ripperoni = self.everyone_filter(ripperoni, message.author, message.server)

            prays = self.stats.get_amount(PRAYER)
            await client.send_message(message.channel, trans.get("MSG_RIP", lang).format(ripperoni, prays))

            self.stats.add(PRAYER)


class NanoPlugin:
    name = "Admin Commands"
    version = "11"

    handler = Fun
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
