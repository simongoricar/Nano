# coding=utf-8
import os
import sys
import subprocess
import logging
import traceback
from shutil import copy2
from asyncio import sleep
from random import shuffle
from discord import Message, Game, Member, utils, errors
from data.serverhandler import ServerHandler
from data.utils import is_valid_command, log_to_file
from data.stats import MESSAGE


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


initial_status = "Hi there!"

game_list = [
    "(formerly AyyBot)",
    "HI MOM!",
    "@Nano",
    "fun games",
    "with discord.py",
    "with DefaltSimon",
    "with Discord",
    "with python",
    "get a 'nano.invite'"
]


valid_commands = [
    "nano.dev.", "nano.playing", "nano.reload", "nano.restart", "nano.kill"
]


class StatusRoller:
    def __init__(self, client, time=10800):  # 3 Hours
        self.time = time
        self.client = client

        log.info("Status roller enabled")

    async def change_status(self, name):
        log.info("Changing status to {}".format(name))
        await self.client.change_presence(game=Game(name=str(name)))

    async def run(self):
        await self.client.wait_until_ready()

        await self.change_status(initial_status)

        shuffle(game_list)
        await sleep(self.time)

        while not self.client.is_closed:
            for game in game_list:

                if self.client.is_closed:
                    break

                await self.change_status(game)
                await sleep(self.time)

            shuffle(game_list)

        log_to_file("Exited status roller")


class BackupManager:
    def __init__(self, time=86400):  # 86400 seconds = one day (backup is executed once a day)
        log.info("Backup enabled")

        if not os.path.isdir("backup"):
            os.mkdir("backup")

        self.servers = os.path.join("backup", "servers.yml.bak")
        self.stats = os.path.join("backup", "stats.yml.bak")

        self.servers_double = os.path.join("backup", "servers.yml.bak2")
        self.stats_double = os.path.join("backup", "stats.yml.bak2")

        self.real_servers = os.path.join("data", "servers.yml")
        self.real_stats = os.path.join("data", "stats.yml")

        self.time = int(time)

        self.running = True

    def stop(self):
        self.running = False

    async def backup(self):
        if not self.running:
            return

        if not os.path.isdir("backup"):
            os.mkdir("backup")

        # Create double backups
        copy2(self.servers, self.servers_double)
        copy2(self.stats, self.stats_double)

        copy2(self.real_servers, self.servers)
        copy2(self.real_stats, self.stats)

    def manual_backup(self):
        self.backup()
        log.info("Manual backup complete")

    async def start(self):
        while self.running:
            # Run the backup every day
            await sleep(self.time)

            log_to_file("Creating a backup...")
            await self.backup()


class DevFeatures:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        self.backup = BackupManager()
        self.roller = StatusRoller(self.client)

        self.mode = None

    async def on_message(self, message, **kwargs):
        if not is_valid_command(message.content, valid_commands, prefix=kwargs.get("prefix")):
            return
        else:
            self.stats.add(MESSAGE)

        assert isinstance(message, Message)
        client = self.client

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # Global owner filter
        assert isinstance(self.handler, ServerHandler)

        if not self.handler.is_bot_owner(message.author.id):
            # /todo/ fix
            await client.send_message(message.channel, "You are not permitted to use this feature. (must be bot owner)")
            return


        # nano.dev.get_servers
        if startswith("nano.dev.get_servers"):
            servers = ["{} ({} u) - `{}`".format(srv.name, srv.member_count, srv.id) for srv in client.servers]

            final = ["\n".join(a) for a in [servers[i:i+1500] for i in range(0, len(servers), 1500)]]

            for chunk in final:
                await client.send_message(message.channel, chunk)

        # nano.dev.server_info [id]
        elif startswith("nano.dev.server_info"):
            id = message.content[len("nano.dev.server_info "):]

            srv = utils.find(lambda s: s.id == id, client.servers)

            if not srv:
                await client.send_message(message.channel, "Error. :x:")
                return

            nano_data = self.handler.get_server_data(srv.id)
            to_send = "{}\n```css\nMember count: {}\nChannels: {}\nOwner: {}```\n" \
                      "Nano settings: ```{}```".format(srv.name, srv.member_count, ",".join([ch.name for ch in srv.channels]), srv.owner.name, nano_data)

            await client.send_message(message.channel, to_send)

        # nano.dev.test_error
        elif startswith("nano.dev.test_error"):
            int("abcdef")

        # nano.reload
        elif startswith("nano.reload"):
            self.handler.reload()

            await client.send_message(message.channel, "Refreshed :muscle: :smile:")

        # nano.restart
        elif startswith("nano.restart"):
            m = await client.send_message(message.channel, "Restarting...")

            await client.send_message(message.channel, "**DED**")
            await client.delete_message(m)

            await client.logout()

            self.mode = "restart"
            return "shutdown"

        # nano.kill
        elif startswith("nano.kill"):
            await client.send_message(message.channel, "**DED**")

            await client.logout()

            self.mode = "exit"
            return "shutdown"

        # nano.playing
        elif startswith("nano.playing"):
            status = message.content[len("nano.playing "):]

            await client.change_presence(game=Game(name=str(status)))

            await client.send_message(message.channel, "Status changed :+1:")

    async def on_ready(self):
        await self.backup.start()
        await self.roller.run()

    async def on_shutdown(self):

        if self.mode == "restart":
            # Launches a new instance of Nano...
            if sys.platform == "win32":
                subprocess.Popen("startbot.bat")
            else:
                subprocess.Popen(os.path.abspath("startbot.sh"), shell=True)

    @staticmethod
    async def on_error(event, *args, **kwargs):
        e_type, _, _ = sys.exc_info()

        # Ignore Forbidden errors (but log them anyways)
        if e_type == errors.Forbidden:
            log.warn("Forbidden: 403")

            if isinstance(args[0], Message):
                log_to_file("Forbidden 403. Server: {}, channel: {}".format(args[0].server, args[0].channel))

            elif isinstance(args[0], Member):
                log_to_file("Forbidden 403. Server: {}, member: {}:{}".format(args[0].server, args[0].name, args[0].id))

            else:
                log_to_file("Forbidden 403. Unknown instance: {}:{}".format(type(args[0]), args[0].__dict__))

        else:
            print('Ignoring exception in {}'.format(event), file=sys.stderr)
            traceback.print_exc()


class NanoPlugin:
    _name = "Developer Commands"
    _version = "0.2.1"

    handler = DevFeatures
    events = {
        "on_message": 10,
        "on_ready": 5,
        "on_shutdown": 15,
        "on_error": 5,
        # type : importance
    }
