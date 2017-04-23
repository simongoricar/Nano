# coding=utf-8
import time
import asyncio
from datetime import datetime
from discord import Message, utils, Embed, Colour
from data.utils import is_valid_command
from data.stats import MESSAGE, HELP, WRONG_ARG


# Strings
help_nano = """**Hey, I'm Nano!**

To get familiar with simple commands, type `>help simple`.
If you want specific info about a command, do `>help [command]`.

Or you could just simply take a look at the wiki page: http://nanobot.pw/commands.html
If you are an admin/server owner and want to set up your server for Nano, type `>setup`.
It is highly recommended that you join the "official" Nano server for announcements and help : https://discord.gg/FZJB6UJ
"""

help_simple = """`_hello` - Welcomes you or the mentioned person.
`_randomgif` - Posts a random gif from Giphy
`_roll number` - rolls a random number
`_wiki term` - gives you a description of a term from Wikipedia
`_urban term` - gives you a description of a term from Urban Dictionary
`_decide option|option...` - decides between your options so you don't have to
`_tf item_name` - item prices from backpack.tf
`_steam user_id` - search users on Steam

These are just a few of some of the simpler commands. For more info about each command, use `_help command` or type `_cmds` to look at the wiki page with all the commands."""

nano_bug = "Found a bug? Please report it to me, (**DefaltSimon**) on Discord.\nYou can find me here: https://discord.gg/FZJB6UJ"

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
    "_notifydev": {"desc": "Sends a message to the developer", "use": "[command] [message]", "alias": "_suggest"},
    "_suggest": {"desc": "Sends a message to the developer", "use": "[command] [message]", "alias": "_notifydev"},
    "_bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "nano.bug"},
    "nano.bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "_bug"},
}

valid_commands = commands.keys()


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

        self.last_times = {}
        self.commands = {}

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
        assert isinstance(message, Message)
        client = self.client

        prefix = kwargs.get("prefix")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        # A shortcut
        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # !help and @Nanos
        if message.content.strip(" ") == (prefix + "help"):
            await client.send_message(message.channel, help_nano.replace(">", prefix))

            self.stats.add(HELP)

        # @Nano help
        elif self.client.user in message.mentions:
            un_mentioned = str(message.content[21:])
            if un_mentioned == "" or un_mentioned == " ":
                await client.send_message(message.channel, help_nano.replace(">", prefix))

            self.stats.add(HELP)

        # !cmds or !commands
        elif startswith(prefix + "cmds", prefix + "commands"):
            await client.send_message(message.channel, "Commands and their explanations can be found here: "
                                                       "http://nanobot.pw/commands.html")

            self.stats.add(HELP)

        # !help simple
        elif startswith(prefix + "help simple"):
            await client.send_message(message.channel, help_simple.replace("_", prefix))

            self.stats.add(HELP)

        # !help [command]
        elif startswith(prefix + "help"):
            search = str(message.content)[len(prefix + "help "):]

            self.stats.add(HELP)

            def get_command_info(cmd):
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

                    emb.add_field(name="Description", value=description)

                    if use:
                        emb.add_field(name="Use", value=use, inline=False)
                    if alias:
                        emb.add_field(name="Aliases", value=alias, inline=False)

                    self.stats.add(HELP)
                    return "**{}**".format(cmd_name), emb

                if not cmd1:
                    self.stats.add(WRONG_ARG)
                    return None, None

            # Allows for !help ping AND !help !ping
            if search.startswith(prefix) or search.startswith("nano."):
                name, embed = get_command_info(search)

                if name:
                    await client.send_message(message.channel, name, embed=embed)

                else:
                    await client.send_message(message.channel, "Command could not be found.\n"
                                                               "**(Use: `>help [command]`)**".replace(">", prefix))

            else:
                name, embed = get_command_info(prefix + search)

                if name:
                    await client.send_message(message.channel, name, embed=embed)

                else:
                    await client.send_message(message.channel, "Command could not be found.\n"
                                                               "**(Use: `>help [command]`)**".replace(">", prefix))

        # !notifydev
        elif startswith(prefix + "notifydev", prefix + "suggest"):
            # Cooldown implementation
            if not self.last_times.get(message.author.id):
                self.last_times[message.author.id] = time.time()
            else:
                # 300 seconds --> 5 minute cooldown
                if (time.time() - self.last_times[message.author.id]) < 300:
                    await client.send_message(message.channel, "You are being rate limited. Try again in 5 minutes.")
                    return

                else:
                    self.last_times[message.author.id] = time.time()

            if startswith(prefix + "notifydev"):
                report = message.content[len(prefix + "notifydev "):]
                typ = "Report"

            elif startswith(prefix + "suggest"):
                report = message.content[len(prefix + "suggest "):]
                typ = "Suggestion"

            else:
                return

            dev_server = utils.get(client.servers, id=self.nano.dev_server)

            # Timestamp
            ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            # 'Compiled' report
            comp = "{} from {} ({}):\n```{}```\n**__Timestamp__**: `{}`\n**__Server__**: `{}` ({} members)\n" \
                   "**__Server Owner__**: {}".format(typ, message.author.name, message.author.id, report, ts,
                                                     message.channel.server.name, message.channel.server.member_count,
                                                     "Yes" if message.author.id == message.channel.server.owner.id
                                                     else message.channel.server.owner.id)

            # Saves the submission
            await save_submission(comp.replace(message.author.mention, "{} ({})\n".format(message.author.name, message.author.id)))

            await client.send_message(dev_server.owner, comp)
            await client.send_message(message.channel, "**Thank you** for your *{}*.".format(
                "submission" if typ == "Report" else "suggestion"))

        # !bug
        elif startswith(prefix + "bug"):
            await client.send_message(message.channel, nano_bug.replace("_", prefix))


class NanoPlugin:
    name = "Help Commands"
    version = "0.2.5"

    handler = Help
    events = {
        "on_message": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
