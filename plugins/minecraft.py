# coding=utf-8
import logging
import os
import time

try:
    from rapidjson import loads
except ImportError:
    from json import loads

from json import JSONDecodeError

import aiohttp
from discord import File

from core.stats import MESSAGE, WRONG_ARG, IMAGE_SENT
from core.utils import is_valid_command, is_number
from core.confparser import PLUGINS_DIR

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS
ITEM_ID_PAIR = 1
ITEM_ID = 2
ITEM_NAME = 3

commands = {
    "_mc": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]"},
}

valid_commands = commands.keys()


class McItems:
    """
    Data layout:
        raw_data: json
        last_fetch: float (epoch time)

        hash:
            <id:meta>: dict(info)
    """
    url = "http://minecraft-ids.grahamedgecombe.com/items.json"

    def __init__(self, handler, loop):
        # Gets a fresh copy of items at each startup.
        self.ids = {}
        self.by_type = {}
        self.names = {}

        MAX_AGE = 604800  # 1 week

        cache_temp = handler.get_cache_handler()
        self.cache = cache_temp.get_plugin_data_manager("mc")

        # Check validity of cache
        if self.cache.exists("raw_data") and (time.time() - float(self.cache.get("last_fetch"))) < MAX_AGE:
            log.info("Valid minecraft data found in DB.")
            data = loads(self.cache.get("raw_data"))
            loop.create_task(self._parse(data))

        else:
            # Fetch and parse data
            log.info("No cache found.")
            loop.create_task(self.request_data())

    async def request_data(self):
        log.info("Requesting JSON data from minecraft-ids.grahamedgecombe.com")
        async with aiohttp.ClientSession() as session:
            async with session.get(McItems.url) as resp:
                raw_data = await resp.text()

                try:
                    self.cache.set("raw_data", raw_data)
                    self.cache.set("last_fetch", time.time())
                    log.info("New mc dataset in cache")

                    data = loads(raw_data)
                    await self._parse(data)
                except JSONDecodeError as e:
                    log.critical("Could not load JSON: {}".format(e))
                    raise RuntimeError

        log.info("Done")

    async def _parse(self, data):
        for item in data:
            idmeta_string = "{}:{}".format(item["type"], item["meta"])
            name_string = str(item.get("name")).lower()

            self.ids[idmeta_string] = item
            self.names[name_string] = item

            if self.by_type.get(item["type"]):
                self.by_type[int(item["type"])].append(item)
            else:
                self.by_type[int(item["type"])] = [item]

    def find_by_id_meta(self, id_, meta):
        return self.ids.get("{}:{}".format(id_, meta))

    def find_by_name(self, name):
        return self.names.get(name)

    def group_to_list(self, group):
        return self.by_type.get(int(group)) or []

    @staticmethod
    def get_picture_path_by_item(item):
        path = "{}/mc/{}-{}.png".format(PLUGINS_DIR, item.get("type"), item.get("meta"))
        if not os.path.isfile(path):
            return None
        else:
            return path

    def get_group_by_name(self, name):
        # Group(ify)
        if str(name).lower() == "wool":
            return self.group_to_list(35)
        elif str(name).lower() == "stone":
            return self.group_to_list(1)
        elif str(name).lower() == "wood plank":
            return self.group_to_list(5)
        elif str(name).lower() == "sapling":
            return self.group_to_list(6)
        elif str(name).lower() == "sand":
            return self.group_to_list(12)
        elif str(name).lower() == "wood":
            return self.group_to_list(17)
        elif str(name).lower() == "leaves":
            return self.group_to_list(18)
        elif str(name).lower() == "sponge":
            return self.group_to_list(19)
        elif str(name).lower() == "sandstone":
            return self.group_to_list(24)
        elif str(name).lower() == "flower":
            return self.group_to_list(38)
        elif str(name).lower() == "double slab":
            return self.group_to_list(43)
        elif str(name).lower() == "slab":
            return self.group_to_list(44)
        elif str(name).lower() == "stained glass":
            return self.group_to_list(95)
        elif str(name).lower() == "monster egg":
            return self.group_to_list(97)
        elif str(name).lower() == "stone brick":
            return self.group_to_list(98)
        elif str(name).lower() == "double wood slab":
            return self.group_to_list(125)
        elif str(name).lower() == "wood slab":
            return self.group_to_list(126)
        elif str(name).lower() == "quartz block":
            return self.group_to_list(155)
        elif str(name).lower() == "stained clay":
            return self.group_to_list(159)
        elif str(name).lower() == "stained glass pane":
            return self.group_to_list(160)
        elif str(name).lower() == "prismarine":
            return self.group_to_list(168)
        elif str(name).lower() == "carpet":
            return self.group_to_list(171)
        elif str(name).lower() == "plant":
            return self.group_to_list(175)
        elif str(name).lower() == "sandstone":
            return self.group_to_list(179)
        elif str(name).lower() == "fish":
            return self.group_to_list(349)
        elif str(name).lower() == "dye":
            return self.group_to_list(351)
        elif str(name).lower() == "spawn egg":
            return self.group_to_list(383)
        elif str(name).lower() == "head":
            return self.group_to_list(397)

        else:
            return []


class Minecraft:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        self.mc = McItems(self.handler, self.loop)

    async def on_message(self, message, **kwargs):
        trans = self.trans
        mc = self.mc

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # !mc
        if startswith(prefix + "mc"):
            argument = message.content[len(prefix + "mc "):].strip(" ").lower()

            if not argument:
                await message.channel.send(trans.get("MSG_MC_PLSARUGMENTS", lang))
                return

            # !mc help
            if argument == "help":
                await message.channel.send(trans.get("MSG_MC_HELP", lang).replace("_", prefix))
                return

            # Argument is name
            if not is_number(argument.split(":")[0]):
                # Check for groupings
                gr = mc.get_group_by_name(argument)
                if gr:
                    data = gr
                # Not a group
                else:
                    data = mc.find_by_name(str(argument))

            # Argument is id and meta
            else:
                try:
                    i_type, i_meta = argument.split(":")
                except ValueError:
                    i_type, i_meta = argument, 0

                data = mc.find_by_id_meta(i_type, i_meta)

            if not data:
                await message.channel.send(trans.get("MSG_MC_NO_ITEMS", lang))
                self.stats.add(WRONG_ARG)
                return

            # One item, not a group
            if not isinstance(data, list):
                details = trans.get("MSG_MC_DETAILS", lang).format(data.get("name"), data.get("type"), data.get("meta"))

                # Details are uploaded simultaneously with the picture

                # No image
                path = mc.get_picture_path_by_item(data)
                if not path:
                    await message.channel.send(details)
                    self.stats.add(IMAGE_SENT)
                else:
                    with open(mc.get_picture_path_by_item(data), "rb") as pic:
                        await message.channel.send(details, file=File(pic))
                        self.stats.add(IMAGE_SENT)

            # Multiple items, a group
            else:
                combined = []
                for item in data:
                    details = trans.get("MSG_MC_DETAILS", lang).format(item.get("name"), item.get("type"), item.get("meta"))
                    combined.append(details)

                await message.channel.send("".join(combined))


class NanoPlugin:
    name = "Minecraft Commands"
    version = "14"

    handler = Minecraft
    events = {
        "on_message": 10
        # type : importance
    }
