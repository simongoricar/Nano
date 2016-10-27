# coding=utf-8
# coding=utf-8
import requests
import time
import logging
import configparser
from json import load
from discord import Message
from data.utils import threaded, is_valid_command
from data.stats import MESSAGE

__author__ = "DefaltSimon"
# Backpack.tf price plugin for Nano

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

valid_commands = [
    "_tf"
]


def get_quality_name(num):
    """
    Gets the quality name corresponding to the number
    :param num: int
    :return: str
    """
    return str(quality_names.get(int(num)))


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

            pr = d.get(list(d.keys())[0]).get(list(d.get(list(d.keys())[0]).keys())[0]) # Took me long enough :P

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
    def __init__(self, api_key, max_age=14400, allow_cache=True):
        """
        :param api_key: backpack.tf/developer key
        :param max_age: max cache age in s, if allow_local_cache is True (default)
        :param allow_cache: should CommunityPrices be allowed to use cache
        :return: None
        """
        self.api_key = api_key
        self.max_age = max_age  # Defaults to 4 hours

        self.parameters = {"key": api_key}
        self.address = "https://backpack.tf/api/IGetPrices/v4"

        if allow_cache:  # Should this be a feature? (todo)
            try:

                with open("cache/bptf_cache.temp", "r") as d:
                    data = load(d)

                    if (time.time() - int(data.get("current_time"))) > max_age:
                        # If cache is too old, request new cache
                        logger.info("Downloading prices from backpack.tf/api")
                        data = self._request()
                        self._write_temp(data)
                    else:
                        logger.info("Using cache")

            except FileNotFoundError:
                # If cached file does not exist, get new data and cache it.
                data = self._request()

                if not data.get("success") == 0:
                    self._write_temp(data)

        else:
            logger.info("Downloading prices from backpack.tf/api")
            data = self._request()

        if data.get("success") == 0:
            raise ApiError(data.get("message"))

        self.cache_timestamp = data.get("current_time")
        self.cached_raw_currency = data.get("raw_usd_value")
        self.cached_raw_items = data.get("items")

        self.cached_items = []

        self.currency = {"name": data.get("usd_currency"),
                         "index": data.get("usd_currency_index")}

        if not self.cached_raw_items:
            raise ApiError("No items in response.")

    def _request(self, address=None, params=None):
        if not address:
            address = self.address

        if not params:
            params = self.parameters

        resp = requests.get(address, params=params)

        return resp.json().get("response")

    @threaded
    def _update_cache(self, max_age=None):
        if not max_age: max_age = self.max_age
        self.__init__(self.api_key, max_age)

    @staticmethod
    def _write_temp(data):
        from json import dump
        import os

        if not os.path.isdir("cache"):
            os.mkdir("cache")

        dump(data, open("cache/bptf_cache.temp", "w"))

    def _check_cache(self):
        if (time.time() - self.cache_timestamp) > self.max_age:
            self._update_cache()

    def get_item_list(self):
        """
        Gets all items on backpack.tf
        :return: A list of un
        """
        self._check_cache()

        if not self.cached_items:
            self.cached_items = [Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices")) for name in self.cached_raw_items]
        return self.cached_items

    def get_item_by_name(self, name):
        if not name:
            return

        self._check_cache()

        try:
            return Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices"))
        except AttributeError:
            return None


class TeamFortress:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        self.tf = CommunityPrices(api_key=parser.get("backpack.tf", "apikey"))

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

        if startswith(prefix + "tf"):
            item_name = message.content[len(prefix + "tf "):]

            item = self.tf.get_item_by_name(str(item_name))

            if not item:
                await client.send_message(message.channel, "An item with that name *does not exist*.".format(item_name))
                # stat.pluswrongarg()
                return

            ls = []
            for qu in item.get_all_qualities():
                down = qu.get(list(qu.keys())[0])
                dt = "__**{}**__: `{} {}`".format(get_quality_name(list(qu.keys())[0]),
                                                  down.get("price").get("value"),
                                                  "ref" if down.get("price").get("currency") == "metal" else down.get(
                                                      "price").get("currency"))
                ls.append(dt)

            det = """**{}** *(on bp.tf)*\n\n{}""".format(item.name, "\n".join(ls))
            await client.send_message(message.channel, det)


class NanoPlugin:
    _name = "Team Fortress 2"
    _version = 0.1

    handler = TeamFortress
    events = {
        "on_message": 10
        # type : importance
    }
