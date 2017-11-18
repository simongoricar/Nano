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
    __slots__ = (
        "_redis", "redis"
    )

    def __init__(self, redis_ip, redis_port, redis_pass):
        # TODO make request buffering (~5s)
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

    @classmethod
    def from_settings(cls) -> "NanoStats":
        setup_type = par.get("Redis", "setup", fallback=None)

        if setup_type == "openshift":
            redis_ip = os.environ["OPENSHIFT_REDIS_HOST"]
            redis_port = os.environ["OPENSHIFT_REDIS_PORT"]
            redis_pass = os.environ["REDIS_PASSWORD"]

        else:
            redis_ip = par.get("Redis", "ip", fallback=None)
            redis_port = par.get("Redis", "port", fallback=None)
            redis_pass = par.get("Redis", "password", fallback=None)

            # Fallback to defaults
            if not redis_ip:
                redis_ip = "localhost"
            if not redis_port:
                redis_port = 6379
            if not redis_pass:
                redis_pass = None

        return NanoStats(redis_ip, redis_port, redis_pass)

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
