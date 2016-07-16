# coding=utf-8

"""Part of AyyBot"""

from yaml import load,dump
import os

# Pretty much like v1, but with small changes

__author__ = "DefaltSimon"

class BotStats:
    def __init__(self):
        pass

    def write(self,data):
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(data,default_flow_style=False))

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