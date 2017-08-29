# coding=utf-8
import asyncio
import configparser
import logging
import aiohttp

from random import randint
from ujson import loads
from bs4 import BeautifulSoup
from typing import Union

from discord import Embed, Colour

from data.stats import MESSAGE, IMAGE_SENT
from data.utils import is_valid_command, is_number, log_to_file
from data.confparser import get_config_parser

commands = {
    "_xkcd": {"desc": "Fetches XKCD comics for you (defaults to random).", "use": "[command] (random/number/latest)"},
    "_joke": {"desc": "Tries to make you laugh (defaults to random joke)", "use": "[command] (yo mama/chuck norris)"},
    "_cat": {"desc": "Gives you a random cat pic", "use": "[command] (gif/jpg/png)"},
}

valid_commands = commands.keys()

parser = get_config_parser()

log = logging.getLogger(__name__)


class APIFailure(Exception):
    pass


class Connector:
    def __init__(self):
        self.session = None

    def _handle_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

        return self.session

    @staticmethod
    def _build_url(url, **fields):
        if not url.endswith("?"):
            url += "?"

        field_list = ["{}={}".format(key, value) for key, value in fields.items()]
        return str(url) + "&".join(field_list)

    async def get_json(self, url, **fields) -> dict:
        session = self._handle_session()

        async with session.get(self._build_url(url, **fields)) as resp:
            # Check if everything is ok
            if not (200 <= resp.status < 300):
                raise APIFailure("response code: {}".format(resp.status))

            text = await resp.text()
            return loads(text)

    async def get_html(self, url, **fields):
        session = self._handle_session()

        async with session.get(self._build_url(url, **fields)) as resp:
            # Check if everything is ok
            if not (200 <= resp.status < 300):
                raise APIFailure("response code: {}".format(resp.status))

            return await resp.text()


class CatGenerator:
    def __init__(self):
        try:
            self.key = parser.get("catapi", "api-key")
        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Cat Api key not found, disabling")
            raise RuntimeError

        self.url = "http://thecatapi.com/api/images/get"
        self.format = "html"
        self.size = "med"
        self.req = Connector()

    async def random_cat(self, type_="gif"):
        # structure:
        # response -> data -> images -> image -> url
        try:
            data = await self.req.get_html(self.url, api_key=self.key, format=self.format, size=self.size, type=type_)
            link = BeautifulSoup(data, "lxml").find("img").get("src")
        except (APIFailure, Exception) as e:
            log_to_file("CatGenerator exception: {}".format(e))
            return None

        return link


class ComicImage:
    __slots__ = ("img", "num", "link", "safe_title")

    def __init__(self, **kwargs):
        # for name, value in kwargs.items():
        #     try:
        #         self.__setattr__(name, value)
        #     except AttributeError:
        #         pass

        # Performance ftw
        self.img = kwargs.get("img")
        self.num = kwargs.get("num")
        self.link = kwargs.get("link")
        self.safe_title = kwargs.get("safe_title")


class XKCD:
    def __init__(self, loop=asyncio.get_event_loop()):
        self.url_latest = "http://xkcd.com/info.0.json"
        self.url_number = "http://xkcd.com/{}/info.0.json"
        self.link_base = "https://xkcd.com/{}"

        self.last_num = None
        self.cache = {}

        self.req = Connector()
        self.loop = loop

        self.running = True

        self.loop.create_task(self.updater())

    def exists_in_cache(self, number) -> bool:
        return bool(self.cache.get(number))

    def get_from_cache(self, number) -> Union[None, ComicImage]:
        return self.cache.get(number)

    def make_link(self, number) -> str:
        return self.link_base.format(number)

    async def add_to_cache(self, number, data) -> bool:
        if not is_number(number):
            return False

        if not self.exists_in_cache(number):
            self.cache[int(number)] = data
            return True
        else:
            return False

    async def updater(self):
        while self.running:
            await self._set_last_num()
            # Update every 6 hours
            await asyncio.sleep(3600*6)

    async def _set_last_num(self, time_falloff=1):
        c = await self.get_latest_xkcd()

        if c:
            self.last_num = int(c.num)
            log.info("Last comic number gotten: {}".format(self.last_num))
        else:
            log.warning("Could not get latest xkcd number! (retrying in {} min)".format(5 * time_falloff))
            # First retry is always 5 minutes, after that, 25 minutes
            await asyncio.sleep(60 * 5 * time_falloff)
            await self._set_last_num(time_falloff=5)

    async def get_latest_xkcd(self) -> Union[None, ComicImage]:
        # Checks cache
        if self.exists_in_cache(self.last_num):
            return self.get_from_cache(self.last_num)

        try:
            data = await self.req.get_json(self.url_latest)
        except APIFailure:
            return None

        comic = ComicImage(**data)
        await self.add_to_cache(data.get("num"), comic)
        return comic

    async def get_xkcd_by_number(self, num) -> Union[None, ComicImage]:
        # Checks cache
        if self.exists_in_cache(num):
            return self.get_from_cache(num)

        try:
            data = await self.req.get_json(self.url_number.format(num))
        except APIFailure:
            return None

        comic = ComicImage(**data)
        await self.add_to_cache(data.get("num"), comic)
        return comic

    async def get_random_xkcd(self) -> Union[None, ComicImage]:
        if not self.last_num:
            return await self.get_latest_xkcd()

        num = randint(1, self.last_num)

        return await self.get_xkcd_by_number(num)


