import aiohttp
import configparser
import logging
from random import randint
import asyncio
from bs4 import BeautifulSoup
from ujson import loads
from discord import Message, Client
from data.utils import is_valid_command, StandardEmoji, is_number
from data.stats import MESSAGE, IMAGE_SENT

commands = {
    "_xkcd": {"desc": "Fetches XKCD comics for you (defaults to random).", "use": "[command] (random/number/latest)", "alias": None},
    "_joke": {"desc": "Tries to make you laugh (defaults to random joke)", "use": "[command] (yo mama/chuck norris)", "alias": None},
    "_cat": {"desc": "Tells you a random joke", "use": "[command] (gif/jpg/png)", "alias": None},
}

valid_commands = commands.keys()

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class APIFailure(Exception):
    pass


class Requester:
    def __init__(self):
        pass

    @staticmethod
    def _build_url(url, **fields):
        if not url.endswith("?"):
            url += "?"

        field_list = ["{}={}".format(key, value) for key, value in fields.items()]
        return str(url) + "&".join(field_list)

    async def get_json(self, url, **fields) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self._build_url(url, **fields)) as resp:
                # Check if everything is ok
                if not (200 <= resp.status < 300):
                    raise APIFailure("response code: {}".format(resp.status))

                text = await resp.text()
                return loads(text)

    async def get_html(self, url, **fields):
        async with aiohttp.ClientSession() as session:
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
            raise LookupError

        self.url = "http://thecatapi.com/api/images/get"
        self.format = "html"
        self.size = "med"
        self.type = "gif"
        self.req = Requester()

    async def random_cat(self, type_="gif"):
        # structure:
        # response -> data -> images -> image -> url
        try:
            data = await self.req.get_html(self.url, api_key=self.key, format=self.format, size=self.size, type=type_)
            link = BeautifulSoup(data, "lxml").find("img").get("src")
        except (APIFailure, Exception):
            return None

        return link


class Comic:
    __slots__ = (
        "month", "num", "link", "year", "news", "safe_title",
        "transcript", "alt", "img", "title", "day"
    )

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            try:
                self.__setattr__(name, value)
            except AttributeError:
                pass


class XKCD:
    def __init__(self, loop=asyncio.get_event_loop()):
        self.url_latest = "http://xkcd.com/info.0.json"
        self.url_number = "http://xkcd.com/{}/info.0.json"

        self.last_num = None

        self.req = Requester()
        self.loop = loop

        self.loop.run_until_complete(self._set_last_num())

    async def _set_last_num(self, multiply=1):
        c = await self.get_latest_xkcd()

        if c:
            self.last_num = int(c.num)
            log.info("Last comic number gotten: {}".format(self.last_num))
        else:
            log.warning("Could not get latest xkcd number! (retrying in {} min)".format(5 * multiply))
            # First retry is always 5 minutes, after that, 25 minutes
            await asyncio.sleep(60 * 5 * multiply)
            await self._set_last_num(multiply=5)

    async def get_latest_xkcd(self):
        try:
            data = await self.req.get_json(self.url_latest)
        except APIFailure:
            return None

        return Comic(**data)

    async def get_xkcd_by_number(self, num):
        try:
            data = await self.req.get_json(self.url_number.format(num))
        except APIFailure:
            return None

        return Comic(**data)

    async def get_random_xkcd(self):
        if not self.last_num:
            return await self.get_latest_xkcd()

        num = randint(1, self.last_num)

        return await self.get_xkcd_by_number(num)


class JokeGenerator:
    def __init__(self, loop=asyncio.get_event_loop()):
        self.yo_mama = "http://api.yomomma.info/"
        self.chuck = "https://api.chucknorris.io/jokes/random"

        self.req = Requester()

        self.cache = []

    async def get_random_cache(self):
        if self.cache:
            rand = randint(0, len(self.cache) - 1)
            return self.cache[rand]

    async def add_to_cache(self, joke):
        if not joke in self.cache:
            self.cache.append(joke)

    async def yomama_joke(self):
        joke = await self.req.get_json(self.yo_mama)

        if not joke:
            return None

        await self.add_to_cache(joke)
        return joke.get("joke")

    async def chuck_joke(self):
        joke = await self.req.get_json(self.chuck)

        if not joke:
            return None

        await self.add_to_cache(joke)
        return joke.get("value")

    async def get_joke(self, type_=randint(0, 2)):
        if type_ == 0:
            return await self.yomama_joke()
        elif type_ == 1:
            return await self.chuck_joke()

        else:
            if self.cache:
                return await self.get_random_cache()

            else:
                return await self.get_joke(randint(0, 1))


class Joke:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        try:
            self.cat = CatGenerator()
        except LookupError:
            raise RuntimeError

        self.xkcd = XKCD(self.loop)
        self.joke = JokeGenerator()

        assert isinstance(self.client, Client)

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)
        client = self.client

        prefix = kwargs.get("prefix")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*args):
            for a in args:
                if message.content.startswith(a):
                    return True

            return False

        # !cat gif/jpg/png
        if startswith(prefix + "cat"):
            args = str(message.content[len(prefix + "cat"):]).strip(" ")

            # GIF is the default type!
            type_ = "gif"
            if len(args) != 0:
                if args == "jpg":
                    type_ = "jpg"
                elif args == "png":
                    type_ = "png"

            pic = await self.cat.random_cat(type_)

            if not pic:
                await client.send_message(message.channel, "Could not get a random cat picture... " + StandardEmoji.CRY)
            else:
                await client.send_message(message.channel, pic)

            self.stats.add(IMAGE_SENT)

        # !xkcd random/number/latest
        elif startswith(prefix + "xkcd"):
            args = str(message.content[len(prefix + "xkcd"):]).strip(" ")

            # Decides mode
            fetch = "random"
            if len(args) != 0:
                if is_number(args):
                    # Check if number is valid
                    if int(args) > self.xkcd.last_num:
                        await client.send_message(message.channel, "Such XKCD number does not exist.")
                        return
                    else:
                        fetch = "number"
                else:
                    fetch = "latest"

            if fetch == "random":
                xkcd = await self.xkcd.get_random_xkcd()
            elif fetch == "number":
                xkcd = await self.xkcd.get_xkcd_by_number(args)
            else:
                xkcd = await self.xkcd.get_latest_xkcd()

            await client.send_message(message.channel, str(xkcd.img))

        # !joke (yo mama/chuck norris)
        elif startswith(prefix + "joke"):
            arg = str(message.content[len(prefix + "joke"):]).strip(" ")

            if arg.lower() == "yo mama":
                joke = await self.joke.get_joke(0)
            elif arg.lower() == "chuck norris":
                joke = await self.joke.get_joke(1)
            else:
                # Already random
                joke = await self.joke.get_joke()

            if not joke:
                await client.send_message(message.channel, "Could not get a proper joke... " + StandardEmoji.CRY)

            await client.send_message(message.channel, str(joke))


class NanoPlugin:
    name = "Joke-telling module"
    version = "0.1"

    handler = Joke
    events = {
        "on_message": 10
    }
