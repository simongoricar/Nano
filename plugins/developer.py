# coding=utf-8
import configparser
import logging
import os
import subprocess
import sys
from asyncio import sleep
from datetime import datetime
from random import shuffle
from shutil import copy2

from discord import Message, Game, utils, Embed, Colour, Object

from data.stats import MESSAGE
from data.utils import is_valid_command, log_to_file, StandardEmoji

#######################
# NOT TRANSLATED
#######################

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("settings.ini")


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
    "nano.invite",
    "with you all",
    "party hard (▀̿Ĺ̯▀̿ ̿)",
    "nanobot.pw",
    ""
]

commands = {
    "nano.dev": {"desc": "Developer commands, resticted."},
    "nano.playing": {"desc": "Restricted to owner, changes 'playing' status.", "use": "[command] [status]", "alias": None},
    "nano.restart": {"desc": "Restricted to owner, restarts down the bot.", "use": "[command]", "alias": None},
    "nano.reload": {"desc": "Restricted to owner, reloads all settings from config file.", "use": None, "alias": "_reload"},
    "nano.kill": {"desc": "Restricted to owner, shuts down the bot.", "use": "[command]", "alias": None},
}

valid_commands = commands.keys()


class StatusRoller:
    def __init__(self, client, time=21600):  # 6 Hours
        self.time = time
        self.client = client

        log.info("Status changer enabled")

    async def change_status(self, name):
        log.debug("Changing status to {}".format(name))
        log_to_file("Changing status to {}".format(name))

        await self.client.change_presence(game=Game(name=str(name)))

    async def run(self):
        await self.client.wait_until_ready()

        await self.change_status(initial_status)

        # Shuffle the game list
        shuffle(game_list)
        await sleep(self.time)

        while not self.client.is_closed:
            for game in game_list:

                if self.client.is_closed:
                    break

                await self.change_status(game)
                await sleep(self.time)

            shuffle(game_list)

        log_to_file("Exited status changer")


class BackupManager:
    def __init__(self, time=86400, keep_backup_every=3):  # 86400 seconds = one day (backup is executed once a day)
        log.info("Backup enabled: redis")
        self.s_path = os.path.join("data", "data.rdb")
        self.s_path_d = os.path.join("backup", "data.rdb.bak")

        if not os.path.isdir("backup"):
            os.mkdir("backup")

        self.time = int(time)
        self.keep_every = int(keep_backup_every)
        self.keep_buffer = int(self.keep_every)

        self.running = True

    def stop(self):
        self.running = False

    def backup(self, make_dated_backup=False):
        if not self.running:
            return

        if not os.path.isdir("backup"):
            os.mkdir("backup")

        # Make a dated backup if needed
        if make_dated_backup:
            if not os.path.isdir(os.path.join("backup", "full")):
                os.mkdir(os.path.join("backup", "full"))

            buff_name = "data{}.rdb".format(str(datetime.now().strftime("%d-%B-%Y_%H-%M-%S")))
            f_name = os.path.join("backup", "full", buff_name)
            copy2(self.s_path, f_name)
            log.info("Created a dated backup.")

        try:
            copy2(self.s_path, self.s_path_d)
        except FileNotFoundError:
            pass

    def manual_backup(self, make_dated_backup=True):
        self.backup(make_dated_backup)
        log.info("Manual backup complete")

    async def start(self):
        while self.running:
            # Run the backup every day
            await sleep(self.time)

            # Full backup counter
            self.keep_buffer -= 1

            if self.keep_buffer <= 0:
                dated_backup = True
                self.keep_buffer = int(self.keep_every)
            else:
                dated_backup = False

            log_to_file("Creating a backup...")
            self.backup(dated_backup)


