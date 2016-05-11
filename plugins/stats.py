"""Part of AyyBot"""

from yaml import load,dump
import os

__author__ = "DefaltSimon"

class BotStats:
    def __init__(self):
        pass
    def plusmsg(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["msgcount"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def sizeofdown(self):
        size = sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f))
        return size
    def pluswrongarg(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["wrongargcount"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plusleftserver(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["serversleft"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plusslept(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["timesslept"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def pluswrongperms(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["wrongpermscount"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plushelpcommand(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["peoplehelped"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plusimagesent(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["imagessent"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plusonevote(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["votesgot"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))
    def plusoneping(self):
        with open("plugins/stats.yml","r+") as file:
            file = load(file)
            file["timespinged"] += 1
        with open("plugins/stats.yml","w") as outfile:
            outfile.write(dump(file,default_flow_style=False))