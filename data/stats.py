# coding=utf-8
import time
import logging
from yaml import load, dump
from .utils import threaded

__author__ = "DefaltSimon"
# Stats handler for Nano

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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


class NanoStats:
    def __init__(self):
        log.info("Enabled")
        self.data_lock = False

        with open("data/stats.yml", "r") as file:
            self.cached_data = load(file)

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
            outfile.write(dump(self.cached_data, default_flow_style=False))

        self.release_lock()

    def get_data(self):
        return self.cached_data

    def _reload_data(self):
        log.info("Reloading stats from file")
        with open("data/stats.yml", "r") as file:
            self.cached_data = load(file)

    def get_amount(self, typ):
        return self.cached_data.get(typ)

    # The code efficiency is getting real
    def add(self, stat_type):
        if stat_type in [MESSAGE, WRONG_ARG, SERVER_LEFT, SLEPT, WRONG_PERMS, HELP, IMAGE_SENT, VOTE, PING, SUPPRESS, DOWNLOAD, PRAYER]:

            self.cached_data[stat_type] += 1

            self.write()
