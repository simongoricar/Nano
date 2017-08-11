# coding=utf-8
import asyncio
import configparser
import logging
import os
import time

from ujson import load, dump, loads

import aiohttp

from data.stats import MESSAGE, WRONG_ARG
from data.utils import is_valid_command

#####
# TF2 plugin
# Uses API by backpack.tf
#####

logger = logging.getLogger(__name__)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

# Constants

STOCK = 0
PROMOTIONAL = 1
VINTAGE = 3
EFFECT_OR_HALLOWEEN = 5
UNIQUE = 6
COMMUNITY = 7
DEVELOPER = 8
SELF_MADE = 9
STRANGE = 11
HAUNTED = 13
COLLECTORS = 14
DECORATED = 15

quality_names = {0: "Stock",
                 1: "Promotional",
                 3: "Vintage",
                 5: "Effect/Halloween",
                 6: "Unique",
                 7: "Community",
                 8: "Developer",
                 9: "Self-made",
                 11: "Strange",
                 13: "Haunted",
                 14: "Collector's",
                 15: "Decorated"}

commands = {
    "_tf": {"desc": "Gets item prices from backpack.tf (not perfect for items with unusual effects/sheens)", "use": "[command] [item name]", "alias": None},
}

valid_commands = commands.keys()


def get_quality_name(num):
    """
    Gets the quality name corresponding to the number
    :param num: int
    :return: str
    """
    return quality_names.get(int(num))


# Exception classes

class ApiError(Exception):
    """
    Raised when something goes wrong when connecting to the api.
    """
    pass


class InvalidQuality(Exception):
    """
    Raised when specifying a non-existent quality (int).
    """
    pass

# Item object


class Item(object):
    """
    Item in the game.
    """
    def __init__(self, name, defindex, prices):
        self.name = str(name)
        self.defindex = defindex
        self._prices = prices

    def __len__(self):
        """
        Represents amount of qualities.
        :return: int
        """
        return len(self._prices)

    def __eq__(self, other):
        try:
            return self.name == other.name
        except AttributeError:
            return False

    def has_quality(self, quality):
        """
        Indicates if the item has the specified quality.
        :param quality: one of stock, promotional, ...
        :return: bool
        """
        if quality not in quality_names.keys():
            raise InvalidQuality

        return int(quality) in [int(key) for key in self._prices.keys()]

    def get_quality(self, quality):
        """
        Gets details on the specified quality if it exists.
        :param quality: one of stock, promotional, ...
        :return: dict with details
        """
        if not self.has_quality(quality):
            return None
        else:

            d = self._prices.get(str(quality))

            # Took me long enough :P
            # Tradable/Non-Tradable -> Craftable/Non-Craftable -> Priceindex
            pr = d.get(list(d.keys())[0]).get(list(d.get(list(d.keys())[0]).keys())[0])

            try:
                pr = pr[0]
            except KeyError:
                pass

            det = {"tradable": d.get("Tradable") is not None,
                   "craftable": d.get(list(d.keys())[0]).get("Craftable") is not None,
                   "price": pr}
            return det

    def get_all_qualities(self):
        qualities = []
        for this in [STOCK, PROMOTIONAL, VINTAGE, EFFECT_OR_HALLOWEEN, UNIQUE, COMMUNITY,
                     DEVELOPER, SELF_MADE, STRANGE, HAUNTED, COLLECTORS, DECORATED]:

            q = self.get_quality(this)
            if q:
                qualities.append({this: q})

        return qualities

# bp.tf class


