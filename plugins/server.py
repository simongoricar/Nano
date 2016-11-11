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
from data.utils import is_valid_command, log_to_file


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

nano_welcome = "**Hi!** I'm Nano!\nNow that you have invited me to your server, you might want to set up some things." \
               "Right now only the server owner can use my restricted commands. But no worries, you can add admin permissions" \
               "to others using `nano.admins add @mention` or by assigning them a role named **Nano Admin**!" \
               "\nTo get started, type `!setup` as the server owner. It will help you set up most of the things. " \
               "After that, you might want to see `!cmds` to get familiar with my commands."

valid_commands = [
    "_stats", "_stats more", "_status", "_prefix", "_members", "nano.prefix", "_debug"
]


class ServerManagement:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

    async def handle_log_channel(self, server):
        # Check if the channel already exists
        if not [ch for ch in server.channels if ch.name == self.handler.get_var(server.id, "logchannel")]:

            # Creates permission overwrites: normal users cannot see the channel, only users with the role "Nano Admin" and the bot
            them = discord.PermissionOverwrite(read_messages=False, send_messages=False, read_message_history=False)
            us = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True,
                                             attach_files=True, embed_links=True, manage_messages=True)

            admins = discord.utils.find(lambda m: m.name == "Nano Admin", server.roles)

            if admins:
                admin_perms = discord.ChannelPermissions(target=admins, overwrite=us)
            else:
                admin_perms = None

            then_perms = discord.ChannelPermissions(target=server.default_role, overwrite=them)
            nano_perms = discord.ChannelPermissions(target=server.me, overwrite=us)

            log_channel_name = self.handler.get_var(server.id, "logchannel")

            if admins:
                return await self.client.create_channel(server, log_channel_name, admin_perms, then_perms, nano_perms)

            else:
                return await self.client.create_channel(server, log_channel_name, then_perms, nano_perms)

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

            stats = "**Stats**\n\nServers: `{}`\nUsers: `{}`\nChannels: `{}`".format(server_count, members, channels)

            await client.send_message(message.channel, stats)

        # !debug
        elif startswith(prefix + "debug", prefix + "stats more"):
            # Some more debug data

            # RAM
            def check_ram():
                nano_process = psutil.Process(os.getpid())
                return round(nano_process.memory_info()[0] / float(2 ** 20), 1)  # Converts to MB

            mem_before = check_ram()
            # Attempt garbage collection
            gc.collect()

            mem_after = check_ram()
            garbage = round(mem_after - mem_before, 2)

            # CPU
            cpu = psutil.cpu_percent(interval=0.5)

            # OTHER
            d = datetime(1, 1, 1) + timedelta(seconds=time.time() - self.nano.boot_time)
            uptime = "{} days, {}:{}:{}".format(d.day - 1, d.hour, d.minute, d.second)

            nano_version = self.nano.version
            discord_version = discord.__version__

            reminders = len(self.nano.get_plugin("reminder").get("instance").reminder.reminders)
            polls = len(self.nano.get_plugin("voting").get("instance").vote.progress)

            debug_data = """```
Nano:                  {}
discord.py:            {}
RAM usage:             {} MB (garbage collected {} MB)
Cpu usage:             {} %
Uptime:                {}
Current reminders:     {}
Current votes:         {}```""".format(nano_version, discord_version, mem_after, garbage, cpu, uptime, reminders, polls)

            await client.send_message(message.channel, debug_data)

        # !stats
        elif startswith(prefix + "stats"):
            file = self.stats.get_data()

            messages = file.get("msgcount")
            wrong_args = file.get("wrongargcount")
            sleeps = file.get("timesslept")
            wrong_permissions = file.get("wrongpermscount")
            helps = file.get("peoplehelped")
            images = file.get("imagessent")
            votes = file.get("votesgot")
            pings = file.get("timespinged")

            to_send = "**Stats**\n```python\n{} messages sent\n{} people yelled at because of wrong args\n" \
                      "{} people denied because of wrong permissions\n{} people helped\n{} votes got\n{} times slept\n" \
                      "{} images uploaded\n{} times Pong!-ed```".format(messages, wrong_args, wrong_permissions,
                                                                        helps, votes, sleeps, images, pings)

            await client.send_message(message.channel, to_send)

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
            ":server": member.server.name }

        welcome_msg = str(self.handler.get_var(member.server.id, "welcomemsg"))

        # Replacement logic
        for trigg, repl in replacement_logic.items():
            welcome_msg = welcome_msg.replace(trigg, repl)

        log_c = await self.client.handler_log_channel(member.server)

        await self.client.send_message(log_c, welcome_msg)
        await self.client.send_message(member.server.default_channel, welcome_msg)

    async def on_member_ban(self, member, **_):
        assert isinstance(self.handler, ServerHandler)

        replacement_logic = {
            ":user": member.mention,
            ":server": member.server.name}

        ban_msg = str(self.handler.get_var(member.server.id, "banmsg"))

        for trigg, repl in replacement_logic.items():
            ban_msg = ban_msg.replace(trigg, repl)

        log_c = await self.handle_log_channel(member.server)

        await self.client.send_message(log_c, ban_msg)

    async def on_member_remove(self, member, **_):
        assert isinstance(self.handler, ServerHandler)

        replacement_logic = {
            ":user": member.mention,
            ":server": member.server.name}

        leave_msg = str(self.handler.get_var(member.server.id, "leavemsg"))

        for trigg, repl in replacement_logic.items():
            leave_msg = leave_msg.replace(trigg, repl)

        log_c = await self.handle_log_channel(member.server)

        await self.client.send_message(log_c, leave_msg)
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
        pass
        
        #await self.client.wait_until_ready()

        #log.info("Checking server vars...")
        #for server in self.client.servers:
        #    self.handler._check_server_vars(server.id, delete_old=False)
        #log.info("Finished checking server data.")


class NanoPlugin:
    _name = "Moderator"
    _version = "0.2.4"

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