class DevFeatures:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.handler = kwargs.get("handler")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

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

        lang = kwargs.get("lang")

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # Global owner filter

        if not self.handler.is_bot_owner(message.author.id):
            await client.send_message(message.channel, self.trans.get("PERM_OWNER", lang))
            return


        # nano.dev.get_servers
        if startswith("nano.dev.get_servers"):
            # fixme message is still too long
            servers = ["{} ({} u) - `{}`".format(srv.name, srv.member_count, srv.id) for srv in client.servers]

            final = ["\n".join(a) for a in [servers[i:i+1000] for i in range(0, len(servers), 1000)]]

            for chunk in final:
                await client.send_message(message.channel, chunk)

        # nano.dev.server_info [id]
        elif startswith("nano.dev.server_info"):
            s_id = message.content[len("nano.dev.server_info "):]

            srv = utils.find(lambda s: s.id == s_id, client.servers)

            if not srv:
                await client.send_message(message.channel, "Error. " + StandardEmoji.CROSS)
                return

            nano_data = self.handler.get_server_data(srv)
            to_send = "{}\n```css\nMember count: {}\nChannels: {}\nOwner: {}```\n" \
                      "*Settings*: ```{}```".format(srv.name, srv.member_count, ",".join([ch.name for ch in srv.channels]), srv.owner.name, nano_data)

            await client.send_message(message.channel, to_send)

        # nano.dev.test_error
        elif startswith("nano.dev.test_exception"):
            int("abcdef")

        # nano.dev.embed_test
        elif startswith("nano.dev.embed_test"):
            emb = Embed(title="Stats", colour=Colour.darker_grey())
            emb.add_field(name="Messages Sent", value="sample messages")

            await client.send_message(message.channel, "Stats", embed=emb)

        # nano.dev.backup
        elif startswith("nano.dev.backup"):
            self.backup.manual_backup()
            await client.send_message(message.channel, "Backup completed " + StandardEmoji.PERFECT)

        # nano.dev.leave_server
        elif startswith("nano.dev.leave_server"):
            sid = int(message.content[len("nano.dev.leave_server "):])

            srv = Object(id=sid)
            await client.leave_server(srv)
            await client.send_message(message.channel, "Left {}".format(srv.id))

        # nano.dev.tf.reload
        elif startswith("nano.dev.tf.clean"):
            self.nano.get_plugin("tf2").get("instance").tf.request()

            await client.send_message(message.channel, "Re-downloaded data...")

        # nano.dev.plugin.reload
        elif startswith("nano.dev.plugin.reload"):
            name = str(message.content)[len("nano.dev.plugin.reload "):]

            v_old = self.nano.get_plugin(name).get("plugin").NanoPlugin.version
            s = await self.nano.reload_plugin(name)
            v_new = self.nano.get_plugin(name).get("plugin").NanoPlugin.version

            if s:
                await client.send_message(message.channel, "Successfully reloaded **{}**\n"
                                                           "From version *{}* to *{}*.".format(name, v_old, v_new))
            else:
                await client.send_message(message.channel, "Something went wrong, check the logs.")

        # nano.dev.servers.clean
        elif startswith("nano.dev.servers.clean"):
            self.handler.delete_server_by_list([s.id for s in self.client.servers])

        elif startswith("nano.dev.servers.leave"):
            s_id = int(str(message.content)[len("nano.dev.server.leave "):])
            serv = Object(id=s_id)

            if not serv:
                await client.send_messsage(message.channel, "Could not leave server: does not exist")
            else:
                await client.leave_server(serv)
                await client.send_message(message.channel, StandardEmoji.PERFECT + " Left {}".format(serv.id))

        # nano.reload
        elif startswith("nano.reload"):
            self.handler.reload()

            await client.send_message(message.channel, "Refreshed server data {} {}".format(StandardEmoji.MUSCLE, StandardEmoji.SMILE))

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

            await client.send_message(message.channel, "Status changed " + StandardEmoji.THUMBS_UP)

        # nano.dev.translations.reload
        elif startswith("nano.dev.translations.reload"):
            self.trans.reload_translations()

            await client.send_message(message.channel, StandardEmoji.PERFECT)

        # nano.dev.announce
        elif startswith("nano.dev.announce"):
            await client.send_message(message.channel, "Sending...")
            ann = message.content[len("nano.dev.announce "):]

            s = []
            for g in self.client.servers:
                try:
                    await client.send_message(g.default_channel, ann)
                    log_to_file("Sending announcement for {}".format(g.name))
                    s.append(g.name)
                except:
                    pass


            await client.send_message(message.channel, "Sent to {}".format("\n".join(s)))
            await client.send_message(message.channel, "Sent :ok_hand:".format())

    async def on_ready(self):
        self.loop.create_task(self.backup.start())
        self.loop.create_task(self.roller.run())

    async def on_shutdown(self):
        # Make redis BGSAVE data
        self.handler.bg_save()

        if self.mode == "restart":
            # Launches a new instance of Nano...
            if sys.platform == "win32":
                subprocess.Popen("startbot.bat")
            else:
                subprocess.Popen(os.path.abspath("startbot.sh"), shell=True)


class NanoPlugin:
    name = "Developer Commands"
    version = "0.2.4"

    handler = DevFeatures
    events = {
        "on_message": 10,
        "on_ready": 5,
        "on_shutdown": 15,
        # type : importance
    }
