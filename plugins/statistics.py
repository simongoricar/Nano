# coding=utf-8
import logging

try:
    from ujson import loads, dumps
except ImportError:
    from json import loads, dumps
from discord import Embed, Colour

from data.utils import is_valid_command, get_valid_commands
from data.confparser import get_config_parser
from data.stats import MESSAGE

commands = {
    "_stats": {"desc": "Some stats like message count and stuff like that."},
    "_advancedstats": {"desc": "More in-depth stats."},
}

valid_commands = commands.keys()

parser = get_config_parser()
log = logging.getLogger(__name__)


class StatisticsParser:
    T_DAY = 60 * 60 * 24
    T_WEEK = 60 * 60 * 24 * 7
    T_MONTH = 60 * 60 * 24 * 7 * 30

    """
    Data layout:
        
        MAIN DB:
        bs:uniqueusers -> Set with user ids
        bs:uniqueguilds -> Set with guild ids
        
        CACHE DB
        bs: 
            ˇ represents user/guild ID
            u/g: day:<id>   -> value
                 week:<id>  -> value
                 month:<id> -> value
    
    """
    def __init__(self, handler):
        cache = handler.get_cache_handler()
        self.cache = cache.get_plugin_data_manager("bs")
        self.plugin = handler.get_plugin_data_manager("bs")

        self.time_periods = {
            "day": StatisticsParser.T_DAY,
            "week": StatisticsParser.T_WEEK,
            "month": StatisticsParser.T_MONTH
        }


    def track_user(self, user_id, guild_id):
        # To increase performance
        pipe = self.plugin.pipeline()

        pipe.sadd("bs:uniqueusers", user_id)
        pipe.sadd("bs:uniqueguilds", guild_id)

        pipe.execute()

        # History belongs to the cache part
        cpipe = self.cache.pipeline()

        for name, ttl in self.time_periods.items():
            cpipe.set("bs:u:{}:{}".format(name, user_id), 0, ex=ttl)
            cpipe.set("bs:g:{}:{}".format(name, guild_id), 0, ex=ttl)

        cpipe.execute()

    def get_statistics_uniques(self) -> tuple:
        u_users = self._get_sscan_length("bs:uniqueusers")
        u_guilds = self._get_sscan_length("bs:uniqueguilds")

        return u_users, u_guilds

    def _get_sscan_length(self, name, match=None) -> int:
        """
        Memory-efficient sscan length
        """
        amount = 0

        cursor = '0'
        while cursor != 0:
            cursor, data = self.plugin.sscan(name, cursor, use_namespace=False, match=match, count=20)
            amount += len(data)

        return amount

    def _get_scan_length(self, match) -> int:
        """
        Memory-efficient scan length
        """
        amount = 0

        cursor = '0'
        while cursor != 0:
            cursor, data = self.cache.scan(cursor, use_namespace=False, match=match, count=20)
            amount += len(data)

        return amount

    def get_statistics_history(self) -> dict:
        data = {}
        for name in self.time_periods.keys():
            data[name] = {
                "users": self._get_scan_length("bs:u:{}:*".format(name)),
                "guilds": self._get_scan_length("bs:g:{}:*".format(name))
            }

        return data


class Statistics:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.adv_stats = StatisticsParser(self.handler)
        self.valid_commands = set()

    async def on_plugins_loaded(self):
        # Collect all valid commands
        plugins = [a.get("plugin") for a in self.nano.plugins.values() if a.get("plugin")]

        temp = []
        for pl in plugins:
            cmds = get_valid_commands(pl)
            if cmds is not None:
                # Joins two lists
                temp += cmds

        # Special case: rip
        temp.remove("_rip")

        self.valid_commands = set(temp)

    async def on_message(self, message, **kwargs):
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        # If any of the commands match, add user to statistics
        np_text = "_" + message.content.lstrip(prefix).split(" ")[0]
        if np_text in self.valid_commands:
            # Register user to stats
            self.adv_stats.track_user(message.author.id, message.guild.id)

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

        # !stats
        if startswith(prefix + "stats"):
            file = self.stats.get_data()

            messages = file.get("msgcount")
            wrong_args = file.get("wrongargcount")
            sleeps = file.get("timesslept")
            wrong_permissions = file.get("wrongpermscount")
            helps = file.get("peoplehelped")
            votes = file.get("votesgot")
            pings = file.get("timespinged")
            imgs = file.get("imagessent")

            embed = Embed(colour=Colour.gold())

            embed.add_field(name=trans.get("MSG_STATS_MSGS", lang), value=messages)
            embed.add_field(name=trans.get("MSG_STATS_ARGS", lang), value=wrong_args)
            embed.add_field(name=trans.get("MSG_STATS_PERM", lang), value=wrong_permissions)
            embed.add_field(name=trans.get("MSG_STATS_HELP", lang), value=helps)
            embed.add_field(name=trans.get("MSG_STATS_IMG", lang), value=imgs)
            embed.add_field(name=trans.get("MSG_STATS_VOTES", lang), value=votes)
            embed.add_field(name=trans.get("MSG_STATS_SLEPT", lang), value=sleeps)
            embed.add_field(name=trans.get("MSG_STATS_PONG", lang), value=pings)
            embed.add_field(name=trans.get("MSG_STATS_IMG", lang), value=imgs)

            await message.channel.send(trans.get("MSG_STATS_INFO", lang), embed=embed)

        # !advancedstats
        elif startswith(prefix + "advancedstats"):
            u_users, u_guilds = self.adv_stats.get_statistics_uniques()

            data = self.adv_stats.get_statistics_history()

            description = trans.get("MSG_ADVS_DESC", lang).format(u_users, u_guilds) \
                        + "\n\n"\
                        + trans.get("MSG_ADVS_HISTORY", lang)\
                        + trans.get("MSG_ADVS_HISTORY_BODY", lang).format(
                                day_u=data["day"]["users"],
                                day_g=data["day"]["guilds"],
                                week_u=data["week"]["users"],
                                week_g=data["week"]["guilds"],
                                month_u=data["month"]["users"],
                                month_g=data["month"]["guilds"],
                            )

            embed = Embed(title=trans.get("MSG_ADVS_TITLE", lang).format(NanoPlugin.version),
                          description=description)

            await message.channel.send(embed=embed)




class NanoPlugin:
    name = "Statistics"
    version = "2"

    handler = Statistics
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
