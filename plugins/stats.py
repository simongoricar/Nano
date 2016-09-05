# coding=utf-8

import os
import time
import logging
import threading
from yaml import load, dump

__author__ = "DefaltSimon"
# Stats plugin for Nano

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Decorator


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

# Pretty much like v1, but with small changes


class BotStats:
    def __init__(self):
        log.info("Enabled")
        self.data_lock = False

        with open("plugins/stats.yml", "r") as file:
            self.cached_data = load(file)

    def lock(self):
        self.data_lock = True

    def wait_until_release(self):
        while self.data_lock is True:
            time.sleep(0.05)

        return

    def release_lock(self):
        self.data_lock = False

    @threaded
    def write(self, data):
        # Prevents data corruption
        self.wait_until_release()

        self.cached_data = data.copy()

        self.lock()
        with open("plugins/stats.yml", "w") as outfile:
            outfile.write(dump(data, default_flow_style=False))
        self.release_lock()

    def get_data(self):
        return self.cached_data

    def _reload_data(self):
        log.info("Reloading stats from file")
        with open("plugins/stats.yml", "r") as file:
            self.cached_data = load(file)

    def plusmsg(self):
        data = self.get_data()

        data["msgcount"] += 1
        self.write(data)

    @staticmethod
    def sizeofdown():
        size = sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f))
        return size

    def pluswrongarg(self):
        data = self.get_data()

        data["wrongargcount"] += 1
        self.write(data)

    def plusleftserver(self):
        data = self.get_data()

        data["serversleft"] += 1
        self.write(data)

    def plusslept(self):
        data = self.get_data()

        data["timesslept"] += 1
        self.write(data)

    def pluswrongperms(self):
        data = self.get_data()

        data["wrongpermscount"] += 1
        self.write(data)

    def plushelpcommand(self):
        data = self.get_data()

        data["peoplehelped"] += 1
        self.write(data)

    def plusimagesent(self):
        data = self.get_data()

        data["imagessent"] += 1
        self.write(data)

    def plusonevote(self):
        data = self.get_data()

        data["votesgot"] += 1
        self.write(data)

    def plusoneping(self):
        data = self.get_data()

        data["timespinged"] += 1
        self.write(data)

    def plusonesupress(self):
        data = self.get_data()

        data["messagessuppressed"] += 1
        self.write(data)

    def plus_download(self, size):
        data = self.get_data()

        data["imagesize"] += size
        self.write(data)
