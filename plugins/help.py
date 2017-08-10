# coding=utf-8
import time
import configparser
from datetime import datetime

from discord import Message, Embed, Colour, utils

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
}

valid_commands = commands.keys()


parser = configparser.ConfigParser()
parser.read("settings.ini")

OWNER_ID = parser.get("Settings", "ownerid")
DEVSERVER_ID = parser.get("Dev", "server")


async def save_submission(sub):
    with open("data/submissions.txt", "a") as subs:
        subs.write(str(sub) + "\n" + ("-" * 20))


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
        client = self.client
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(message, Message)

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
            typ = "Suggestion"

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


            dev_server = utils.get(client.guilds, id=self.nano.dev_server)
            # Timestamp
            ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            # 'Compiled' report
            # NOT TRANSLATED!!
            comp = "{} from {} ({}):\n```{}```\n**__Timestamp__**: `{}`\n**__Server__**: `{}` ({} members)\n" \
                   "**__Server Owner__**: {}\n**Language used:** `{}`".format(typ, message.author.name, message.author.id, report, ts,
                                                     message.guild.name, message.guild.member_count,
                                                     "Yes" if message.author.id == message.guild.owner.id else message.guild.owner.id, lang)

            # Saves the submission
            await save_submission(comp.replace(message.author.mention, "{} ({})\n".format(message.author.name, message.author.id)))

            await client.send_message(dev_server.owner, comp)
            await message.channel.send(trans.get("MSG_REPORT_THANKS", lang))

        # !bug
        elif startswith(prefix + "bug"):
            await message.channel.send(trans.get("MSG_BUG", lang))


class NanoPlugin:
    name = "Help Commands"
    version = "27"

    handler = Help
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