class CommunityPrices:
    """
    Community (backpack.tf) price parser.
    """
    def __init__(self, loop, api_key, max_age=2880, allow_cache=True):
        """
        :param api_key: backpack.tf/developer key
        :param max_age: max cache age in s, if allow_local_cache is True (default)
        :param allow_cache: should CommunityPrices be allowed to use cache
        :return: None
        """
        self.api_key = api_key
        self.max_age = max_age  # Defaults to 8 hours
        self.success = None

        self.loop = loop

        self.is_updating = True
        self.allow_cache = allow_cache

        self.parameters = {"key": api_key}
        self.address = "https://backpack.tf/api/IGetPrices/v4"

        self.cached_items = None

        # One for read, one for write
        loop.create_task(self.download_data(allow_cache, allow_cache))

    async def download_data(self, cache_read=True, cache_write=True):
        if await self._download_data(cache_read, cache_write) is False:
            logger.warning("Error white getting TF2 data. Plugin disabled.")
            self.success = False
        else:
            logger.info("Successfully got TF2 item data")
            self.success = True

        self.is_updating = False

    async def _download_data(self, cache_read=True, cache_write=True):
        # Read from cache if permitted and it exists
        if cache_read and os.path.isfile("cache/bptf_cache.temp"):
            with open("cache/bptf_cache.temp") as cache:
                try:
                    data = load(cache)

                # Malformed json data
                except:
                    data = await self._request()

                # Everything is fine, validate data
                else:
                    if not data:
                        return False

                    # Checks cache age
                    if (time.time() - int(data.get("current_time"))) > self.max_age:
                        data = await self._request()
                    else:
                        logger.info("Using cache")
                if not data:
                    return False

        # Otherwise just normally request it
        else:
            data = await self._request()
            if not data:
                return False

        # Check data validity
        if data.get("success") == 0:
            raise ApiError(data.get("message"))

        # Write to cache if permitted
        if cache_write:
            self._write_temp(data)

        self.cache_timestamp = data.get("current_time")
        self.cached_raw_currency = data.get("raw_usd_value")
        self.cached_raw_items = data.get("items")

        self.cached_items = []

        self.currency = {"name": data.get("usd_currency"),
                         "index": data.get("usd_currency_index")}

        if not self.cached_raw_items:
            raise ApiError("No items in response.")

        self.is_updating = False
        return True

    async def _request(self, address=None, params=None):
        logger.info("Downloading prices...")

        if not address:
            address = self.address
        if not params:
            params = self.parameters

        async with aiohttp.ClientSession(json_serialize=loads) as session:
            async with session.get(address, params=params) as resp:
                if resp.status != 200:
                    if resp.status == 504:
                        logger.warning("Got 504: Gateway Timeout, retrying in 5 min")
                        await asyncio.sleep(60*5)
                        await self._download_data()

                    elif resp.status == 429:
                        logger.warning("Got 429: Too Many Requests - retrying in 120 s")
                        await asyncio.sleep(60*2)
                        await self._download_data()

                    else:
                        logger.warning("Got {} in response".format(resp.status))

                    return None
                else:
                    return (await resp.json()).get("response")

    async def _update_cache(self):
        if not self.is_updating:
            self.is_updating = True
            await self.download_data(self.allow_cache, self.allow_cache)

    @staticmethod
    def _write_temp(data):
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        dump(data, open("cache/bptf_cache.temp", "w"))

    async def _check_cache(self):
        if (time.time() - self.cache_timestamp) > self.max_age:
            await self._update_cache()

    async def get_item_list(self):
        """
        Gets all items on backpack.tf
        :return: A list of un
        """
        await self._check_cache()

        if not self.cached_items:
            self.cached_items = [Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices")) for name in self.cached_raw_items]
        return self.cached_items

    async def get_item_by_name(self, name):
        if not name:
            return None

        await self._check_cache()

        try:
            return Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices"))
        except AttributeError:
            return None


class TeamFortress:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        try:
            key = parser.get("backpack.tf", "apikey")
            if not key:
                raise configparser.NoOptionError

            self.tf = CommunityPrices(self.loop, api_key=key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.critical("No api key for bp.tf, disabling")
            raise RuntimeError

    async def on_message(self, message, **kwargs):
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

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

        # !tf [item name]
        if startswith(prefix + "tf"):
            if not self.tf.success:
                await message.channel.send(trans.get("MSG_TF_UNAVAILABLE", lang))
                return

            item_name = message.content[len(prefix + "tf "):]
            if not item_name:
                await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            item = await self.tf.get_item_by_name(str(item_name))
            if not item:
                await message.channel.send(trans.get("MSG_TF_NO_SUCH_ITEM", lang).format(item_name))
                self.stats.add(WRONG_ARG)
                return

            ls = []
            for qu in item.get_all_qualities():
                v_data = qu.get(list(qu.keys())[0])
                quality = get_quality_name(list(qu.keys())[0])
                currency = "ref" if v_data.get("price").get("currency") == "metal" else v_data.get("price").get("currency")

                ls.append("__**{}**__: `{} {}`".format(quality, v_data.get("price").get("value"), currency))

            det = trans.get("MSG_TF_LIST", lang).format(item.name, "\n".join(ls))
            await message.channel.send(det)


class NanoPlugin:
    name = "Team Fortress 2"
    version = "18"

    handler = TeamFortress
    events = {
        "on_message": 10
        # type : importance
    }
