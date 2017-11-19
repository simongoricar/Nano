# coding=utf-8
import os
import configparser
import logging
import redis
from .utils import decode

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


# Regarding NanoStats
# Stats are saved in a hash => stats


class NanoStats:
    __slots__ = ("_redis", "redis", "_pending_data", "MAX_BEFORE_UPDATE")

    def __init__(self, redis_ip, redis_port, redis_pass):
        self.redis = redis.StrictRedis(host=redis_ip, port=redis_port, password=redis_pass)

        try:
            self.redis.ping()
        except redis.ConnectionError:
            raise ConnectionError("Could not connect to Redis db!")

        # Set up the hash if it does not exist
        if not decode(self.redis.exists("stats")):
            types = {typ: 0 for typ in stat_types}
            self.redis.hmset("stats", types)

            log.info("Enabled: stats initialized")

        else:
            log.info("Enabled: stats found")

        self._pending_data = {a: 0 for a in stat_types}
        self.MAX_BEFORE_UPDATE = 5

    def add(self, stat_type):
        if stat_type not in stat_types:
            return False

        self._pending_data[stat_type] += 1

        value = self._pending_data[stat_type]
        if value >= self.MAX_BEFORE_UPDATE:
            log.info("Reached max size, posting to redis...")
            # Send data and reset the pending counter
            self.redis.hincrby("stats", stat_type, value)
            self._pending_data[stat_type] = 0

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
