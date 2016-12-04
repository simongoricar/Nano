# coding=utf-8
from datetime import datetime
from discord import Message, utils, Embed, Colour
from data.utils import threaded, is_valid_command
from data.stats import MESSAGE, HELP, WRONG_ARG


# Strings
help_nano = """**Hey, I'm Nano!**

To get familiar with simple commands, type `>help simple`.
If you want specific info about a command, do `>help command`.

Or you could just simply take a look at my wiki page: https://github.com/DefaltSimon/Nano/wiki/Commands-list
If you are an admin and want to set up your server for Nano, type `>getstarted`.
If you need additional help, you can visit "my official server" : https://discord.gg/FZJB6UJ
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
cmd_help_normal = {
    "_help": {"desc": "This is here.", "use": None, "alias": None},
    "_hello": {"desc": "Welcomes a **mentioned** person, or if no mentions are present, you.", "use": "[command] [mention]", "alias": None},
    "_uptime": {"desc": "Tells you for how long I have been running.", "use": None, "alias": None},
    "_randomgif": {"desc": "Sends a random gif from Giphy.", "use": None, "alias": None},
    "_8ball": {"desc": "Answers your questions. 8ball style.", "use": "[command] [question]", "alias": None},
    "_wiki": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "[command] [word]", "alias": "_define"},
    "_define": {"desc": "Gives you the definition of a word from Wikipedia.", "use": "[command] [word]", "alias": "_wiki"},
    "_urban": {"desc": "Gives you the definition of a word from Urban Dictionary.", "use": "[command] [word]", "alias": None},
    "_avatar": {"desc": "Gives you the avatar url of a mentioned person", "use": "[command] [mention or name]", "alias": None},
    "_ping": {"desc": "Just to check if I'm alive. fyi: I love ping-pong.", "use": None, "alias": None},
    "_roll": {"desc": "Replies with a random number in range from 0 to your number.", "use": "[command] [number]", "alias": None},
    "_nano": {"desc": "A little info about me.", "use": None, "alias": "nano.info"},
    "_github": {"desc": "Link to my project on GitHub.", "use": None, "alias": None},
    "_decide": {"desc": "Decides between different choices so you don't have to.", "use": "[command] word1|word2|word3|...", "alias": None},
    "_cmd list": {"desc": "Returns a server-specific command list.", "use": None, "alias": None},
    "_cat": {"desc": "I love cats. And this is a gif of a cat.", "use": None, "alias": None},
    "_kappa": {"desc": "I couldn't resist it.", "use": None, "alias": None},
    "_johncena": {"desc": "I have to remove this someday. dun dun dun dun, dun dun dun dun", "use": None, "alias": None},
    "_rip": {"desc": "Rest in peperoni, man.", "use": "[command] [mention]", "alias": None},
    "ayy lmao": {"desc": "Yes, it's the ayy lmao meme.", "use": None, "alias": None},
    "_music join": {"desc": "Joins a voice channel.", "use": "[command] [channel name]", "alias": None},
    "_music leave": {"desc": "Leaves a music channel.", "use": None, "alias": None},
    "_music volume": {"desc": "Returns the current volume or sets one.", "use": "[command] [volume 0-150]", "alias": None},
    "_music pause": {"desc": "Pauses the current song.", "use": None, "alias": None},
    "_music resume": {"desc": "Resumes the paused song", "use": None, "alias": None},
    "_music skip": {"desc": "Skips the current song.", "use": None, "alias": "_music stop"},
    "_music stop": {"desc": "Skips the current song", "use": None, "alias": "_music skip"},
    "_music playing": {"desc": "Gives you info about the current song.", "use": None, "alias": None},
    "_music help": {"desc": "Some help with all the music commands.", "use": None, "alias": None},
    "_prefix": {"desc": "No use whatsoever, but jk here you have it.", "use": None, "alias": None},
    "_vote": {"desc": "One up for your choice, if there's a vote running.", "use": "[command] [choice]", "alias": None},
    "_status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "nano.status"},
    "nano.status": {"desc": "Displays current status: server, user and channel count.", "use": None, "alias": "_status"},
    "_stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "nano.stats"},
    "nano.stats": {"desc": "Some stats like message count and stuff like that.", "use": None, "alias": "_stats"},
    "_bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "nano.bug"},
    "nano.bug": {"desc": "Place where you can report bugs.", "use": None, "alias": "_bug"},
    "_feature": {"desc": "Place where you can submit your ideas for this bot", "use": None, "alias": None},
    "nano.info": {"desc": "A little info about me.", "use": None, "alias": "_ayybot"},
    "nano.prefix": {"desc": "Helps you figure out the prefix.", "use": None, "alias": None},
    "_changes": {"desc": "A list of changes in the recent versions.", "use": None, "alias": "_changelog"},
    "_changelog": {"desc": "A list of changes in the recent versions.", "use": None, "alias": "_changes"},
    "_steam": {"desc": "Searches for the specified steam id.\nSubcommands: 'steam user', 'steam games', 'steam friends'", "use": "[command] [end of user url/id]", "alias": None},
    "_steam user": {"desc": "Searches for general info about the user.", "use": "[command] [end of user url/id]", "alias": None},
    "_steam games": {"desc": "Searches for all owned games in user's account.", "use": "[command] [end of user url/id]", "alias": None},
    "_steam friends": {"desc": "Searches for all friends that the user has.", "use": "[command] [end of user url/id]", "alias": None},
    "_mc": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]", "alias": "_minecraft"},
    "_minecraft": {"desc": "Searches for items and displays their details", "use": "[command] [item name or id:meta]", "alias": "_mc"},
    "_tf": {"desc": "Gets item prices from backpack.tf (not perfect for items with unusual effects/shines)", "use": "[command] [item name]", "alias": None},
    "_quote": {"desc": "Brightens your day with a random quote.", "use": None, "alias": None},
    "_notifydev": {"desc": "Sends a message to the developer", "use": "[command] [message]", "alias": "_suggest"},
    "_suggest": {"desc": "Sends a message to the developer", "use": "[command] [message]", "alias": "_notifydev"},
    "_remind": {"desc": "General module for timers\nSubcommands: remind me in, remind here in, remind list, remind remove", "use": None, "alias": None},
    "_remind me": {"desc": "Subcommands: remind me in, remind here in", "use": None, "alias": None},
    "_remind me in": {"desc": "Adds a reminder (reminds you in dm)", "use": "[command] [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind here in": {"desc": "Adds a reminder (reminds everybody in current channel)", "use": "[command] [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind list": {"desc": "Displays all ongoing timers.", "use": None, "alias": None},
    "_remind remove": {"desc": "Removes a timer with supplied description or time (or all timers with 'all')", "use": "[command] [timer description or time in sec]", "alias": None},
    "_cmds": {"desc": "Displays a link to the wiki page where all commands are listed.", "use": None, "alias": "_commands"},
    "_commands": {"desc": "Displays a link to the wiki page where all commands are listed.", "use": None, "alias": "_cmds"},
    "_say": {"desc": "Says something (#channel is optional)", "use": "[command] (#channel) [message]", "alias": None}
}

cmd_help_admin = {
    "_ban": {"desc": "Bans a member.", "use": "[command] [mention]", "alias": "nano.ban"},
    "nano.ban": {"desc": "Bans a member.", "use": "User: [command] [mention]", "alias": "_ban"},
    "_kick": {"desc": "Kicks a member.", "use": "[command] [mention]", "alias": "nano.kick"},
    "nano.kick": {"desc": "Kicks a member", "use": "[command] [mention]", "alias": "_kick"},
    # "_unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "nano.unban"},
    # "nano.unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "_unban"},
    "_softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "[command] [time] @mention", "alias": "nano.softban"},
    "nano.softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "[command] [time] @mention", "alias": "_softban"},
    "_role add": {"desc": "Adds a role to the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role remove": {"desc": "Removes a role from the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role replacewith": {"desc": "Replace all roles with the specified one for a user.", "use": "[command] [role name] [mention]", "alias": None},
    "_cmd add": {"desc": "Adds a command to the server.", "use": "[command] command|response", "alias": None},
    "_cmd remove": {"desc": "Removes a command from the server.", "use": "[command] command", "alias": None},
    "_invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "use": None, "alias": "nano.invite"},
    "_vote start": {"desc": "Starts a vote on the server.", "use": "[command] \"question\" choice1|choice2|...", "alias": None},
    "_vote end": {"desc": "Simply ends the current vote on the server.", "use": None, "alias": None},
    "_setup": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "use": None, "alias": "nano.getstarted"},
    "_user": {"desc": "Gives info about the user", "use": "[command] [mention or name]", "alias": None},
    "nano.setup": {"desc": "(Re)sets all server related bot settings to default.", "use": None, "alias": "_setup"},
    "nano.admins add": {"desc": "Adds a user to admins on the server.", "use": "[command] [mention]", "alias": None},
    "nano.admins remove": {"desc": "Removes a user from admins on the server.", "use": "[command] [mention]", "alias": None},
    "nano.admins list": {"desc": "Lists all admins on the server.", "use": None, "alias": None},
    "nano.sleep": {"desc": "Puts Nano to sleep. (per-server basis)", "use": None, "alias": None},
    "nano.wake": {"desc": "Wakes Nano up. (per-server basis)", "use": None, "alias": None},
    "nano.invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "use": None, "alias": "_invite"},
    "nano.settings": {"desc": "Sets server settings like word, spam and invite filtering and changes log channel.", "use": "[command] [setting] True/False", "alias": None},
    "nano.displaysettings": {"desc": "Displays all server settings.", "use": None, "alias": None},
    "nano.blacklist add": {"desc": "Adds a channel to command blacklist.", "use": "[command] [channel name]", "alias": None},
    "nano.blacklist remove": {"desc": "Removes a channel from command blacklist", "use": "[command] [channel name]", "alias": None},
    "nano.changeprefix": {"desc": "Changes the prefix on the server.", "use": "[command] prefix", "alias": None},
    "_mute": {"desc": "Mutes the user - deletes all future messages from the user until he/she is un-muted.", "use": "[command] [mention or name]", "alias": None},
    "_unmute": {"desc": "Un-mutes the user (see mute help for more info).", "use": "[command] [mention or name]", "alias": None},
    "_muted": {"desc": "Displays a list of all members currently muted.", "use": None, "alias": None},
    "_purge": {"desc": "Deletes the messages from the specified user in the last x messages", "use": "[command] [amount] [user name]", "alias": None},
    "_welcomemsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @userthatjoined, ':server' = server name", "use": "[command] [content]", "alias": None},
    "_banmsg": {"desc": "Sets the message sent when a member is banned.\nFormatting: ':user' = user name", "use": "[command] [content]", "alias": None},
    "_kickmsg": {"desc": "Sets the message sent when a member is kicked.\nFormatting: ':user' = user name", "use": "[command] [content]", "alias": None},
    "_nuke": {"desc": "Nukes (deletes) last x messages.", "use": None, "alias": None},
}

cmd_help_owner = {
    "_playing": {"desc": "Restricted to owner(!), changes 'playing' status.", "use": "[command] [status]", "alias": None},
    "nano.kill": {"desc": "Restricted to owner, shuts down the bot.", "use": "[command]", "alias": None},
    "nano.restart": {"desc": "Restricted to owner, restarts down the bot.", "use": "[command]", "alias": None},
    "nano.reload": {"desc": "Restricted to owner, reloads all settings from config file.", "use": None, "alias": "_reload"},
    "_reload": {"desc": "Restricted to owner, reloads all settings from config file.", "use": None, "alias": "nano.reload"},
}

valid_commands = [
    "_cmds", "_commands", "_help", "_notifydev", "_suggest", "_bug"
]


@threaded
def save_submission(sub):
    with open("data/submissions.txt", "a") as file:
        file.write(str(sub) + "\n" + ("-" * 20))


class Help:
    def __init__(self, **kwargs):
        self.loop = kwargs.get("loop")
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

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

        # !help and @Nano
        if message.content.strip(" ") == (prefix + "help"):
            await client.send_message(message.channel, help_nano)

            self.stats.add(HELP)

        # @Nano help
        elif self.client.user in message.mentions:
            un_mentioned = str(message.content[21:])
            if un_mentioned == "" or un_mentioned == " ":
                await client.send_message(message.channel, help_nano)

            self.stats.add(HELP)

        # !cmds or !commands
        elif startswith(prefix + "cmds", prefix + "commands"):
            await client.send_message(message.channel, "A 'complete' list of commands is available here: "
                                                       "https://github.com/DefaltSimon/Nano/wiki/Commands")

            self.stats.add(HELP)

        # !help simple
        elif startswith(prefix + "help simple"):
            await client.send_message(message.channel, help_simple)

            self.stats.add(HELP)

        # !help [command]
        elif startswith(prefix + "help"):
            search = str(message.content)[len(prefix + "help "):]

            self.stats.add(HELP)

            def get_command_info(cmd):

                # Normal commands
                cmd1 = cmd_help_normal.get(str(cmd.replace(prefix, "_").strip(" ")))
                if cmd1 is not None:
                    cmd_name = cmd.replace(prefix, "")

                    description = cmd1.get("desc")
                    use = cmd1.get("use").replace("[command]",
                                                  prefix + cmd_name if not cmd_name.startswith("nano.") else cmd_name)
                    alias = cmd1.get("alias")

                    emb = Embed(colour=Colour.blue())

                    emb.add_field(name="Description", value=description)

                    if use:
                        emb.add_field(name="Use", value=use, inline=False)
                    if alias:
                        emb.add_field(name="Aliases", value=alias, inline=False)

                    self.stats.add(HELP)
                    return "**{}**".format(cmd_name), emb

                # Admin commands
                cmd2 = cmd_help_admin.get(str(cmd.replace(prefix, "_").strip(" ")))
                if cmd2 is not None:
                    cmd_name = cmd.replace(prefix, "")

                    description = cmd2.get("desc")
                    use = cmd2.get("use").replace("[command]",
                                                  prefix + cmd_name if not cmd_name.startswith("nano.") else cmd_name)
                    alias = cmd2.get("alias")

                    emb = Embed(colour=Colour.green())

                    emb.add_field(name="Description", value=description)

                    if use:
                        emb.add_field(name="Use", value=use, inline=False)
                    if alias:
                        emb.add_field(name="Aliases", value=alias, inline=False)

                    self.stats.add(HELP)
                    return "**{}** (admin only)".format(cmd_name), emb

                # Owner commands
                cmd3 = cmd_help_owner.get(str(cmd.replace(prefix, "_").strip(" ")))
                if cmd3 is not None:
                    cmd_name = cmd.replace(prefix, "")

                    description = cmd3.get("desc")
                    use = cmd3.get("use").replace("[command]",
                                                  prefix + cmd_name if not cmd_name.startswith("nano.") else cmd_name)
                    alias = cmd3.get("alias")

                    emb = Embed(colour=Colour.magenta())

                    emb.add_field(name="Description", value=description)

                    if use:
                        emb.add_field(name="Use", value=use, inline=False)
                    if alias:
                        emb.add_field(name="Aliases", value=alias, inline=False)

                    self.stats.add(HELP)
                    return "**{}** (owner only)".format(cmd_name), emb

                if not cmd1 or not cmd2 or not cmd3:
                    self.stats.add(WRONG_ARG)
                    return None, None

            # Allows for !help ping AND !help !ping
            if search.startswith(prefix) or search.startswith("nano."):
                name, embed = get_command_info(search)

                if name:
                    await client.send_message(message.channel, name, embed=embed)

                else:
                    await client.send_message(message.channel, "Command could not be found.\n"
                                                               "**(Use: `>help command`)**".replace(">", prefix))

            else:
                name, embed = get_command_info(prefix + search)

                if name:
                    await client.send_message(message.channel, name, embed=embed)

                else:
                    await client.send_message(message.channel, "Command could not be found.\n"
                                                               "**(Use: `>help command`)**".replace(">", prefix))

        # !notifydev
        elif startswith(prefix + "notifydev", prefix + "suggest"):
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

            # Saves the submission to disk
            save_submission(comp.replace(message.author.mention, "{} ({})\n".format(message.author.name, message.author.id)))

            await client.send_message(dev_server.owner, comp)
            await client.send_message(message.channel, "**Thank you** for your *{}*.".format(
                "submission" if typ == "Report" else "suggestion"))

        # !bug
        elif startswith(prefix + "bug"):
            await client.send_message(message.channel, nano_bug.replace("_", prefix))


class NanoPlugin:
    _name = "Help Commands"
    _version = "0.2"

    handler = Help
    events = {
        "on_message": 10
        # type : importance
    }
