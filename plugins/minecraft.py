# coding=utf-8

__author__ = "DefaltSimon"

# Minecraft plugin for Nano

import requests
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Exception class

class MinecraftException(Exception):
    def __init__(self, *args, **kwargs):
        pass

# Main class

class Minecraft:
    def __init__(self):
        # Gets a fresh copy of items at each startup.
        log.info("Requesting JSON data from minecraft-ids")
        jsondata = requests.get("http://minecraft-ids.grahamedgecombe.com/items.json")
        self.data = jsondata.json()

    def id_to_data(self, num):
        if len(str(num).split(":")) > 1:
            idd = str(num).split(":")[0]
            meta = str(num).split(":")[1]
        else:
            idd = num
            meta = 0

        for item in self.data:
            if int(item.get("type")) == int(idd):
                if int(item.get("meta")) == int(meta):
                    return item

    def name_to_data(self, name):
        for c, item in enumerate(self.data):
            if item.get("name").lower() == str(name).lower():
                return self.data[c]

    def group_to_list(self, group):
        items = []
        for item in self.data:
            if str(item.get("type")) == str(group):
                items.append(item)

        return items

    def _items_to_list(self, **kwargs):
        # Private for now, todo
        items = []
        for item in self.data:
            if kwargs.get(str(item.get("type"))) is not None:
                pass

    def id_to_pic(self, num):
        if num > len(self.data):
            raise MinecraftException

        data = self.data[num]

        with open("plugins/mc_item_png/{}-{}.png".format(num, data.get("metadata"))) as pic:
            return pic