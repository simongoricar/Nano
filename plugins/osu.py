# coding=utf-8
import configparser
import logging
import time

import osu_ds
from discord import Message, Embed, Colour, errors

from data.stats import MESSAGE
from data.utils import is_valid_command, invert_num, invert_str, split_every

#####
# osu! plugin
#####

logger = logging.getLogger(__name__)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

commands = {
    "_osu": {"desc": "Displays stats for that osu! user.", "use": "[command] [username/id]", "alias": None},
}

valid_commands = commands.keys()


# About inverting: this inverts the number before and after the splitting
# Makes the number formatted
# 1000 -> 1,000
def prepare(this):
    return invert_str(",".join(split_every(str(invert_num(this)), 3)))


class Osu:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        try:
            key = parser.get("osu", "api-key")
            self.osu = osu_ds.OsuApi(api_key=key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.critical("Missing api key for osu!, disabling plugin...")
            raise RuntimeError

    async def on_message(self, message, **kwargs):
        client = self.client
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

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

        # TODO fix osu-ds
        if startswith(prefix + "osu"):
            username = message.content[len(prefix + "osu "):]
            t_start = time.time()

            user = await self.osu.get_user(username)

            if not user:
                await client.send_message(message.channel, trans.get("ERROR_NO_USER2", lang))
                return

            global_rank = prepare(user.world_rank)
            country_rank = prepare(user.country_rank)

            total_score = prepare(user.total_score)
            ranked_score = prepare(user.ranked_score)

            try:
                acc = "{} %".format(round(float(user.accuracy), 2))
            except TypeError:
                acc = trans.get("INFO_ERROR", lang)

            pp_amount = int(float(user.pp))
            osu_level = int(float(user.level))
            avatar_url = user.avatar_url

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
            # Only masters get the gold ;)
            else:
                color = Colour.gold()

            desc = trans.get("MSG_OSU_DESC", lang).format(global_rank, user.country, country_rank, pp_amount, user.playcount)
            name = trans.get("MSG_OSU_TITLE", lang).format(user.name, osu_level)

            embed = Embed(url=user.profile_url, description=desc, colour=color)
            embed.set_author(name=name)
            embed.set_thumbnail(url=avatar_url)

            embed.add_field(name=trans.get("MSG_OSU_TOTAL_SC", lang), value=total_score)
            embed.add_field(name=trans.get("MSG_OSU_RANKED_SC", lang), value=ranked_score)
            embed.add_field(name=trans.get("MSG_OSU_AVG_ACC", lang), value=acc)

            delta = int((time.time() - t_start) * 1000)
            embed.set_footer(text=trans.get("MSG_OSU_TIME", lang).format(delta))

            try:
                await client.send_message(message.channel, embed=embed)
            except errors.HTTPException:
                await client.send_message(message.channel, trans.get("MSG_OSU_ERROR", lang))


class NanoPlugin:
    name = "osu!"
    version = "6"

    handler = Osu
    events = {
        "on_message": 10
        # type : importance
    }
