# coding=utf-8
import asyncio
import gc
import logging
import os
import time
import psutil

from discord import utils, Embed, Colour, __version__ as d_version, HTTPException
from discord import Member, Guild

from data.stats import MESSAGE
from data.utils import is_valid_command, log_to_file, is_disabled, IgnoredException

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Might be implemented someday
# BOT_FARM_RATIO = 0.55
# BOT_FARM_MIN_MEMBERS = 40

FAILPROOF_TIME_WAIT = 2.5

commands = {
    "_debug": {"desc": "Displays EVEN MORE stats about Nano."},
    "_status": {"desc": "Displays current status: server, user and channel count.", "alias": "nano.status"},
    "nano.status": {"desc": "Displays current status: server, user and channel count.", "alias": "_status"},
    "_prefix": {"desc": "No use whatsoever, but jk here you have it."},
    "nano.prefix": {"desc": "Helps you figure out the prefix."},
    "_members": {"desc": "Lists all members on the server."},
    "_server": {"desc": "Shows info about current server."}
}

valid_commands = commands.keys()


class ServerManagement:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        # Debug
        self.lt = time.time()

        self.modp = self.handler.get_plugin_data_manager("moderation")

    async def handle_log_channel(self, guild):
        # Older servers may still have names of channels, that can cause an error
        try:
            chan = int(self.handler.get_var(guild.id, "logchannel"))
        except ValueError:
            return None
        except TypeError:
            return None

        if is_disabled(chan):
            return None

        return utils.find(lambda m: m.id == chan, guild.text_channels)

    async def default_channel(self, guild):
        # If the guild doesn't have any text channels just exit
        if not guild.text_channels:
            raise IgnoredException

        default = self.handler.get_defaultchannel(guild.id)

        # If a custom one is set, ignore other logic
        if not is_disabled(default):
            default = int(default)

            chan = utils.find(lambda c: c.id == default, guild.text_channels)
            if chan:
                return chan

        # Try to find #general or one that starts with general
        chan = utils.find(lambda c: c.name == "general", guild.text_channels)
        if chan:
            return chan

        # Else, return the topmost one

        top = sorted(guild.text_channels, key=lambda a: a.position)[0]
        return top

    @staticmethod
    async def send_message_failproof(channel, message=None, embed=None):
        try:
            await channel.send(content=message, embed=embed)
        except HTTPException:
            await asyncio.sleep(FAILPROOF_TIME_WAIT)
            await channel.send(content=message, embed=embed)
            raise

    @staticmethod
    def make_logchannel_embed(user, action, color=Colour(0x2e75cc)):
        # Color: Nano's dark blue color
        return Embed(description="ID: {}".format(user.id), color=color).set_author(name="{} {}".format(user.name, action), icon_url=user.avatar_url)

    @staticmethod
    def parse_dynamic_response(text: str, member: Member, guild: Guild):
        order = [":username", ":user", ":server"]
        replacements = {
            ":user": member.mention,
            ":username": member.display_name,
            ":server": guild.name
        }

        for t in order:
            text = text.replace(t, replacements[t])

        return text

    async def on_message(self, message, **kwargs):
        client = self.client
        trans = self.trans

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

        # !status
        if startswith(prefix + "status"):
            server_count = 0
            members = 0
            channels = 0

            # Iterate though servers and add up things
            for guild in client.guilds:

                server_count += 1
                members += int(guild.member_count)
                channels += len(guild.channels)

            embed = Embed(name=trans.get("MSG_STATUS_STATS", lang), colour=Colour.dark_blue())

            embed.add_field(name=trans.get("MSG_STATUS_SERVERS", lang), value=trans.get("MSG_STATUS_SERVERS_L", lang).format(server_count), inline=True)
            embed.add_field(name=trans.get("MSG_STATUS_USERS", lang), value=trans.get("MSG_STATUS_USERS_L", lang).format(members), inline=True)
            embed.add_field(name=trans.get("MSG_STATUS_CHANNELS", lang), value=trans.get("MSG_STATUS_CHANNELS_L", lang).format(channels), inline=True)

            await message.channel.send("**Stats**", embed=embed)

        # !debug
        elif startswith(prefix + "debug", prefix + "stats more"):
            # Some more debug data

            # Ratelimit every 360 seconds
            if ((self.lt - time.time()) < 360) and not self.handler.is_bot_owner(message.author.id):
                await message.channel.send(trans.get("MSG_STATUS_RATELIMIT", lang))
                return

            self.lt = time.time()

            # CPU
            cpu = psutil.cpu_percent(interval=0.3)

            # RAM
            def get_ram_usage():
                nano_process = psutil.Process(os.getpid())
                return round(nano_process.memory_info()[0] / float(2 ** 20), 1)  # Converts to MB

            mem_before = get_ram_usage()
            # Attempt garbage collection
            gc.collect()

            mem_after = get_ram_usage()
            garbage = round(mem_after - mem_before, 2)

            # OTHER
            nano_version = self.nano.version
            discord_version = d_version

            reminders = self.nano.get_plugin("reminder").instance.reminder.get_reminder_amount()
            polls = self.nano.get_plugin("voting").instance.vote.get_vote_amount()

            # Redis db stats
            redis_mem = self.handler.db_info("memory").get("used_memory_human")
            redis_size = self.handler.db_size()

            fields = trans.get("MSG_DEBUG_MULTI", lang).format(nano_version, discord_version, mem_after, abs(garbage),
                                                               cpu, reminders, polls, redis_mem, redis_size)

            total_shards = len(self.client.shards.keys())
            current_shard = message.guild.shard_id

            additional = trans.get("MSG_DEBUG_MULTI_2", lang).format(total_shards, current_shard)

            await message.channel.send(fields + "\n" + additional)

        # !prefix
        elif startswith(prefix + "prefix"):
            await message.channel.send(trans.get("MSG_PREFIX_OHYEAH", lang))

        # nano.prefix
        elif startswith("nano.prefix"):
            await message.channel.send(trans.get("MSG_PREFIX", lang).format(prefix))

        # !members
        elif startswith(prefix + "members"):
            ls = [member.name for member in message.guild.members]
            amount = len(ls)

            members = trans.get("MSG_MEMBERS_LIST", lang).format(", ".join(["`{}`".format(mem) for mem in ls])) + \
                      trans.get("MSG_MEMBERS_TOTAL", lang).format(amount)

            if len(members) > 2000:
                # Only send the number if the message is too long.
                await message.channel.send(trans.get("MSG_MEMBERS_AMOUNT", lang).format(amount))

            else:
                await message.channel.send(members)

        # !server
        elif startswith(prefix + "server"):
            user_count = message.guild.member_count
            users_online = len([user.id for user in message.guild.members if user.status == user.status.online])

            v_level = message.guild.verification_level
            if v_level == v_level.none:
                v_level = trans.get("MSG_SERVER_VL_NONE", lang)
            elif v_level == v_level.low:
                v_level = trans.get("MSG_SERVER_VL_LOW", lang)
            elif v_level == v_level.medium:
                v_level = trans.get("MSG_SERVER_VL_MEDIUM", lang)
            else:
                v_level = trans.get("MSG_SERVER_VL_HIGH", lang)

            text_chan = len(message.guild.text_channels)
            voice_chan = len(message.guild.voice_channels)
            channels = text_chan + voice_chan

            # Teal Blue
            embed = Embed(colour=Colour(0x3F51B5), description=trans.get("MSG_SERVER_ID", lang).format(message.guild.id))

            if message.guild.icon:
                embed.set_author(name=message.guild.name, icon_url=message.guild.icon_url)
                embed.set_thumbnail(url=message.guild.icon_url)
            else:
                embed.set_author(name=message.guild.name)

            embed.set_footer(text=trans.get("MSG_SERVER_DATE_CREATED", lang).format(message.guild.created_at))

            embed.add_field(name=trans.get("MSG_SERVER_MEMBERS", lang).format(user_count),
                            value=trans.get("MSG_SERVER_MEMBERS_L", lang).format(users_online))

            embed.add_field(name=trans.get("MSG_SERVER_CHANNELS", lang).format(channels),
                            value=trans.get("MSG_SERVER_CHANNELS_L", lang).format(voice_chan, text_chan))

            embed.add_field(name=trans.get("MSG_SERVER_VL", lang), value=v_level)
            embed.add_field(name=trans.get("MSG_SERVER_ROLES", lang),
                            value=trans.get("MSG_SERVER_ROLES_L", lang).format(len(message.guild.roles) - 1))

            owner = message.guild.owner

            embed.add_field(name=trans.get("MSG_SERVER_OWNER", lang),
                            value=trans.get("MSG_SERVER_OWNER_L", lang).format(owner.name,
                                                                               owner.discriminator,
                                                                               owner.id))

            await message.channel.send(trans.get("MSG_SERVER_INFO", lang), embed=embed)

    async def on_member_join(self, member, **kwargs):
        lang = kwargs.get("lang")

        raw_msg = str(self.handler.get_var(member.guild.id, "welcomemsg"))
        welcome_msg = self.parse_dynamic_response(raw_msg, member, member.guild)

        log_c = await self.handle_log_channel(member.guild)
        def_c = await self.default_channel(member.guild)

        # Ignore if disabled
        if log_c:
            embed = self.make_logchannel_embed(member, self.trans.get("EVENT_JOIN", lang))
            await self.send_message_failproof(log_c, embed=embed)
        
        if not is_disabled(welcome_msg):
            await self.send_message_failproof(def_c, welcome_msg)

    async def on_member_remove(self, member, **kwargs):
        """
        Bans, kicks, softbans and leaves are all handled here
        """
        lang = kwargs.get("lang")

        # Automatically switches between kick/leave/... messages
        val = self.modp.get("{}:{}".format(member.guild.id, member.id))

        if val == "kick":
            key = "kickmsg"
            ev_text = self.trans.get("EVENT_KICK", lang)
        elif val == "softban":
            key = "banmsg"
            ev_text = self.trans.get("EVENT_SOFTBAN", lang)
        elif val == "ban":
            key = "banmsg"
            ev_text = self.trans.get("EVENT_BAN", lang)
        else:
            key = "leavemsg"
            ev_text = self.trans.get("EVENT_LEAVE", lang)


        raw_msg = str(self.handler.get_var(member.guild.id, key))
        leave_msg = self.parse_dynamic_response(raw_msg, member, member.guild)

        log_c = await self.handle_log_channel(member.guild)
        def_c = await self.default_channel(member.guild)

        # Ignore if disabled
        if log_c:
            embed = self.make_logchannel_embed(member, ev_text)
            await self.send_message_failproof(log_c, embed=embed)
        
        if not is_disabled(leave_msg):
            await self.send_message_failproof(def_c, leave_msg)

    async def on_guild_join(self, guild, **kwargs):
        # Always 'en'
        lang = kwargs.get("lang")

        d_chan = await self.default_channel(guild)
        # Say hi to the server
        await self.send_message_failproof(d_chan, self.trans.get("EVENT_SERVER_JOIN", lang))

        # Create server settings
        self.handler.server_setup(guild)

        # Log
        log_to_file("Joined guild: {}".format(guild.name))

    async def on_guild_remove(self, guild, **_):
        # Deletes server data
        self.handler.delete_server(guild.id)

        # Log
        log_to_file("Removed from guild: {}".format(guild.name))

    async def on_ready(self):
        await self.client.wait_until_ready()

        # Delay in case servers are still being received
        await asyncio.sleep(10)

        log.info("Checking guild vars...")
        for guild in self.client.guilds:
            if not self.handler.server_exists(guild.id):
                self.handler.server_setup(guild)

            self.handler.check_server_vars(guild)
        log.info("Done.")

        log.info("Checking for non-used guild data...")
        server_ids = [s.id for s in self.client.guilds]
        self.handler.check_old_servers(server_ids)
        log.info("Done.")


class NanoPlugin:
    name = "Moderator"
    version = "2"

    handler = ServerManagement
    events = {
        "on_message": 10,
        "on_ready": 11,
        "on_member_join": 10,
        "on_member_remove": 10,
        "on_guild_join": 9,
        "on_guild_remove": 9,
        # type : importance
    }
