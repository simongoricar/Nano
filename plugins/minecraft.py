# coding=utf-8
import requests
import logging
from discord import Client, Message
from data.stats import MESSAGE
from data.utils import is_valid_command

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS
ITEM_ID_PAIR = 1
ITEM_ID = 2
ITEM_NAME = 3

commands = {
    "_mc": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]", "alias": "_minecraft"},
    "_minecraft": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]", "alias": "_mc"},
}

valid_commands = commands.keys()


class McItems:
    def __init__(self):
        # Gets a fresh copy of items at each startup.
        log.info("Requesting JSON data from minecraft-ids")
        json_data = requests.get("http://minecraft-ids.grahamedgecombe.com/items.json")
        self.data = json_data.json()

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
        # Not used,
        # Private for now, /todo cant find a use for this
        items = []
        for item in self.data:
            if kwargs.get(str(item.get("type"))) is not None:
                pass

    def id_to_pic(self, num):
        if num > len(self.data):
            return None

        data = self.data[num]

        with open("plugins/mc/{}-{}.png".format(num, data.get("metadata"))) as pic:
            return pic

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
        elif str(name).lower() == "egg":
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

        self.mc = McItems()

    async def on_message(self, message, **kwargs):
        prefix = kwargs.get("prefix")
        client = self.client
        mc = self.mc

        assert isinstance(client, Client)
        assert isinstance(message, Message)

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "mc", prefix + "minecraft"):
            if startswith(prefix + "mc help", prefix + "minecraft help"):
                # Help message
                await client.send_message(message.channel,
                                          "**Minecraft**\n```css\n"
                                          "_mc name/id:meta - search for items and display their details```".replace("_", prefix))
                return

            elif startswith(prefix + "mc "):
                da = message.content[len(prefix + "mc "):]
            elif startswith(prefix + "minecraft "):
                da = message.content[len(prefix + "minecraft "):]

            else:
                return

            # Determines if arg is id or name
            if len(str(da).split(":")) > 1:
                typ = ITEM_ID_PAIR

            else:
                try:
                    int(da)
                    typ = ITEM_ID
                except ValueError:
                    typ = ITEM_NAME

            # Requests item data from minecraft plugin
            if typ == ITEM_ID_PAIR or typ == ITEM_ID:
                data = mc.id_to_data(da)
            else:
                # Check for groupings
                if mc.get_group_by_name(da):
                    data = mc.get_group_by_name(da)

                else:
                    data = mc.name_to_data(str(da))

            if not data:
                await client.send_message(message.channel, "**No item with that name/id**")
                # stat.pluswrongarg()
                return

            if not isinstance(data, list):
                details = "**{}**```css\nId: {}:{}```".format(data.get("name"), data.get("type"), data.get("meta"))

                # Details are uploaded simultaneously with the picture
                with open("plugins/mc/{}-{}.png".format(data.get("type"), data.get("meta") or 0), "rb") as pic:
                    await client.send_file(message.channel, pic, content=details)
                    # stat.plusimagesent()
            else:
                combined = []
                for item in data:
                    details = "**{}**```css\nId: {}:{}```".format(item.get("name"), item.get("type"), item.get("meta"))
                    combined.append(details)

                await client.send_message(message.channel, "".join(combined))


class NanoPlugin:
    _name = "Minecraft Commands"
    _version = 0.1

    handler = Minecraft
    events = {
        "on_message": 10
        # type : importance
    }
