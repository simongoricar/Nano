# coding=utf-8
import requests
import time
import threading
from json import load

__author__ = "DefaltSimon"
__version__ = "0.1"

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

def get_quality_name(num):
    """
    Gets the quality name corresponding to the number
    :param num: int
    :return: str
    """
    return str(quality_names.get(int(num)))

# Decorator

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

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

            try:
                pr = d.get(list(d.keys())[0]).get(list(d.get(list(d.keys())[0]).keys())[0]) # Took me long enough :P
                pr = pr[0]
            except KeyError:
                pass

            det = {"tradable": d.get("Tradable") is not None,
                   "craftable": d.get(list(d.keys())[0]).get("Craftable") is not None,
                   "price": pr}
            return det

    def get_all_qualities(self):
        qualities = []
        for this in [STOCK, PROMOTIONAL, VINTAGE, EFFECT_OR_HALLOWEEN, UNIQUE, COMMUNITY, DEVELOPER, SELF_MADE, STRANGE, HAUNTED, COLLECTORS, DECORATED]:
            q = self.get_quality(this)
            if q:
                qualities.append({this: q})

        return qualities

# Main class

class CommunityPrices:
    """
    Community (backpack.tf) price parser.
    """
    def __init__(self, api_key, max_age=14400, allow_cache=True):
        """
        :param api_key: backpack.tf/developer key
        :param max_age: max cache age in s, if allow_cache is True (default)
        :param allow_cache: should CommunityPrices be allowed to use cache
        :return: None
        """
        self.api_key = api_key
        self.max_age = max_age  # Defaults to 4 hours

        self.dparams = {"key": api_key}
        self.address = "https://backpack.tf/api/IGetPrices/v4"

        if allow_cache:  # Should this be a feature? (todo)
            try:

                with open("cache/bptf_cache.temp", "r") as d:
                    data = load(d)

                    if (time.time() - int(data.get("current_time"))) > max_age:
                        # If cache is too old, request new cache
                        data = self._request()
                        self._write_temp(data)

            except FileNotFoundError:
                # If cached file does not exist, get new data and cache it.
                data = self._request()

                if not data.get("success") == 0:
                    self._write_temp(data)

        else:
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
            params = self.dparams

        resp = requests.get(address, params=params)

        return resp.json().get("response")

    @threaded
    def _update_cache(self, max_age=None):
        if not max_age: max_age = self.max_age
        self.__init__(self.api_key, max_age)

    def _write_temp(self, data):
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
        #print(self.cached_raw_items)
        #return self.cached_raw_items
        self._check_cache()

        if not self.cached_items:
            self.cached_items = [Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices")) for name in self.cached_raw_items]
        return self.cached_items

    def get_item_by_name(self, name):
        if not name:
            return

        self._check_cache()

        return Item(name, self.cached_raw_items.get(name).get("defindex"), self.cached_raw_items.get(name).get("prices"))


#import configparser
#parser = configparser.ConfigParser()
#parser.read("settings.ini")
#
#bptf = CommunityPrices(parser.get("Credentials", "apikey"))
#
#prof = bptf.get_item_by_name("Sydney Sleeper")
#
#print(prof.get_all_qualities())