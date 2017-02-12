# coding=utf-8
import discord
import os
import logging
import psutil
import time
import gc
import asyncio
from datetime import datetime, timedelta
from data.stats import NanoStats, MESSAGE
from data.serverhandler import ServerHandler
from data.utils import is_valid_command, log_to_file, is_disabled


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

nano_welcome = "**Hi!** I'm Nano!\nNow that you have invited me to your server, you might want to set up some things." \
               "Right now only the server owner can use my restricted commands. But no worries, you can add admin permissions" \
               "to others using `nano.admins add @mention` or by assigning them a role named **Nano Admin**!" \
               "\nTo get started, type `!setup` as the server owner. It will help you set up most of the things. " \
               "After that, you might want to see `!cmds` to get familiar with my commands."

commands = {
    "_debug": {"desc": "Displays EVEN MORE stats about Nano.", "use": None, "alias": None},
    "_status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "nano.status"},
    "nano.status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "_status"},
    "_stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "nano.stats"},
    "nano.stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "_stats"},
    "_prefix": {"desc": "No use whatsoever, but jk here you have it.", "use": None, "alias": None},
    "nano.prefix": {"desc": "Helps you figure out the prefix.", "use": None, "alias": None},
    "_members": {"desc": "Lists all members on the server.", "use": None, "alias": None},
}

valid_commands = commands.keys()

