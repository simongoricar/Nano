# coding=utf-8

"""Part of Nano"""

import os
import time
import logging
from yaml import load, dump

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Pretty much like v1, but with small changes

__author__ = "DefaltSimon"

class BotStats:
    def __init__(self):
        log.info("Enabled")
        self.data_lock = False

    def lock(self):
        self.data_lock = True

    def wait_until_release(self):
        while self.data_lock is True:
            time.sleep(0.05)

        return

    def release_lock(self):
        self.data_lock = False

    def write(self,data):
        # Prevents data corruption
        self.wait_until_release()

        self.lock()
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(data,default_flow_style=False))
        self.release_lock()

    def plusmsg(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["msgcount"] += 1
        self.write(file)

    @staticmethod
    def sizeofdown():
        size = sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f))
        return size

    def pluswrongarg(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["wrongargcount"] += 1
        self.write(file)

    def plusleftserver(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["serversleft"] += 1
        self.write(file)

    def plusslept(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["timesslept"] += 1
        self.write(file)

    def pluswrongperms(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["wrongpermscount"] += 1
        self.write(file)

    def plushelpcommand(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["peoplehelped"] += 1
        self.write(file)

    def plusimagesent(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["imagessent"] += 1
        self.write(file)

    def plusonevote(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["votesgot"] += 1
        self.write(file)

    def plusoneping(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["timespinged"] += 1
        self.write(file)

    def plusonesupress(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["messagessuppressed"] += 1
        self.write(file)

    def plus_download(self, size):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["imagesize"] += size
        self.write(file)