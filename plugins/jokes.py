# coding=utf-8
import asyncio
import configparser
import logging
import aiohttp
import os
import traceback

from random import randint
from ujson import loads, load
from bs4 import BeautifulSoup
from typing import Union

from discord import Embed, Colour

from data.stats import MESSAGE, IMAGE_SENT
from data.utils import is_valid_command, is_number, log_to_file
from data.confparser import get_config_parser, PLUGINS_DIR

commands = {
    "_xkcd": {"desc": "Fetches XKCD comics (defaults to random).", "use": "[command] (random/number/latest)"},
    "_joke": {"desc": "Tries to make you laugh", "use": "[command]"},
    "_cat": {"desc": "Gives you a random cat pic", "use": "[command] (gif/jpg/png)"},
}

valid_commands = commands.keys()

parser = get_config_parser()

log = logging.getLogger(__name__)


class APIFailure(Exception):
    pass


class Connector:
    def __init__(self, loop):
        self.session = aiohttp.ClientSession(loop=loop)

    @staticmethod
    def _build_url(url, **fields):
        if not url.endswith("?"):
            url += "?"

        field_list = ["{}={}".format(key, value) for key, value in fields.items()]
        return str(url) + "&".join(field_list)

    async def get_json(self, url, **fields) -> dict:
        async with self.session.get(self._build_url(url, **fields)) as resp:
            # Check if everything is ok
            if not (200 <= resp.status < 300):
                raise APIFailure("response code: {}".format(resp.status))

            return await resp.json(loads=loads, content_type=None)

    async def get_html(self, url, **fields):
        async with self.session.get(self._build_url(url, **fields)) as resp:
            # Check if everything is ok
            if not (200 <= resp.status < 300):
                raise APIFailure("response code: {}".format(resp.status))

            return await resp.text()


class CatGenerator:
    def __init__(self, loop):
        try:
            self.key = parser.get("catapi", "api-key")
        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Cat Api key not found, disabling")
            raise RuntimeError

        self.url = "http://thecatapi.com/api/images/get"
        self.format = "html"
        self.size = "med"
        self.req = Connector(loop)

    async def random_cat(self, type_="gif"):
        # structure:
        # response -> data -> images -> image -> url
        try:
            data = await self.req.get_html(self.url, api_key=self.key, format=self.format, size=self.size, type=type_)
            link = BeautifulSoup(data, "lxml").find("img").get("src")
        except (APIFailure, Exception):
            log_to_file("CatGenerator exception\n{}".format(traceback.format_exc()), "bug")
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
    def __init__(self, handler, loop=asyncio.get_event_loop()):
        self.url_latest = "http://xkcd.com/info.0.json"
        self.url_number = "http://xkcd.com/{}/info.0.json"
        self.link_base = "https://xkcd.com/{}"

        self.last_num = None
        cache_handler = handler.get_cache_handler()
        self.cache = cache_handler.get_plugin_data_manager("xkcd")

        self.req = Connector(loop)
        self.loop = loop

        self.running = True

        self.loop.create_task(self.updater())

    def exists_in_cache(self, number) -> bool:
        return self.cache.exists(number)

    def get_from_cache(self, number) -> Union[None, dict]:
        return self.cache.hgetall(number)

    def make_link(self, number) -> str:
        return self.link_base.format(number)

    async def add_to_cache(self, number, data) -> bool:
        if not is_number(number):
            return False

        if not self.exists_in_cache(number):
            self.cache.hmset(int(number), data)
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
            self.last_num = int(c["num"])
            log.info("Last comic number gotten: {}".format(self.last_num))
        else:
            log.warning("Could not get latest xkcd! (retrying in {} min)".format(5 * time_falloff))
            # First retry is always 5 minutes, after that, 25 minutes
            await asyncio.sleep(60 * 5 * time_falloff)
            await self._set_last_num(time_falloff=5)

    async def get_latest_xkcd(self) -> Union[None, dict]:
        # Checks cache
        if self.exists_in_cache(self.last_num):
            return self.get_from_cache(self.last_num)

        try:
            data = await self.req.get_json(self.url_latest)
        except APIFailure:
            return None

        await self.add_to_cache(data.get("num"), data)
        return data

    async def get_xkcd_by_number(self, num) -> Union[None, dict]:
        # Checks cache
        if self.exists_in_cache(num):
            return self.get_from_cache(num)

        try:
            data = await self.req.get_json(self.url_number.format(num))
        except APIFailure:
            return None

        await self.add_to_cache(data.get("num"), data)
        return data

    async def get_random_xkcd(self) -> Union[None, ComicImage]:
        if not self.last_num:
            return await self.get_latest_xkcd()

        num = randint(1, self.last_num)

        return await self.get_xkcd_by_number(num)


class JokeList:
    __slots__ = (
        "redis", "reddit_ns", "stupidstuff_ns"
    )

    """
    Data layout: set
        body1
        body2
        ...
    
    """

    def __init__(self, handler):
        self.stupidstuff_ns = "stupidstuff"

        self.redis = handler.get_cache_handler()

        if self.redis.scard(self.stupidstuff_ns):
            log.info("Joke 'dataset' already in db. Ready!")
            return

        log.info("Jokes not yet in redis db, adding...")

        with open(os.path.join(PLUGINS_DIR, "jokes", "stupidstuff.json")) as j:
            jokes = load(j)

        for joke in jokes:
            # Verify that %SEP% exists
            # if "%SEP%" not in joke:
            #     raise LookupError("invalid jokes.json")

            self.redis.sadd(self.stupidstuff_ns, joke)

        del jokes
        log.info("Dataset ready!")

    def random_joke(self) -> str:
        # title, body = self.redis.srandmember(self.r_namespace)[0].split("%SEP%")
        # return title, body

        return self.redis.srandmember(self.stupidstuff_ns)[0]


class Joke:
    __slots__ = (
        "client", "loop", "handler", "nano", "stats", "trans", "cats", "xkcd", "joke"
    )

    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.cats = CatGenerator(self.loop)
        self.xkcd = XKCD(self.handler, self.loop)
        self.joke = JokeList(self.handler)

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

            xkcd_link = self.xkcd.make_link(xkcd["num"])

            embed = Embed(title=trans.get("MSG_XKCD", lang).format(xkcd["num"]), description=xkcd["safe_title"])
            embed.set_image(url=xkcd["img"])
            embed.set_footer(text=trans.get("MSG_XKCD_SOURCe", lang).format(xkcd_link))

            await message.channel.send(embed=embed)

        # !joke (yo mama/chuck norris)
        elif startswith(prefix + "joke"):
            content = self.joke.random_joke()

            embed = Embed(description=content)
            await message.channel.send(embed=embed)


class NanoPlugin:
    name = "Joke-telling module"
    version = "10"

    handler = Joke
    events = {
        "on_message": 10
    }
