# coding=utf-8
import time
import configparser
from datetime import datetime

from discord import Embed, Colour

from data.stats import MESSAGE, HELP, WRONG_ARG
from data.utils import is_valid_command

# Template: {"desc": "", "use": None, "alias": None},


# OBSOLETE HELP MESSAGES FOR VOICE

# "_music join": {"desc": "Joins a voice channel.", "use": "[command] [channel name]", "alias": None},
# "_music leave": {"desc": "Leaves a music channel.", "use": None, "alias": None},
# "_music volume": {"desc": "Returns the current volume or sets one.", "use": "[command] [volume 0-150]", "alias": None},
# "_music pause": {"desc": "Pauses the current song.", "use": None, "alias": None},
# "_music resume": {"desc": "Resumes the paused song", "use": None, "alias": None},
# "_music skip": {"desc": "Skips the current song.", "use": None, "alias": "_music stop"},
# "_music stop": {"desc": "Skips the current song", "use": None, "alias": "_music skip"},
# "_music playing": {"desc": "Gives you info about the current song.", "use": None, "alias": None},
# "_music help": {"desc": "Some help with all the music commands.", "use": None, "alias": None},

commands = {
    "_cmds": {"desc": "Displays a link to the wiki page where all commands are listed.", "use": None, "alias": "_commands"},
    "_commands": {"desc": "Displays a link to the wiki page where all commands are listed.", "use": None, "alias": "_cmds"},
    "_help": {"desc": "This is here.", "use": None, "alias": None},
    "_suggest": {"desc": "Sends a message to the developer", "use": "[command] [message]", "alias": None},
    "_bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "nano.bug"},
    "nano.bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "_bug"},
    "_tos": {"desc": "Displays more info about the Terms of Service", "use": None, "alias": None},
}

valid_commands = commands.keys()


parser = configparser.ConfigParser()
parser.read("settings.ini")

OWNER_ID = parser.get("Settings", "ownerid")
DEVSERVER_ID = parser.get("Dev", "server")


def save_submission(sub):
    with open("data/submissions.txt", "a") as subs:
        subs.write(str(sub) + "\n" + ("-" * 20))
        subs.write("\n\n")


def get_valid_commands(plugin):
    try:
        return plugin.commands
    except AttributeError:
        return None


