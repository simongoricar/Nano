# coding=utf-8
import time
from datetime import datetime

from discord import Embed, Colour

from data.stats import MESSAGE, HELP, WRONG_ARG
from data.utils import is_valid_command
from data.confparser import get_settings_parser

# Template: {"desc": ""},

commands = {
    "_cmds": {"desc": "Displays a link to the wiki page where all commands are listed.\nTo link directly to a specific category, use `_cmds category_name` (for example: `_cmds admin`)", "alias": "_commands"},
    "_commands": {"desc": "Displays a link to the wiki page where all commands are listed.\nTo link directly to a specific category, use `_commands category_name` (for example: `_commands admin`)", "alias": "_cmds"},
    "_help": {"desc": "This is here."},
    "_suggest": {"desc": "Sends a message to the developer", "use": "[command] [message]"},
    "_bug": {"desc": "Place where you can report bugs.", "alias": "nano.bug"},
    "nano.bug": {"desc": "Place where you can report bugs.", "alias": "_bug"},
    "_tos": {"desc": "Displays more info about the Terms of Service"},
}

valid_commands = commands.keys()

parser = get_settings_parser()

OWNER_ID = parser.get("Settings", "ownerid")
DEVSERVER_ID = parser.get("Dev", "server")

BASE_CMDS_LINK = "http://nanobot.pw/commands.html"
cmd_links = {
    "useful": "#useful",
    "ful": "#fun",
    "help": "#help",
    "games": "#games",
    "reminder": "#reminders",
    "reminders": "#reminders",
    "other": "#other",
    "misc": "#other",
    "mod": "#moderator",
    "moderator": "#moderator",
    "admin": "#admin"
}


def save_submission(sub):
    with open("data/submissions.txt", "a") as subs:
        subs.write(str(sub) + "\n" + ("-" * 20))
        subs.write("\n\n")


def get_valid_commands(plugin):
    return getattr(plugin, "commands", None)


class Help:
    def __init__(self, **kwargs):
        self.loop = kwargs.get("loop")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.last_times = {}
        self.commands = {}

    def get_command_info(self, cmd_name, prefix, lang) -> tuple:
        # Normal commands
        cmd = self.commands.get(str(cmd_name.replace(prefix, "_").strip(" ")))

        if cmd:
            emb = Embed(colour=Colour.blue())

            cmd_name = cmd_name.replace(prefix, "")

            description = cmd.get("desc")
            if description:
                description = description.replace("{p}", prefix)
                emb.add_field(name=self.trans.get("MSG_HELP_DESC", lang), value=description)

            use = cmd.get("use")
            if use:
                use = cmd.get("use").replace("[command]", prefix + cmd_name if not cmd_name.startswith("nano.") else cmd_name)
                emb.add_field(name=self.trans.get("MSG_HELP_USE", lang), value=use, inline=False)

            alias = cmd.get("alias")
            if alias:
                alias = cmd.get("alias").replace("_", prefix)
                emb.add_field(name=self.trans.get("MSG_HELP_ALIASES", lang), value=alias, inline=False)

            self.stats.add(HELP)
            return "**{}**".format(cmd_name), emb

        if not cmd:
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
            if startswith(prefix + "cmds"):
                arg = message.content[len(prefix + "cmds "):].lower()
            else:
                arg = message.content[len(prefix + "commands "):].lower()

            if not arg or not cmd_links.get(arg):
                await message.channel.send(trans.get("MSG_HELP_CMDWEB", lang))
            else:
                ending = cmd_links.get(arg)
                full_link = BASE_CMDS_LINK + ending

                await message.channel.send(trans.get("MSG_HELP_CMD_SPEC", lang).format(full_link))


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

            # :P
            if report in ("hi", "hello"):
                await message.channel.send(trans.get("MSG_REPORT_EE_THX", lang))
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
                      "Language used: {8}\n{0}".format("-" * 10, name, u_id, report, guild_name, guild_id, guild_members, owner_info, lang)

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
    version = "30"

    handler = Help
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
