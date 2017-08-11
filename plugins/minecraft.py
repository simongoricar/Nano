# coding=utf-8
import logging
import os
from json import loads, JSONDecodeError

import aiohttp
from discord import Message, File

from data.stats import MESSAGE, WRONG_ARG, IMAGE_SENT
from data.utils import is_valid_command, is_number

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS
ITEM_ID_PAIR = 1
ITEM_ID = 2
ITEM_NAME = 3

commands = {
    "_mc": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]", "alias": None},
}

valid_commands = commands.keys()


class McItems:
    url = "http://minecraft-ids.grahamedgecombe.com/items.json"

    def __init__(self, loop):
        # Gets a fresh copy of items at each startup.
        self.data = None
        self.ids = {}
        self.names = {}

        loop.run_until_complete(self.request_data())

    async def request_data(self):
        log.info("Requesting JSON data from minecraft-ids.grahamedgecombe.com")
        async with aiohttp.ClientSession() as session:
            async with session.get(McItems.url) as resp:
                raw_data = await resp.text()

                try:
                    self.data = loads(raw_data)
                    await self._parse_items(self.data)
                except JSONDecodeError as e:
                    log.critical("Could not load JSON: {}".format(e))
                    raise RuntimeError

        log.info("Done")

    async def _parse_items(self, data):
        for item in data:
            idmeta_string = "{}:{}".format(item.get("type"), item.get("meta"))
            name_string = str(item.get("name")).lower()

            self.ids[idmeta_string] = item
            self.names[name_string] = item


    def find_by_id_meta(self, id_, meta):
        return self.ids.get("{}:{}".format(id_, meta))

    def find_by_name(self, name):
        return self.names.get(name)

    def group_to_list(self, group):
        items = []
        for item in self.data:
            if str(item.get("type")) == str(group):
                items.append(item)

        return items

    @staticmethod
    def get_picture_path_by_item(item):
        path = "plugins/mc/{}-{}.png".format(item.get("type"), item.get("meta"))
        if not os.path.isfile(path):
            return None
        else:
            return path

    def get_group_by_name(self, name):
        data = None

        # Group(ify)
        if str(name).lower() == "wool":
            data = self.group_to_list(35)
        elif str(name).lower() == "stone":
            data = self.group_to_list(1)
        elif str(name).lower() == "wood plank":
            data = self.group_to_list(5)
        elif str(name).lower() == "sapling":
            data = self.group_to_list(6)
        elif str(name).lower() == "sand":
            data = self.group_to_list(12)
        elif str(name).lower() == "wood":
            data = self.group_to_list(17)
        elif str(name).lower() == "leaves":
            data = self.group_to_list(18)
        elif str(name).lower() == "sponge":
            data = self.group_to_list(19)
        elif str(name).lower() == "sandstone":
            data = self.group_to_list(24)
        elif str(name).lower() == "flower":
            data = self.group_to_list(38)
        elif str(name).lower() == "double slab":
            data = self.group_to_list(43)
        elif str(name).lower() == "slab":
            data = self.group_to_list(44)
        elif str(name).lower() == "stained glass":
            data = self.group_to_list(95)
        elif str(name).lower() == "monster egg":
            data = self.group_to_list(97)
        elif str(name).lower() == "stone brick":
            data = self.group_to_list(98)
        elif str(name).lower() == "double wood slab":
            data = self.group_to_list(125)
        elif str(name).lower() == "wood slab":
            data = self.group_to_list(126)
        elif str(name).lower() == "quartz block":
            data = self.group_to_list(155)
        elif str(name).lower() == "stained clay":
            data = self.group_to_list(159)
        elif str(name).lower() == "stained glass pane":
            data = self.group_to_list(160)
        elif str(name).lower() == "prismarine":
            data = self.group_to_list(168)
        elif str(name).lower() == "carpet":
            data = self.group_to_list(171)
        elif str(name).lower() == "plant":
            data = self.group_to_list(175)
        elif str(name).lower() == "sandstone":
            data = self.group_to_list(179)
        elif str(name).lower() == "fish":
            data = self.group_to_list(349)
        elif str(name).lower() == "dye":
            data = self.group_to_list(351)
        elif str(name).lower() == "spawn egg":
            data = self.group_to_list(383)
        elif str(name).lower() == "head":
            data = self.group_to_list(397)

        return data


class Minecraft:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        self.mc = McItems(self.loop)

    async def on_message(self, message, **kwargs):
        trans = self.trans
        mc = self.mc

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(message, Message)

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix=prefix):
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
    version = "12"

    handler = Minecraft
    events = {
        "on_message": 10
        # type : importance
    }
