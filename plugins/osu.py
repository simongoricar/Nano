# coding=utf-8
# coding=utf-8
import logging
import configparser
import osu_ds
import time
from discord import Message, Embed, Colour
from data.utils import is_valid_command, invert_num, invert_str, split_every
from data.stats import MESSAGE

__author__ = "DefaltSimon"
# osu! plugin for Nano

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

valid_commands = [
    "_osu"
]


class Osu:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        self.osu = osu_ds.OsuApi(api_key=parser.get("osu", "api-key"))

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)
        client = self.client

        prefix = kwargs.get("prefix")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*args):
            for a in args:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "osu"):
            username = message.content[len(prefix + "osu "):]

            t_start = time.time()

            user = self.osu.get_user(username)

            if not user:
                await client.send_message(message.channel, "User does not exist.")
                return

            # About inverting: this inverts the number before and after the splitting
            def prepare(this):
                return invert_str(",".join(split_every(str(invert_num(this)), 3)))

            global_rank = prepare(user.world_rank)
            country_rank = prepare(user.country_rank)

            total_score = prepare(user.total_score)
            ranked_score = prepare(user.ranked_score)

            acc = str(round(float(user.accuracy), 2)) + " %"

            osu_level = int(float(user.level))
            avatar_url = "http://a.ppy.sh/{}".format(user.id)

            # Color is determined by the level range
            if osu_level < 10:
                color = Colour.darker_grey()
            elif osu_level < 25:
                color = Colour.light_grey()
            elif osu_level < 40:
                color = Colour.dark_teal()
            elif osu_level < 50:
                color = Colour.teal()
            elif osu_level < 75:
                color = Colour.dark_purple()
            elif osu_level < 100:
                color = Colour.purple()
            # Only the masters get the gold ;)
            else:
                color = Colour.gold()

            desc = "**Level**: {}\n**Rank**: \n\t" \
                   "**Global**:            #{}\n\t" \
                   "**Country** (**{}**): #{}".format(osu_level, global_rank, user.country, country_rank)

            embed = Embed(url=user.profile_url, description=desc, colour=color)
            embed.set_author(name=user.name)
            embed.set_thumbnail(url=avatar_url)

            embed.add_field(name="Total score", value=total_score)
            embed.add_field(name="Ranked score", value=ranked_score)
            embed.add_field(name="Average accuracy", value=acc)

            delta = int((time.time() - t_start) * 1000)
            embed.set_footer(text="Search took {} ms".format(delta))

            await client.send_message(message.channel, embed=embed)


class NanoPlugin:
    _name = "osu!"
    _version = "0.1"

    handler = Osu
    events = {
        "on_message": 10
        # type : importance
    }