class Help:
    def __init__(self, **kwargs):
        self.loop = kwargs.get("loop")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.last_times = {}
        self.commands = {}

    def get_command_info(self, cmd, prefix, lang):
        # Normal commands
        cmd1 = self.commands.get(str(cmd.replace(prefix, "_").strip(" ")))
        if cmd1 is not None:
            cmd_name = cmd.replace(prefix, "")

            description = cmd1.get("desc")

            use = cmd1.get("use")
            if use:
                use = cmd1.get("use").replace("[command]",
                                              prefix + cmd_name if not cmd_name.startswith("nano.") else cmd_name)

            alias = cmd1.get("alias")
            if alias:
                alias = cmd1.get("alias").replace("_", prefix)

            emb = Embed(colour=Colour.blue())

            emb.add_field(name=self.trans.get("MSG_HELP_DESC", lang), value=description)

            if use:
                emb.add_field(name=self.trans.get("MSG_HELP_USE", lang), value=use, inline=False)
            if alias:
                emb.add_field(name=self.trans.get("MSG_HELP_ALIASES", lang), value=alias, inline=False)

            self.stats.add(HELP)
            return "**{}**".format(cmd_name), emb

        if not cmd1:
            self.stats.add(WRONG_ARG)
            return None, None

    async def on_plugins_loaded(self):
        # Collect all commands
        plugins = [a.get("plugin") for a in self.nano.plugins.values() if a.get("plugin")]
        cmdslist = [get_valid_commands(b) for b in plugins if get_valid_commands(b)]

        for pl_list in cmdslist:
            for command, info in pl_list.items():
                # Valid help dict?
                if commands and info:
                    self.commands[command] = info

    async def on_message(self, message, *_, **kwargs):
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

        # Bare !help
        if message.content.strip(" ") == (prefix + "help"):
            await message.channel.send(trans.get("MSG_HELP", lang).replace("_", prefix))

            self.stats.add(HELP)

        # !cmds or !commands
        elif startswith(prefix + "cmds", prefix + "commands"):
            await message.channel.send(trans.get("MSG_HELP_CMDWEB", lang))

            self.stats.add(HELP)

        # !help simple
        elif startswith(prefix + "help simple"):
            await message.channel.send(trans.get("MSG_HELP_SIMPLE", lang).replace("_", prefix))

            self.stats.add(HELP)

        # !help [command]
        elif startswith(prefix + "help"):
            search = str(message.content)[len(prefix + "help "):]

            # Allows for !help ping AND !help !ping
            if search.startswith(prefix) or search.startswith("nano."):
                name, embed = self.get_command_info(search, prefix, lang)

                if name:
                    await message.channel.send(name, embed=embed)
                else:
                    await message.channel.send(trans.get("MSG_HELP_CMDNOTFOUND", lang).replace("_", prefix))

            else:
                name, embed = self.get_command_info(prefix + search, prefix, lang)

                if name:
                    await message.channel.send(name, embed=embed)
                else:
                    await message.channel.send(trans.get("MSG_HELP_CMDNOTFOUND", lang).replace("_", prefix))

                self.stats.add(HELP)

        # !notifydev
        # Not translated
        elif startswith(prefix + "suggest"):
            report = message.content[len(prefix + "suggest "):].strip(" ")

            # Disallow empty reports
            if not report:
                await message.channel.send(trans.get("MSG_REPORT_EMPTY", lang))
                return

            # Cooldown implementation
            if not self.last_times.get(message.author.id):
                self.last_times[message.author.id] = time.time()
            else:
                # 300 seconds --> 5 minute cooldown
                if (time.time() - self.last_times[message.author.id]) < 300:
                    await message.channel.send(trans.get("MSG_REPORT_RATELIMIT", lang))
                    return

                else:
                    self.last_times[message.author.id] = time.time()

            dev_server = self.client.get_guild(self.nano.dev_server)
            owner = dev_server.get_member(self.nano.owner_id)
            # Timestamp
            ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            # Reused stuff
            name = message.author.name
            u_id = message.author.id
            guild_name = message.guild.name
            guild_id = message.guild.id
            guild_owner = message.guild.owner
            guild_members = message.guild.member_count
            owner_info = "Yes" if message.author == guild_owner else "{}:{}".format(guild_owner.id, guild_owner.id)

            # 'Compiled' report
            # NOT TRANSLATED!!
            comp = "Suggestion from {} ({}):\n```{}```\n**__Timestamp__**: `{}`" \
                   "\n**__Server__**: `{}` ID:{} ({} members)\n**__Server Owner__**: {}" \
                   "\n**Language used:** `{}`".format(name, u_id, report, ts, guild_name, guild_id, guild_members, owner_info, lang)

            # Saves the submission
            to_file = "{0}\nSuggestion from {1}:{2}\nMessage: {3}\n" \
                      "Server: {4}:{5} with {6} members\nServer owner: {7}\n" \
                      "Language used: {}\n{0}".format("-" * 10, name, u_id, report, guild_name, guild_id, guild_members, owner_info, lang)

            save_submission(to_file)
            await owner.send(comp)

            await message.channel.send(trans.get("MSG_REPORT_THANKS", lang))

        # !bug
        elif startswith(prefix + "bug"):
            await message.channel.send(trans.get("MSG_BUG", lang))

        # !tos
        elif startswith(prefix + "tos"):
            await message.channel.send(trans.get("MSG_TOS", lang))


class NanoPlugin:
    name = "Help Commands"
    version = "29"

    handler = Help
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