class JokeGenerator:
    def __init__(self):
        self.yo_mama = "http://api.yomomma.info/"
        self.chuck = "https://api.chucknorris.io/jokes/random"

        self.req = Connector()

        # More are added as time goes on
        # Hardcoded because why not
        self.cache = [
            "Yo mama's so fat the only alphabet she knows is her KFC's",
            "Yo mama so fat the last time she saw 90210 was on a scale",
            "Chuck Norris can arm wrestle with both hands tied behind his back.",
            "Yo mama so fat that she fell over and rocked herself to sleep trying to get up"
        ]

    async def get_random_cache(self) -> str:
        if len(self.cache) > 8:
            rand = randint(0, len(self.cache) - 1)
            return self.cache[rand]

        # Else just try a new joke
        else:
            await self.get_joke(randint(0, 1))

    def add_to_cache(self, joke):
        if joke not in self.cache:
            self.cache.append(joke)

    async def yomama_joke(self) -> Union[str, None]:
        try:
            joke = await self.req.get_json(self.yo_mama)
        except APIFailure:
            return None

        if not joke:
            return None

        self.add_to_cache(joke.get("joke"))
        return joke.get("joke")

    async def chuck_joke(self) -> Union[str, None]:
        try:
            joke = await self.req.get_json(self.chuck)
        except APIFailure:
            return None

        if not joke:
            return None

        self.add_to_cache(joke.get("value"))
        return joke.get("value")

    async def get_joke(self, type_=None) -> Union[str, None]:
        # Defaults to a random joke type
        if type_ is None:
            type_ = randint(0, 2)

        if type_ == 0:
            return await self.yomama_joke()
        elif type_ == 1:
            return await self.chuck_joke()

        else:
            return await self.get_random_cache()


class Joke:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.cats = CatGenerator()
        self.xkcd = XKCD(self.loop)
        self.joke = JokeGenerator()

    async def on_message(self, message, **kwargs):
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

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

        # !cat gif/jpg/png
        if startswith(prefix + "cat"):
            fmt = str(message.content[len(prefix + "cat"):]).strip(" ")

            # GIF is the default type!
            if fmt == "jpg":
                type_ = "jpg"
            elif fmt == "png":
                type_ = "png"
            else:
                type_ = "gif"

            pic = await self.cats.random_cat(type_)

            if pic:
                # Teal (blue-ish)
                embed = Embed(colour=Colour(0x00796b))
                embed.set_image(url=pic)
                embed.set_footer(text=trans.get("MSG_CAT_FOOTER", lang))

                await message.channel.send(embed=embed)
            else:
                await message.channel.send(trans.get("MSG_CAT_FAILED", lang))

            self.stats.add(IMAGE_SENT)

        # !xkcd random/number/latest
        elif startswith(prefix + "xkcd"):
            fmt = str(message.content[len(prefix + "xkcd"):]).strip(" ")

            # Decides mode
            fetch = "random"
            if fmt:
                if is_number(fmt):
                    # Check if number is valid
                    if int(fmt) > self.xkcd.last_num:
                        await message.channel.send(trans.get("MSG_XKCD_NO_SUCH", lang))
                        return
                    else:
                        fetch = "number"
                elif fmt == trans.get("INFO_RANDOM", lang) or fmt == "random":
                    fetch = "random"
                # Any other argument means latest
                else:
                    fetch = "latest"
            # Default: random
            else:
                fetch == "random"

            if fetch == "random":
                xkcd = await self.xkcd.get_random_xkcd()
            elif fetch == "number":
                xkcd = await self.xkcd.get_xkcd_by_number(fmt)
            # Can only mean latest
            else:
                xkcd = await self.xkcd.get_latest_xkcd()

            # In case something went wrong
            if not xkcd:
                await message.channel.send(trans.get("MSG_XKCD_FAILED", lang))
                log_to_file("XKCD: string {}, fetch: {}, got None".format(fmt, fetch))

            xkcd_link = self.xkcd.make_link(xkcd.num)

            embed = Embed(title=trans.get("MSG_XKCD", lang).format(xkcd.num), description=xkcd.safe_title)
            embed.set_image(url=xkcd.img)
            embed.set_footer(text=trans.get("MSG_XKCD_SOURCe", lang).format(xkcd_link))

            await message.channel.send(embed=embed)

        # !joke (yo mama/chuck norris)
        elif startswith(prefix + "joke"):
            arg = str(message.content[len(prefix + "joke"):]).strip(" ").lower()

            if arg == "yo mama":
                joke = await self.joke.get_joke(0)
            elif arg == "chuck norris":
                joke = await self.joke.get_joke(1)
            else:
                # Already random
                joke = await self.joke.get_joke()

            if not joke:
                await message.channel.send(trans.get("MSG_JOKE_FAILED", lang))
                return

            await message.channel.send(str(joke))


class NanoPlugin:
    name = "Joke-telling module"
    version = "9"

    handler = Joke
    events = {
        "on_message": 10
    }
