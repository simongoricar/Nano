# coding=utf-8
import time
import os
import importlib
import configparser
import logging
# yaml is now a conditional import
from .utils import threaded, decode, decode_auto

__author__ = "DefaltSimon"
# Stats handler for Nano

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

par = configparser.ConfigParser()
par.read("settings.ini")

# CONSTANTS

MESSAGE = "msgcount"
WRONG_ARG = "wrongargcount"
SERVER_LEFT = "serversleft"
SLEPT = "timesslept"
WRONG_PERMS = "wrongpermscount"
HELP = "peoplehelped"
IMAGE_SENT = "imagessent"
VOTE = "votesgot"
PING = "timespinged"
SUPPRESS = "messagessuppressed"
DOWNLOAD = "imagesize"
PRAYER = "prayerssaid"

stat_types = [MESSAGE, WRONG_ARG, SERVER_LEFT, SLEPT, WRONG_PERMS, HELP, IMAGE_SENT, VOTE, PING, SUPPRESS, DOWNLOAD, PRAYER]


def get_NanoStats(legacy=False):
    if legacy:
        return LegacyNanoStats()
    else:
        setup_type = 1 if par.get("Redis", "setup") == "openshift" else 2

        if setup_type == 1:
            redis_ip = os.environ["OPENSHIFT_REDIS_HOST"]
            redis_port = os.environ["OPENSHIFT_REDIS_PORT"]
            redis_pass = os.environ["REDIS_PASSWORD"]

        else:
            redis_ip = par.get("Redis", "ip")
            redis_port = par.get("Redis", "port")
            redis_pass = par.get("Redis", "password")

            # Fallback to defaults
            if not redis_ip:
                redis_ip = "localhost"
            if not redis_port:
                redis_port = 6379
            if not redis_pass:
                redis_pass = None

        return RedisNanoStats(redis_ip, redis_port, redis_pass)


# Regarding RedisNanoStats
# Stats are saved in a hash => stats


class RedisNanoStats:
    __slots__ = (
        "_redis", "redis"
    )

    def __init__(self, redis_ip, redis_port, redis_pass):
        self._redis = importlib.import_module("redis")
        self.redis = self._redis.StrictRedis(host=redis_ip, port=redis_port, password=redis_pass)

        try:
            self.redis.ping()
        except self._redis.ConnectionError:
            log.critical("Could not connect to Redis db!")
            return

        # Set up the hash if it does not exist
        if not decode(self.redis.exists("stats")):
            types = {typ: 0 for typ in stat_types}
            self.redis.hmset("stats", types)

            log.info("Enabled: hash 'stats' created")

        else:
            log.info("Enabled: hash found")

    def add(self, stat_type):
        if stat_type in stat_types:
            self.redis.hincrby("stats", stat_type, 1)

    def get_data(self):
        return decode(self.redis.hgetall("stats"))

    def get_amount(self, typ):
        if typ in stat_types:
            return decode(self.redis.hget("stats", typ))
        else:
            return 0

    def _set_amount(self, stat_type: str, amount: int):
        if stat_type in stat_types:
            self.redis.hset("stats", stat_type, amount)


class LegacyNanoStats:
    def __init__(self):
        self.yaml = importlib.import_module("yaml")

        log.info("Enabled: legacy")
        self.data_lock = False

        with open("data/stats.yml", "r") as file:
            self.cached_data = self.load(file)

    def load(self, *args, **kwargs):
        return self.yaml.load(*args, **kwargs)

    def dump(self, *args, **kwargs):
        return self.yaml.dump(*args, **kwargs)

    # The locking system
    def lock(self):
        self.data_lock = True

    def wait_until_release(self):
        while self.data_lock is True:
            time.sleep(0.05)

        return

    def release_lock(self):
        self.data_lock = False

    @threaded
    def write(self):
        # Prevents data corruption
        self.wait_until_release()

        self.lock()
        with open("data/stats.yml", "w") as outfile:
            outfile.write(self.dump(self.cached_data, default_flow_style=False))

        self.release_lock()

    def get_data(self):
        return self.cached_data

    def _reload_data(self):
        log.info("Reloading stats from file")
        with open("data/stats.yml", "r") as file:
            self.cached_data = self.load(file)

    def get_amount(self, typ):
        return self.cached_data.get(typ)

    # The code efficiency is getting real
    def add(self, stat_type):
        if stat_type in [MESSAGE, WRONG_ARG, SERVER_LEFT, SLEPT, WRONG_PERMS, HELP, IMAGE_SENT, VOTE, PING, SUPPRESS, DOWNLOAD, PRAYER]:

            self.cached_data[stat_type] += 1

            self.write()