# noinspection PyTypeChecker
class ServerManagement:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        # Debug
        self.lt = time.time()

    async def handle_log_channel(self, server):
        # Check if the channel already exists
        if not [ch for ch in server.channels if ch.name == self.handler.get_var(server.id, "logchannel")]:

            if is_disabled(self.handler.get_var(server.id, "logchannel")):
                return None

            # Creates permission overwrites: normal users cannot see the channel,
            # only users with the role "Nano Admin" and the bot
            them = discord.PermissionOverwrite(read_messages=False, send_messages=False, read_message_history=False)
            us = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True,
                                             attach_files=True, embed_links=True, manage_messages=True)

            admins = discord.utils.find(lambda m: m.name == "Nano Admin", server.roles)

            them_perms = discord.ChannelPermissions(target=server.default_role, overwrite=them)
            nano_perms = discord.ChannelPermissions(target=server.me, overwrite=us)

            log_channel_name = self.handler.get_var(server.id, "logchannel")

            if admins:
                admin_perms = discord.ChannelPermissions(target=admins, overwrite=us)

                return await self.client.create_channel(server, log_channel_name, admin_perms, them_perms, nano_perms)

            else:
                return await self.client.create_channel(server, log_channel_name, them_perms, nano_perms)

        else:
            return discord.utils.find(lambda m: m.name == self.handler.get_var(server.id, "logchannel"), server.channels)

    async def on_message(self, message, **kwargs):
        assert isinstance(message, discord.Message)
        assert isinstance(self.stats, NanoStats)

        prefix = kwargs.get("prefix")
        client = self.client

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False


        # !status
        if startswith(prefix + "status"):
            server_count = 0
            members = 0
            channels = 0

            # Iterate though servers and add up things
            for server in client.servers:

                server_count += 1
                members += int(server.member_count)
                channels += len(server.channels)

            embed = discord.Embed(name="Stats", colour=discord.Colour.dark_blue())
            embed.add_field(name="Servers", value="{} servers".format(server_count), inline=True)
            embed.add_field(name="Users", value="{} members".format(members), inline=True)
            embed.add_field(name="Channels", value="{} channels".format(channels), inline=True)

            await client.send_message(message.channel, "**Stats**", embed=embed)

        # !debug
        elif startswith(prefix + "debug", prefix + "stats more"):
            # Some more debug data

            if ((self.lt - time.time()) < 360) and not self.handler.is_bot_owner(message.author.id):
                return
            else:
                self.lt = time.time()

            # CPU
            cpu = psutil.cpu_percent(interval=0.5)

            # RAM
            def check_ram():
                nano_process = psutil.Process(os.getpid())
                return round(nano_process.memory_info()[0] / float(2 ** 20), 1)  # Converts to MB

            mem_before = check_ram()
            # Attempt garbage collection
            gc.collect()

            mem_after = check_ram()
            garbage = round(mem_after - mem_before, 2)

            # OTHER
            d = datetime(1, 1, 1) + timedelta(seconds=time.time() - self.nano.boot_time)
            uptime = "{} days, {}:{}:{}".format(d.day - 1, d.hour, d.minute, d.second)

            nano_version = self.nano.version
            discord_version = discord.__version__

            reminders = len(self.nano.get_plugin("reminder").get("instance").reminder.reminders)
            polls = len(self.nano.get_plugin("voting").get("instance").vote.progress)

            embed = discord.Embed(colour=discord.Colour.green())
            embed.add_field(name="Nano version", value=nano_version)
            embed.add_field(name="discord.py", value=discord_version)
            embed.add_field(name="RAM usage", value="{} MB (garbage collected {} MB)".format(mem_after, garbage))
            embed.add_field(name="CPU usage", value="{} %".format(cpu))
            embed.add_field(name="Uptime", value=uptime)
            embed.add_field(name="Ongoing reminders", value=reminders, inline=False)
            embed.add_field(name="Ongoing votes", value=polls)

            await client.send_message(message.channel, "**Debug data:**", embed=embed)

        # !stats
        elif startswith(prefix + "stats"):
            file = self.stats.get_data()

            messages = file.get("msgcount")
            wrong_args = file.get("wrongargcount")
            sleeps = file.get("timesslept")
            wrong_permissions = file.get("wrongpermscount")
            helps = file.get("peoplehelped")
            votes = file.get("votesgot")
            pings = file.get("timespinged")

            embed = discord.Embed(colour=discord.Colour.gold())

            embed.add_field(name="Messages sent", value=messages)
            embed.add_field(name="Wrong arguments got", value=wrong_args)
            embed.add_field(name="Command abuses tried", value=wrong_permissions)
            embed.add_field(name="People Helped", value=helps)
            embed.add_field(name="Votes got", value=votes)
            embed.add_field(name="Times slept", value=sleeps)
            embed.add_field(name="Times Pong!-ed", value=pings)
            # Left out "images uploaded" because there was no use

            await client.send_message(message.channel, "**Stats**", embed=embed)

        # !prefix
        elif startswith(prefix + "prefix"):
            await client.send_message(message.channel, "You guessed it!")

        # nano.prefix
        elif startswith("nano.prefix"):
            await client.send_message(message.channel, "The prefix on this server is **{}**".format(prefix))

        # !members
        elif startswith(prefix + "members"):
            ls = [member.name for member in message.channel.server.members]

            members = "*__Members__*:\n\n{}".format(", ".join(["`{}`".format(mem) for mem in ls])) + "\nTotal: **{}** members".format(len(ls))

            if len(members) > 2000:
                # Only send the number if the message is too long.
                await client.send_message(message.channel, "This guild has a total number of **{}** members".format(len(ls)))

            else:
                await client.send_message(message.channel, members)

    async def on_member_join(self, member, **_):
        assert isinstance(self.handler, ServerHandler)

        replacement_logic = {
            ":user": member.mention,
            ":username": member.name,
            ":server": member.server.name }

        welcome_msg = str(self.handler.get_var(member.server.id, "welcomemsg"))

        # Replacement logic
        for trigg, repl in replacement_logic.items():
            welcome_msg = welcome_msg.replace(trigg, repl)

        log_c = await self.handle_log_channel(member.server)

        # Ignore if disabled
        if log_c:
            await self.client.send_message(log_c, "{} has joined the server".format(member.mention))
        
        if not is_disabled(welcome_msg):
            await self.client.send_message(member.server.default_channel, welcome_msg)

    async def on_member_ban(self, member, **_):
        assert isinstance(self.handler, ServerHandler)

        replacement_logic = {
            ":user": member.mention,
            ":username": member.name,
            ":server": member.server.name}

        ban_msg = str(self.handler.get_var(member.server.id, "banmsg"))

        for trigg, repl in replacement_logic.items():
            ban_msg = ban_msg.replace(trigg, repl)

        log_c = await self.handle_log_channel(member.server)

        # Ignore if disabled
        if log_c:
            await self.client.send_message(log_c, "{} was banned.".format(member.mention))

        if not is_disabled(ban_msg):
            await self.client.send_message(member.server.default_channel, ban_msg)

    async def on_member_remove(self, member, **_):
        assert isinstance(self.handler, ServerHandler)

        replacement_logic = {
            ":user": member.mention,
            ":username": member.name,
            ":server": member.server.name}

        leave_msg = str(self.handler.get_var(member.server.id, "leavemsg"))

        for trigg, repl in replacement_logic.items():
            leave_msg = leave_msg.replace(trigg, repl)

        log_c = await self.handle_log_channel(member.server)

        # Ignore if disabled
        if log_c:
            await self.client.send_message(log_c, "{} left the server.".format(member.mention))
        
        if not is_disabled(leave_msg):
            await self.client.send_message(member.server.default_channel, leave_msg)

    async def on_server_join(self, server, **_):
        # Say hi to the server
        await self.client.send_message(server.default_channel, nano_welcome)

        # Create server settings
        self.handler.server_setup(server)

        # Log
        log_to_file("Joined server: {}".format(server.name))

    async def on_server_remove(self, server, **_):
        # Deletes server data
        server_ids = [s.id for s in self.client.servers]
        self.handler._delete_old_servers(server_ids)

        # Log
        log_to_file("Removed from server: {}".format(server.name))

    async def on_ready(self):
        await self.client.wait_until_ready()

        log.info("Checking server vars...")
        for server in self.client.servers:
            if not self.handler.server_exists(server):
                self.handler.server_setup(server)

            self.handler.check_server_vars(server)

        log.info("Finished checking server data.")


class NanoPlugin:
    _name = "Moderator"
    _version = "0.2.6"

    handler = ServerManagement
    events = {
        "on_message": 10,
        "on_ready": 11,
        "on_member_join": 10,
        "on_member_ban": 10,
        "on_member_remove": 10,
        "on_server_join": 9,
        "on_server_remove": 9,
        # type : importance
    }
