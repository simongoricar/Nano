# coding=utf-8
import asyncio
import datetime
import logging
import time
import traceback

from typing import Union
from discord import utils, Client, Embed, TextChannel, Colour, DiscordException, Object, HTTPException

from data.serverhandler import INVITEFILTER_SETTING, SPAMFILTER_SETTING, WORDFILTER_SETTING
from data.utils import convert_to_seconds, matches_iterable, is_valid_command, StandardEmoji, \
                       resolve_time, log_to_file, is_disabled, IgnoredException, parse_special_chars, \
                       apply_string_padding

from data.stats import MESSAGE


#####
# Administration plugin
# Mostly Nano settings
#####

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS
CMD_LIMIT = 40
CMD_LIMIT_T = 40
CMD_LIMIT_A = 1000
SELFROLE_MAX = 35
PREFIX_MAX = 50
BLACKLIST_MAX = 35
TICK_DURATION = 15

# Threshold for when to make a new command page
NEW_PAGE_BEFORE = 2000 - (CMD_LIMIT_T + CMD_LIMIT_A + 150)

# 15 seconds
REMINDER_MIN = 15
# 5 Days
REMINDER_MAX = 5 * 24 * 60 * 60

# Maximum age (in seconds) of a message that should be kept in cache
MAX_MSG_AGE = 60 * 3

# Maximum join/leave/kick/ban message length
MAX_NOTIF_LENGTH = 800

commands = {
    "_ban": {"desc": "Bans a member.", "use": "[command] [mention/user id]", "alias": "nano.ban"},
    "nano.ban": {"desc": "Bans a member.", "use": "User: [command] [mention]", "alias": "_ban"},
    "_kick": {"desc": "Kicks a member.", "use": "[command] [mention/user id]", "alias": "nano.kick"},
    "nano.kick": {"desc": "Kicks a member", "use": "[command] [mention]", "alias": "_kick"},
    "_unban": {"desc": "Unbans a member.", "use": "[command] [mention/user id]", "alias": "nano.unban"},
    "nano.unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "_unban"},
    "_softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "[command] @mention/username | [time] or [command] @mention [time]"},

    "_cmd": {"desc": "Subcommands:\n`add` `remove` `status` `list`", "use": "[command]"},
    "_cmd add": {"desc": "Adds a command to the server.", "use": "[command] command|response"},
    "_cmd remove": {"desc": "Removes a command from the server.", "use": "[command] command"},
    "_cmd status": {"desc": "Displays how many commands you have and how many more you can add.", "use": "[command] command"},
    "_cmd list": {"desc": "Returns a server-specific command list.", "use": "[command] (page number)"},

    "_mute": {"desc": "Mutes the user - deletes all future messages from the user until he/she is un-muted.", "use": "[command] [mention or name]"},
    "_unmute": {"desc": "Un-mutes the user (see mute help for more info).", "use": "[command] [mention or name]"},
    "_muted": {"desc": "Displays a list of all members currently muted."},
    # "_purge": {"desc": "Deletes the messages from the specified user in the last x messages", "use": "[command] [amount] [user name]"},

    "_setup": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "alias": "nano.setup"},
    "nano.setup": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "alias": "_setup"},
    "_user": {"desc": "Displays info about the user", "use": "[command] [@mention or name]"},
    "_welcomemsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @user, ':server' = server name", "use": "[command] [content]", "alias": "_joinmsg"},
    "_joinmsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @user, ':server' = server name", "use": "[command] [content]", "alias": "_welcomemsg"},
    "_banmsg": {"desc": "Sets the message sent when a member is banned.\nFormatting: ':user' = user name", "use": "[command] [content]"},
    "_kickmsg": {"desc": "Sets the message sent when a member is kicked.\nFormatting: ':user' = user name", "use": "[command] [content]"},
    "_leavemsg": {"desc": "Sets the message sent when a member leaves the server.\nFormatting: ':user' = user name", "use": "[command] [content]"},
    "_nuke": {"desc": "Nukes (deletes) last x messages. (keep in mind that you can only nuke messages up to 2 weeks old)"},

    "nano.blacklist add": {"desc": "Adds a channel to command blacklist.", "use": "[command] [channel name]"},
    "nano.blacklist remove": {"desc": "Removes a channel from command blacklist", "use": "[command] [channel name]"},
    "nano.blacklist list": {"desc": "Shows all blacklisted channels on this server", "use": "[command]"},

    "nano.settings": {"desc": "Sets server settings like word, spam, invite filtering, log channel and selfrole.\nPossible setting keyords: `wordfilter`, `spamfilter`, `invitefilter`, `logchannel`, `selfrole`, `defaultchannel`", "use": "[command] [setting] True/False/Something else"},
    "nano.settings wordfilter": {"desc": "Turns the swearing filter on or off.", "use": "[command] True/False"},
    "nano.settings spamfilter": {"desc": "Turns the spam filter on or off. (please note, this is only a gibberish filter)", "use": "[command] True/False"},
    "nano.settings invitefilter": {"desc": "Turns the invite filter on or off. All links except those sent by Nano Mods or higher will be deleted.", "use": "[command] True/False"},
    "nano.settings logchannel": {"desc": "Sets the channel you want Nano to log events into (this includes join/leave/... events and also some command executions)", "use": "[command] True/False"},
    "nano.settings defaultchannel": {"desc": "Sets the channel you want Nano to post join/leave/kick/ban messages in.", "use": "[command] True/False"},
    "nano.settings selfrole": {"desc": "The selfrole system allows normal members to give themselves a role without an admin's supervision.\nSubcommands: `add` `remove` (For a list current selfroles see `{p}selfrole list`)"},
    "nano.settings selfrole add": {"desc": "Adds a role to server's selfroles.", "use": "[command] [role name]"},
    "nano.settings selfrole remove": {"desc": "Removes a role from server's selfrole list.", "use": "[command] [role name]"},


    "nano.displaysettings": {"desc": "Displays all server settings."},
    "nano.changeprefix": {"desc": "Changes the prefix on the server.", "use": "[command] prefix"},
    "nano.serverreset": {"desc": "Resets all server settings to the default."},

    "_role": {"desc": "General role stuff. Subcommands:\n`add` `remove`"},
    "_role add": {"desc": "Adds a role to the user.", "use": "[command] [role name] | [@mention @mention ...] OR [role name] @mention"},
    "_role remove": {"desc": "Removes a role from the user.", "use": "[command] [role name] | [@mention @mention ...] OR [role name] @mention"},

    "_language": {"desc": "Displays the current language you're using. \nSee `_language list` for available languages or use `_language set [language_code] to set your language.", "use": "[command] [argument]"},
    "_language list": {"desc": "Lists all available languages", "use": "[command]"},
    "_language set": {"desc": "Sets the language for the current server.", "use": "[command] [language_code]"},

    "_selfrole": {"desc": "Selfroles allow normal members to give themselves role(s) without an admin's supervision (see `_selfrole list` for a list of available selfoles)\nIf you already have the role, this command removes it.", "use": "[command] [role name]"},
    "_selfrole list": {"desc": "Lists the current selfroles on this server,", "use": "[command]"},

}

# !cmds conflicts with !cmd add/etc...
ignore_commands = [
    "_cmds"
]


class RedisSoftBanScheduler:
    def __init__(self, client, handler, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop
        self.redis = handler.get_plugin_data_manager(namespace="softban")

    def get_guild_bans(self, guild_id) -> dict:
        return self.redis.hgetall(guild_id)

    def is_guild_ban(self, guild_id, user_id):
        return self.redis.hexists(guild_id, user_id)

    def get_all_bans(self) -> dict:
        return {b: self.get_guild_bans(b) for b in [a.strip("softban:") for a in self.redis.scan_iter("*")]}

    def set_softban(self, guild, user, tim):
        t = time.time()

        if not str(tim).isdigit():
            tim = convert_to_seconds(tim)
        else:
            tim = int(tim)

        if not (REMINDER_MIN <= tim <= REMINDER_MAX):
            return False

        return self.redis.hset(guild.id, user.id, int(t + tim))

    @staticmethod
    async def tick(last_time):
        """
        Very simple implementation of a self-correcting tick system
        :return: epoch time
        """
        delta = TICK_DURATION - (time.time() - last_time)

        # If previous loop took more than TICK_DURATION, do one right away
        if delta <= 0:
            return time.time()

        await asyncio.sleep(delta)
        return time.time()

    async def dispatch(self, guild_id: int, user_id: int):
        try:
            logger.debug("Dispatching")

            guild = self.client.get_guild(guild_id)
            await guild.unban(Object(id=user_id))
        except DiscordException as e:
            logger.warning(e)

    async def start_monitoring(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(1)

        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for guild_id, ban in self.get_all_bans().items():
                # If time is up, unban the user
                for user, tm in ban.items():
                    if int(tm) <= last_time:
                        guild_id = int(guild_id)
                        user_id = int(user)

                        await self.dispatch(guild_id, user_id)
                        self.redis.hdel(guild_id, user_id)

            # And tick.
            last_time = await self.tick(last_time)


class MessageTracker:
    __slots__ = (
        "msgs", "timestamps", "max_age"
    )

    def __init__(self, max_active_age=MAX_MSG_AGE):
        self.msgs = {}
        self.timestamps = {}

        self.max_age = max_active_age

    def is_active(self, message_id):
        return self.timestamps.get(message_id, False)

    def set_message_data(self, msg_id, data, renew_timestamp=False):
        # Update timestamp
        if (msg_id not in self.msgs.keys()) or renew_timestamp:
            self.timestamps[msg_id] = time.time()

        # Set data
        self.msgs[msg_id] = data

    def get_message_data(self, msg_id) -> Union[None, dict]:
        if not self.is_active(msg_id):
            return None

        return self.msgs.get(msg_id)

    @staticmethod
    async def tick(last_time):
        """
        Very simple implementation of a self-correcting tick system
        :return: None
        """
        current_time = time.time()
        delta = TICK_DURATION - (current_time - last_time)

        # If previous loop took more than TICK_DURATION, do one right away
        if delta <= 0:
            return time.time()

        await asyncio.sleep(delta)

        return time.time()

    async def start_monitoring(self):
        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for msg_id, ts in self.timestamps.copy().items():
                # If message is too old, remove it
                if (last_time - ts) > self.max_age:
                    del self.msgs[msg_id]
                    del self.timestamps[msg_id]

            # And tick.
            last_time = await self.tick(last_time)


def make_pages_from_dict(item_dict: dict):
    """
    Makes pages out of a custom command list
    :param item_dict: dictionary containing custom commands
    :return: tuple -> dict(page_index:[lines], etc...), total_pages
    """
    cmd_list = {0: []}
    c_page = 0

    for trigger, value in item_dict.items():
        fm = "{} : {}".format(trigger, value)

        # Creates a new page index if this command is the first one in the new page
        if not cmd_list.get(c_page):
            cmd_list[c_page] = []

        # Shifts the page counter if page is too long
        if (sum([len(a) for a in cmd_list[c_page]]) + len(fm)) > NEW_PAGE_BEFORE:
            c_page += 1
            cmd_list[c_page] = []

        cmd_list[c_page].append(fm)

    # dict(page_index:[lines], etc...), total_pages
    return cmd_list, c_page


def make_pages_from_list(item_list: list):
    """
    Makes pages out of a mute list
    :param item_list: list containing mutes
    :return: tuple -> dict(page_index:[lines], etc...), total_pages
    """
    cmd_list = {0: []}
    c_page = 0

    for item in item_list:
        # Creates a new page index if this command is the first one in the new page
        if not cmd_list.get(c_page):
            cmd_list[c_page] = []

        # Shifts the page counter if page is too long
        if sum([len(a) for a in cmd_list[c_page]]) > NEW_PAGE_BEFORE:
            c_page += 1
            cmd_list[c_page] = []

        cmd_list[c_page].append("➤ " + str(item))

    # dict(page_index:[lines], etc...), total_pages
    return cmd_list, c_page


class ObjectListReactions:
    __slots__ = (
        "client", "handler", "trans", "track"
    )

    # Emojis to react with
    UP = "\U00002B06"
    DOWN = "\U00002B07"

    def __init__(self, client, handler, trans):
        self.client = client
        self.handler = handler
        self.trans = trans

        self.track = MessageTracker()

    async def new_message(self, message, page, object_map, trans_string):
        # Ignore if there is only one page
        if len(object_map.keys()) == 1:
            return

        # Adds reactions for navigation
        await message.add_reaction(ObjectListReactions.UP)
        await message.add_reaction(ObjectListReactions.DOWN)

        # Caches data into MessageTracker
        data = {
            "page": int(page),
            "serv_id": message.guild.id,
            "objs": object_map,
            "trans_string": trans_string
        }

        self.track.set_message_data(message.id, data)

    async def handle_reaction(self, reaction, user, **_):
        # Ignore reactions from self
        if user.id == self.client.user.id:
            return

        msg = reaction.message

        # Get and verify data existence
        data = self.track.get_message_data(msg.id)
        if not data:
            return

        c_page = data.get("page")
        page_amount = len(data.get("objs").keys())

        # Default to down, even though it should always change
        # True - up
        # False - down
        up_down = None
        for react in msg.reactions:

            if react.count > 1:
                if react.emoji == ObjectListReactions.UP:
                    up_down = True
                    break
                elif react.emoji == ObjectListReactions.DOWN:
                    up_down = False
                    break

        # This will not get set if a custom/some other emoji was added
        if up_down is None:
            return

        # True - goes up one page
        if up_down:
            # Can't go higher
            if c_page <= 0:
                return

            page = data.get("objs").get(c_page - 1)
            c_page -= 1

        # False - goes down one page
        else:
            # Can't go lower
            if c_page + 1 >= page_amount:
                return

            page = data.get("objs").get(c_page + 1)
            c_page += 1

        # Reset reactions and edit message
        await msg.clear_reactions()

        new_msg = data.get("trans_string").format(c_page + 1, page_amount, "\n".join(page))
        await msg.edit(content=new_msg)

        await msg.add_reaction(ObjectListReactions.UP)
        await msg.add_reaction(ObjectListReactions.DOWN)

        # Updates the page counter
        data["page"] = c_page
        self.track.set_message_data(msg.id, data)


class Admin:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")
        self.nano = kwargs.get("nano")

        self.timer = RedisSoftBanScheduler(self.client, self.handler, self.loop)
        self.loop.create_task(self.timer.start_monitoring())

        self.list = ObjectListReactions(self.client, self.handler, self.trans)
        self.loop.create_task(self.list.track.start_monitoring())

        self.bans = []
        self.kick_list = []

        self.default_channel = None
        self.handle_log_channel = None

    async def on_plugins_loaded(self):
        self.default_channel = self.nano.get_plugin("server").get("instance").default_channel
        self.handle_log_channel = self.nano.get_plugin("server").get("instance").handle_log_channel
        self.kick_list = self.nano.get_plugin("server").get("instance").kicks

    async def resolve_role(self, name, message, lang, no_error=False):
        if len(message.role_mentions) > 0:
            return message.role_mentions[0]

        if name is None:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_SUCH_ROLE", lang))
                raise IgnoredException

        role = utils.find(lambda r: r.name == name, message.guild.roles)

        if not role:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_SUCH_ROLE", lang))
                raise IgnoredException

        return role

    async def resolve_user(self, name: str, message, lang: str, no_error=False):
        """
        Searches for an user from the provided name and mentions
        Mentions take precedence, after that the name. If no user is found and no_error is False, ERROR_NO_MENTION/NO_USER will be sent.
        If no_error is True, it will return None
        """
        # Tries @mentions
        if len(message.mentions) > 0:
            return message.mentions[0]

        # If there's no mentions and no name provided
        if name is None:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_MENTION", lang))
                raise IgnoredException

        # If ID is passed, check its existence
        if name.isnumeric():
            user = message.guild.get_member(int(name))
            if user:
                return user

        # No mentions, username is provided
        user = utils.find(lambda u: u.name == name, message.guild.members)
        if not user:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_USER", lang))
                raise IgnoredException

        return user

    async def resolve_channel(self, name, message, lang, no_error=False):
        # Tries #mentions
        if len(message.channel_mentions) > 0:
            return message.channel_mentions[0]

        # When no channel name is provided
        if name is None:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_CHMENTION", lang))
                raise IgnoredException

        # Tries to find by name
        chan = utils.find(lambda c: c.name == name, message.guild.channels)
        if not chan:
            if no_error:
                return None
            else:
                await message.channel.send(self.trans.get("ERROR_NO_CHMENTION", lang))
                raise IgnoredException

        return chan

    @staticmethod
    def can_access_role(member_a, s_role):
        """
        Checks if the user is permitted to change this role (can only change roles lower in the hierarchy)
        """
        return bool((member_a.top_role.position >= s_role.position) or member_a == member_a.guild.owner)

    @staticmethod
    async def try_accessing_role(nano_user, role):
        try:
            await nano_user.add_roles(role, atomic=True)
            await nano_user.remove_roles(role, reason="Checking permissions for selfrole.", atomic=True)
            return True
        except:
            log_to_file("ERROR in try_accessing_role: (role: {})".format(role.name) + traceback.format_exc())
            return False

    async def _role_command_parameters(self, message, lang, cut_length) -> tuple:
        """
        Used by !role add and !role remove to parse parameters
        Returns tuple: role, user_list
        """
        users = message.mentions or []

        # Notation without |
        if "|" not in message.content[cut_length:]:
            if len(message.mentions) == 0:
                await message.channel.send(self.trans.get("MSG_ROLE_NEED_MENTION", lang))
                raise IgnoredException

            # Notation without | does not support multiple mentions
            if len(message.mentions) > 1:
                await message.channel.send(self.trans.get("MSG_ROLE_TOO_MANY_MENTIONS", lang))
                raise IgnoredException

            a_role, usr = message.content[cut_length:].rsplit("<", maxsplit=1)

            role = await self.resolve_role(a_role.strip(" "), message, lang)

        # Notation with | as separator
        else:
            if len(message.role_mentions) != 0:
                role = message.role_mentions[0]

                # Search by name if no mention
                if len(message.mentions) == 0:
                    usr = message.content[cut_length:].split("|")[1].strip(" ")
                    usr = await self.resolve_user(usr.strip(" "), message, lang)
                    users.append(usr)

            else:
                role_raw, user_raw = message.content[cut_length:].split("|")

                # Search by name if no mention
                if len(message.mentions) == 0:
                    usr = await self.resolve_user(user_raw.strip(" "), message, lang)
                    users.append(usr)

                role = await self.resolve_role(role_raw.strip(" "), message, lang)

        return role, users

    async def log_nuke_command(self, message, amount, prefix, lang):
        log_channel = await self.handle_log_channel(message.guild)

        if not log_channel:
            return

        embed = Embed(title=self.trans.get("MSG_LOGPOST_NUKE", lang).format(prefix),
                      description=self.trans.get("MSG_NUKE_AMOUNT", lang).format(amount))

        embed.set_author(name="{} ({})".format(message.author.name, message.author.id), icon_url=message.author.avatar_url)
        embed.add_field(name=self.trans.get("INFO_CHANNEL", lang), value=message.channel.mention)

        await log_channel.send(embed=embed)

    async def on_message(self, message, **kwargs):
        client = self.client
        handler = self.handler
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(client, Client)

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix):
            return
        else:
            # Check for conflicts
            for ignore in ignore_commands:
                if message.content.startswith(ignore.replace("_", prefix)):
                    return

            self.stats.add(MESSAGE)

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False


        # Moved from commons.py
        # !selfrole [role name]/list
        if startswith(prefix + "selfrole"):
            if len(message.role_mentions) > 0:
                role_n = message.role_mentions[0].name
            else:
                role_n = message.content[len(prefix + "selfrole "):].strip(" ")

            # If argument is list
            # !selfrole list
            if role_n.startswith("list"):
                arg = role_n[5:].strip(" ")
                try:
                    page = int(arg)

                    if page != 0:
                        page -= 1
                # If no page is specified
                except ValueError:
                    page = 0

                roles = self.handler.get_selfroles(message.guild.id)

                if not roles:
                    await message.channel.send(trans.get("MSG_SELFROLE_NONE", lang))
                    return

                r_list, r_page = make_pages_from_list(roles)

                # If user wants a page that doesn't exist
                if page > r_page:
                    await message.channel.send(trans.get("MSG_SELFROLE_NO_PAGE", lang).format(r_page + 1))
                    return

                msg = trans.get("MSG_SELFROLE_LIST", lang).format(page + 1, r_page + 1, "\n".join(r_list[page]))
                msg_list = await message.channel.send(msg)

                await self.list.new_message(msg_list, page, r_list, trans.get("MSG_SELFROLE_LIST", lang))

            else:
                # If a list is not requested, proceed like normal selfrole

                if not role_n:
                    await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                    return

                valid_role = self.handler.is_selfrole(message.guild.id, role_n)

                if not valid_role:
                    await message.channel.send(trans.get("MSG_SELFROLE_REMOVE_NOT_PRESENT", lang))
                    return

                # Find by name
                role = utils.find(lambda r: r.name == role_n, message.guild.roles)
                # If role is not in server
                if not role:
                    self.handler.remove_selfrole(message.guild.id, role_n)
                    await message.channel.send(trans.get("MSG_SELFROLE_NOT_ANYMORE", lang))
                    return

                # If user already has the role, remove it
                if role in message.author.roles:
                    await message.author.remove_roles(role)
                    await message.channel.send(trans.get("MSG_SELFROLE_REMOVED", lang).format(role_n))
                # Otherwise, add it
                else:
                    await message.author.add_roles(role)
                    await message.channel.send(trans.get("MSG_SELFROLE_ADDED", lang))

            return

        # !nuke
        elif startswith(prefix + "nuke"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            amount = message.content[len(prefix + "nuke "):]

            try:
                amount = int(amount) + 1  # Includes the sender's message
            except ValueError:
                await message.channel.send(trans.get("ERROR_NOT_NUMBER", lang))
                return

            await message.delete()
            await message.channel.send(trans.get("MSG_NUKE_PURGING", lang).format(amount))

            additional = ""

            try:
                await message.channel.purge(limit=amount)
            except HTTPException:
                additional = trans.get("MSG_NUKE_OLD", lang)

            # Show success
            # Message is automatically deleted after 1.5s
            await message.channel.send(trans.get("MSG_NUKE_PURGED", lang).format(amount - 1) + additional, delete_after=1.5)

            await self.log_nuke_command(message, amount, prefix, lang)

            return

        # !kick
        elif startswith(prefix + "kick") and not startswith(prefix + "kickmsg"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return

            name = message.content[len(prefix + "kick "):].strip(" ")
            user = await self.resolve_user(name, message, lang)

            if user.id == client.user.id:
                await message.channel.send(trans.get("MSG_KICK_NANO", lang))
                return

            self.kick_list.append(user.id)
            try:
                await user.kick()
            except DiscordException:
                self.kick_list.remove(user.id)

            await message.channel.send(trans.get("MSG_KICK", lang).format(user.name))

            return

        # !ban
        elif startswith(prefix + "ban") and not startswith(prefix + "banmsg"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "ban "):].strip(" ")
            user = await self.resolve_user(name, message, lang)

            if user.id == client.user.id:
                await message.channel.send(trans.get("MSG_BAN_NANO", lang))
                return

            confirm = trans.get("INFO_CONFIRM", lang)
            await message.channel.send(trans.get("MSG_BAN_USER", lang).format(user.name, confirm))

            def is_author(c):
                return c.author == message.author and c.channel == message.channel and c.content == confirm

            try:
                await client.wait_for("message", check=is_author, timeout=15)
            except asyncio.TimeoutError:
                await message.channel.send(trans.get("MSG_BAN_TIMEOUT", lang))
            else:
                self.bans.append(user.id)
                try:
                    await user.ban(delete_message_days=0)
                except DiscordException:
                    self.bans.remove(user.id)

                await message.channel.send(trans.get("MSG_BAN", lang).format(user.name))

            return

        # !unban
        elif startswith(prefix + "unban"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "unban "):].strip(" ")

            if not name:
                await message.channel.send(trans.get("MSG_UNBAN_WRONG_USAGE", lang).format(prefix))
                return

            user = None
            if name.isnumeric():
                name = int(name)
                # Search by id
                for ban in await message.guild.bans():
                    if ban.user.id == name:
                        user = ban.user

            else:
                for ban in await message.guild.bans():
                    if ban.user.name == name:
                        user = ban.user

            if not user:
                await message.channel.send(trans.get("MSG_UNBAN_NO_BAN", lang))
                return

            await message.guild.unban(user)
            await message.channel.send(trans.get("MSG_UNBAN_SUCCESS", lang).format(user.name))

            return

        # !softban @mention/username | [time]
        elif startswith(prefix + "softban"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            cut = message.content[len(prefix + "softban "):].strip(" ")

            try:
                name, tim = cut.rsplit("|", maxsplit=1)
                name, tim = name.strip(" "), tim.strip(" ")
            # In case the value can't be unpacked: no |
            except ValueError:
                if len(message.mentions) == 0:
                    # Try notation with for
                    try:
                        name, tim = cut.rsplit("for", maxsplit=1)
                        name, tim = name.strip(" "), tim.strip(" ")
                    except ValueError:
                        if cut == "":
                            await message.channel.send(trans.get("MSG_SOFTBAN_PLSMENTION", lang))
                        else:
                            await message.channel.send(trans.get("MSG_SOFTBAN_NO_TIME", lang))

                        return

                else:
                    # Alternate method: @mention [time] (without |)
                    name = message.mentions[0].name
                    tim = cut.replace("<@{}>".format(message.mentions[0].id), "").strip(" ")

                    if tim == "":
                        await message.channel.send(trans.get("MSG_SOFTBAN_NO_TIME", lang))
                        return

            user = await self.resolve_user(name, message, lang)

            total_seconds = convert_to_seconds(tim)

            self.timer.set_softban(message.guild, user, total_seconds)
            await user.ban(delete_message_days=0)

            await message.channel.send(trans.get("MSG_SOFTBAN_SUCCESS", lang).format(user.name, resolve_time(total_seconds, lang)))

            return

        # !mute list
        elif startswith(prefix + "mute list"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            mutes = handler.get_mute_list(message.guild)
            page = message.content[len(prefix + "mute list "):].strip(" ")
            if page:
                try:
                    page -= 1
                except ValueError:
                    await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                    return
            else:
                page = 0

            if mutes:
                # Verifies the presence of users
                muted_ppl = []
                for u_id in mutes:
                    usr = utils.find(lambda b: b.id == u_id, message.guild.members)
                    if usr:
                        muted_ppl.append(usr.name)

                mute_list, m_page = make_pages_from_list(muted_ppl)

                final = trans.get("MSG_MUTE_LIST", lang).format(page + 1, m_page + 1, "\n".join(mute_list[page]))

                msg = await message.channel.send(final)
                await self.list.new_message(msg, page, mute_list, trans.get("MSG_MUTE_LIST", lang))

            else:
                await message.channel.send(trans.get("MSG_MUTE_NONE", lang))

            return

        # !mute
        elif startswith(prefix + "mute"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "mute "):]
            user = await self.resolve_user(name, message, lang)

            if message.guild.owner.id == user.id:
                await message.channel.send(trans.get("MSG_MUTE_OWNER", lang))
                return

            if message.author.id == user.id:
                await message.channel.send(trans.get("MSG_MUTE_SELF", lang))
                return

            handler.mute(message.guild, user.id)
            await message.channel.send(trans.get("MSG_MUTE_SUCCESS", lang).format(user.name))

            return

        # !unmute
        elif startswith(prefix + "unmute"):
            if not handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "unmute "):]

            # In case an admin wishes to unmute everyone
            if name == trans.get("INFO_ALL", lang):
                conf = trans.get("INFO_CONFIRM", lang)

                await message.channel.send(trans.get("MSG_UNMUTE_ALL_CONFIRM", lang).format(conf))

                def is_author(c):
                    return c.author == message.author and c.channel == message.channel and c.content == conf

                try:
                    await client.wait_for("message", check=is_author, timeout=15)
                except asyncio.TimeoutError:
                    await message.channel.send(trans.get("MSG_UNMUTE_TIMEOUT", lang))
                    return

                mutes = handler.get_mute_list(message.guild)
                for user_id in mutes:
                    handler.unmute(user_id, message.guild.id)

                await message.channel.send(trans.get("MSG_UNMUTE_MASS_DONE", lang))
                return

            # Normal unmuting
            user = await self.resolve_user(name, message, lang)
            handler.unmute(user.id, message.guild.id)

            await message.channel.send(trans.get("MSG_UNMUTE_SUCCESS", lang).format(user.name))

            return

        # END of mod commands

        ################################
        # PERMISSION CHECK (only admins)
        ################################
        if not handler.is_admin(message.author, message.guild):
            await message.channel.send(trans.get("PERM_ADMIN", lang))
            return

        # Users from here forth must be admins

        # !joinmsg
        if startswith(prefix + "joinmsg"):
            change = message.content[len(prefix + "joinmsg "):].strip(" ")

            if not change:
                joinmsg = handler.get_var(message.guild.id, "welcomemsg")

                if is_disabled(joinmsg):
                    await message.channel.send(trans.get("MSG_JOIN_IS_DISABLED", lang))
                else:
                    await message.channel.send(trans.get("MSG_JOIN_CURRENT", lang).format(joinmsg))

            elif is_disabled(change):
                handler.update_var(message.guild.id, "welcomemsg", None)
                await message.channel.send(trans.get("MSG_JOIN_DISABLED", lang))

            else:
                if len(change) > MAX_NOTIF_LENGTH:
                    await message.channel.send(trans.get("MSG_NOTIF_TOO_LONG", lang).format(MAX_NOTIF_LENGTH, len(change)))
                    return

                handler.update_var(message.guild.id, "welcomemsg", change)
                await message.channel.send(trans.get("MSG_JOIN", lang))

        # !welcomemsg
        elif startswith(prefix + "welcomemsg"):
            change = message.content[len(prefix + "welcomemsg "):].strip(" ")

            if not change:
                joinmsg = handler.get_var(message.guild.id, "welcomemsg")

                if is_disabled(joinmsg):
                    await message.channel.send(trans.get("MSG_JOIN_IS_DISABLED", lang))
                else:
                    await message.channel.send(trans.get("MSG_JOIN_CURRENT", lang).format(joinmsg))

            elif is_disabled(change):
                handler.update_var(message.guild.id, "welcomemsg", None)
                await message.channel.send(trans.get("MSG_JOIN_DISABLED", lang))

            else:
                if len(change) > MAX_NOTIF_LENGTH:
                    await message.channel.send(trans.get("MSG_NOTIF_TOO_LONG", lang).format(MAX_NOTIF_LENGTH, len(change)))
                    return

                handler.update_var(message.guild.id, "welcomemsg", change)
                await message.channel.send(trans.get("MSG_JOIN", lang))

        # !banmsg
        elif startswith(prefix + "banmsg"):
            change = message.content[len(prefix + "banmsg "):].strip(" ")

            if not change:
                banmsg = handler.get_var(message.guild.id, "banmsg")

                if is_disabled(banmsg):
                    await message.channel.send(trans.get("MSG_BANMSG_IS_DISABLED", lang))
                else:
                    await message.channel.send(trans.get("MSG_BANMSG_CURRENT", lang).format(banmsg))

            elif is_disabled(change):
                handler.update_var(message.guild.id, "banmsg", None)
                await message.channel.send(trans.get("MSG_BANMSG_DISABLED", lang))

            else:
                if len(change) > MAX_NOTIF_LENGTH:
                    await message.channel.send(trans.get("MSG_NOTIF_TOO_LONG", lang).format(MAX_NOTIF_LENGTH, len(change)))
                    return

                handler.update_var(message.guild.id, "banmsg", change)
                await message.channel.send(trans.get("MSG_BANMSG", lang))

        # !kickmsg
        elif startswith(prefix + "kickmsg"):
            change = message.content[len(prefix + "kickmsg "):].strip(" ")

            if not change:
                kickmsg = handler.get_var(message.guild.id, "kickmsg")

                if is_disabled(kickmsg):
                    await message.channel.send(trans.get("MSG_KICKMSG_IS_DISABLED", lang))
                else:
                    await message.channel.send(trans.get("MSG_KICKMSG_CURRENT", lang).format(kickmsg))

            elif is_disabled(change):
                handler.update_var(message.guild.id, "kickmsg", None)
                await message.channel.send(trans.get("MSG_KICKMSG_DISABLED", lang))

            else:
                if len(change) > MAX_NOTIF_LENGTH:
                    await message.channel.send(trans.get("MSG_NOTIF_TOO_LONG", lang).format(MAX_NOTIF_LENGTH, len(change)))
                    return

                handler.update_var(message.guild.id, "kickmsg", change)
                await message.channel.send(trans.get("MSG_KICKMSG", lang))

        # !leavemsg
        elif startswith(prefix + "leavemsg"):
            change = message.content[len(prefix + "leavemsg "):].strip(" ")

            if not change:
                leavemsg = handler.get_var(message.guild.id, "leavemsg")

                if is_disabled(leavemsg):
                    await message.channel.send(trans.get("MSG_LEAVE_IS_DISABLED", lang))
                else:
                    await message.channel.send(trans.get("MSG_LEAVE_CURRENT", lang).format(leavemsg))

            elif is_disabled(change):
                handler.update_var(message.guild.id, "leavemsg", None)
                await message.channel.send(trans.get("MSG_LEAVE_DISABLED", lang))

            else:
                if len(change) > MAX_NOTIF_LENGTH:
                    await message.channel.send(trans.get("MSG_NOTIF_TOO_LONG", lang).format(MAX_NOTIF_LENGTH, len(change)))
                    return

                handler.update_var(message.guild.id, "leavemsg", change)
                await message.channel.send(trans.get("MSG_LEAVE", lang))

        # !user
        elif startswith(prefix + "user"):
            # Selects the proper user
            name = message.content[len(prefix + "user "):].strip(" ")

            if name == "":
                member = message.author
            else:
                member = await self.resolve_user(name, message, lang, no_error=True)

            # If the member does not exist / none was mentioned
            if not member:
                await message.channel.send(trans.get("ERROR_NO_USER", lang))
                return

            # Gets info
            name = member.name
            mid = member.id
            bot = trans.get("MSG_USERINFO_BOT", lang) if member.bot else trans.get("MSG_USERINFO_PERSON", lang)

            # @everyone in embeds doesn't mention
            role = "**" + str(member.top_role) + "**"

            account_created = str(member.created_at).rsplit(".")[0]
            status = str(member.status)

            if status == "online":
                color = Colour.green()
            elif status == "idle":
                color = Colour.gold()
            elif status == "offline":
                color = Colour.darker_grey()
            else:
                color = Colour.red()

            embed = Embed(colour=color)
            embed.set_author(name="{}#{}".format(name, member.discriminator), icon_url=member.avatar_url)

            embed.add_field(name=trans.get("MSG_USERINFO_STATUS", lang), value=status.capitalize())
            embed.add_field(name=trans.get("MSG_USERINFO_MENTION", lang), value=member.mention)
            embed.add_field(name=trans.get("MSG_USERINFO_ID", lang), value=mid)
            embed.add_field(name=trans.get("MSG_USERINFO_TYPE", lang), value=bot)
            embed.add_field(name=trans.get("MSG_USERINFO_TOPROLE", lang), value=role)
            embed.add_field(name=trans.get("MSG_USERINFO_CREATION", lang), value=account_created)

            embed.set_image(url=member.avatar_url)

            c_time = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %B %Y")
            embed.set_footer(text=trans.get("MSG_USERINFO_DATEGOT", lang).format(c_time))

            await message.channel.send(trans.get("MSG_USERINFO_USER", lang), embed=embed)

        # !role
        elif startswith(prefix + "role"):
            if len(message.role_mentions) > 2:
                await message.channel.send(trans.get("ERROR_MENTION_ONE_ROLE", lang))
                return

            # !role add [role name] | [@mention @mention ...] OR !role add [role name] @mention
            if startswith(prefix + "role add "):
                role, users = await self._role_command_parameters(message, lang, len(prefix + "role add "))

                # Checks permissions
                if not self.can_access_role(message.author, role):
                    await message.channel.send(trans.get("PERM_HIERARCHY", lang))
                    return

                already_had = False
                # Adds role to each user
                for user in users:
                    if role in user.roles:
                        already_had = True

                    await user.add_roles(role)

                if already_had:
                    await message.channel.send(trans.get("MSG_ROLE_ALREADY_HAD", lang))
                else:
                    if len(users) == 1:
                        await message.channel.send(trans.get("INFO_DONE", lang) + " " + StandardEmoji.OK)
                    else:
                        await message.channel.send(trans.get("MSG_ROLE_ADDED_MP", lang).format(role.name, len(users)))

            # !role remove [role name] | [@mention @mention ...] OR !role add [role name] @mention
            elif startswith(prefix + "role remove "):
                role, users = await self._role_command_parameters(message, lang, len(prefix + "role remove "))

                if not self.can_access_role(message.author, role):
                    await message.channel.send(trans.get("PERM_HIERARCHY", lang))
                    return

                didnt_have = False
                # Removes role from each user
                for user in users:
                    if role not in user.roles:
                        didnt_have = True

                    await user.remove_roles(role)

                if didnt_have:
                    await message.channel.send(trans.get("MSG_ROLE_REMOVE_SOME_DIDNT", lang))

                else:
                    if len(users) == 1:
                        await message.channel.send(trans.get("INFO_DONE", lang) + " " + StandardEmoji.OK)
                    else:
                        await message.channel.send(trans.get("MSG_ROLE_REMOVED_MP", lang).format(role.name, len(users)))

            # !role / !role help
            else:
                await message.channel.send(trans.get("MSG_ROLE_HELP", lang))

        # !cmd add
        elif startswith(prefix + "cmd add"):
            cut = message.content[len(prefix + "cmd add "):].split("|", maxsplit=1)

            if len(cut) < 2:
                await message.channel.send(trans.get("MSG_CMD_WRONG_PARAMS", lang).format(prefix))
                return

            if handler.get_command_amount(message.guild.id) >= CMD_LIMIT:
                await message.channel.send(trans.get("MSG_CMD_LIMIT_EXCEEDED", lang).format(CMD_LIMIT))
                return

            trigger, resp = cut[0].strip(" "), cut[1].strip(" ")

            if not trigger or not resp:
                await message.channel.send(trans.get("MSG_CMD_EMPTY", lang))
                return

            if handler.custom_command_exists(message.guild.id, trigger):
                conf = trans.get("INFO_CONFIRM", lang)

                await message.channel.send(trans.get("MSG_CMD_ALREADY_EXISTS", lang).format(conf))

                def is_author(c):
                    return c.author == message.author and c.channel == message.channel and c.content == conf

                # Wait for confirmation
                try:
                    await client.wait_for("message", check=is_author, timeout=15)
                except asyncio.TimeoutError:
                    await message.channel.send(trans.get("MSG_CMD_TIMEOUT", lang))
                    return
                # Else, continue normally - overwrites the command
                else:
                    pass


            if len(trigger) >= CMD_LIMIT_T:
                await message.channel.send(trans.get("MSG_CMD_NAME_TOO_LONG", lang).format(CMD_LIMIT_T, len(trigger)))
                return
            if len(resp) >= CMD_LIMIT_A:
                await message.channel.send(trans.get("MSG_CMD_RESPONSE_TOO_LONG", lang).format(CMD_LIMIT_A, len(resp)))
                return

            handler.set_command(message.guild, trigger, resp)
            await message.channel.send(trans.get("MSG_CMD_ADDED", lang).format(cut[0].strip(" ")))

        # !cmd remove
        elif startswith(prefix + "cmd remove"):
            cut = message.content[len(prefix + "cmd remove "):].strip(" ")

            if not cut:
                await message.channel.send(trans.get("MSG_CMD_REMOVE_PARAMS", lang))
                return

            success = handler.remove_command(message.guild, cut)
            if success:
                await message.channel.send(trans.get("INFO_OK", lang) + " " + StandardEmoji.OK)
            else:
                await message.channel.send(trans.get("MSG_CMD_REMOVE_FAIL", lang))

        # !cmd list
        elif startswith(prefix + "cmd list"):
            page = str(message.content)[len(prefix + "cmd list"):].strip(" ")

            try:
                page = int(page)

                if page != 0:
                    page -= 1
            # If no page is specified
            except ValueError:
                page = 0

            custom_cmds = handler.get_custom_commands(message.guild.id)

            if not custom_cmds:
                await message.channel.send(trans.get("MSG_CMD_NO_CUSTOM", lang).format(prefix))
                return

            cmd_list, c_page = make_pages_from_dict(custom_cmds)

            # If user requests a page that does not exist
            if page > c_page:
                await message.channel.send(trans.get("MSG_CMD_LIST_NO_PAGE", lang).format(c_page + 1))
                return

            final = trans.get("MSG_CMD_LIST", lang).format(page + 1, c_page + 1, "\n".join(cmd_list[page]))

            # Mark for reaction monitoring
            msg_list = await message.channel.send(final)
            await self.list.new_message(msg_list, page, cmd_list, trans.get("MSG_CMD_LIST", lang))

        # !cmd status
        elif startswith(prefix + "cmd status"):
            cc = handler.get_custom_commands(message.guild.id)
            await message.channel.send(trans.get("MSG_CMD_STATUS", lang).format(len(cc), CMD_LIMIT))

        # !language
        elif startswith(prefix + "language"):
            cut = message.content[len(prefix + "language "):].strip(" ")

            # !language list
            if cut.startswith("list"):
                lang_list = []
                for l_code, l_details in self.trans.meta.items():

                    if l_code == "en":
                        entry = "`{}` - **{}**".format(l_code, l_details.get("name"))
                        lang_list.append(entry)

                    else:
                        contribs = ", ".join(l_details.get("authors"))
                        entry = "`{}` - **{}** {}".format(l_code, l_details.get("name"), trans.get("MSG_LANG_TRANS", lang).format(contribs))
                        lang_list.append(entry)

                await message.channel.send(trans.get("MSG_LANG_LIST", lang).format("\n".join(lang_list)))

            # !language set [lang]
            elif cut.startswith("set"):
                lang_code = cut[len("set "):].strip(" ").lower()

                if not self.trans.is_language_code(lang_code):
                    # Try to find the language by name
                    lang_code = self.trans.find_language_code(lang_code)
                    if not lang_code:
                        await message.channel.send(trans.get("MSG_LANG_NOT_AVAILABLE", lang))
                        return

                self.handler.set_lang(message.guild.id, lang_code)

                await message.channel.send(trans.get("MSG_LANG_SET", lang).format(
                                                                     lang_code, trans.get("INFO_HELLO", lang_code)))

            # !language
            # Displays current language
            else:
                resp = trans.get("MSG_LANG_CURRENT", lang).format(lang, self.trans.meta.get(lang).get("name"), prefix)
                await message.channel.send(resp)

        # nano.settings
        elif startswith("nano.settings"):
            raw = message.content[len("nano.settings "):]
            cut = raw.split(" ", 1)

            if len(cut) < 2:
                await message.channel.send(trans.get("MSG_SETTINGS_WRONG_USAGE", lang).format(prefix))
                return

            setting, arg = cut[0].strip(" "), cut[1].strip(" ")

            # nano.settings logchannel
            if setting == "logchannel":
                if len(message.channel_mentions) == 0:
                    # User wants to disable the logchannel
                    if is_disabled(arg):
                        handler.set_custom_channel(message.guild.id, "logchannel", None)
                        await message.channel.send(trans.get("MSG_SETTINGS_LOGCHANNEL_DISABLED", lang))
                        return

                    # No channel mention / parameter
                    else:
                        await message.channel.send(trans.get("ERROR_NO_CHMENTION", lang))
                        return

                chan = message.channel_mentions[0]

                # Can't set to voice channel
                if not isinstance(chan, TextChannel):
                    await message.channel.send(trans.get("MSG_SETTINGS_NOT_TEXT", lang))
                    return

                # At this point, the channel should be valid
                handler.set_custom_channel(message.guild.id, "logchannel", chan.id)
                await message.channel.send(trans.get("MSG_SETTINGS_LOGCHANNEL_SET", lang).format(chan.name))

            # nano.settings selfrole
            elif setting == "selfrole":
                # For branching - splits the argument again
                try:
                    setting, arg = arg.split(" ", 1)
                    setting, arg = setting.strip(" "), arg.strip(" ")
                except ValueError:
                    await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                    return

                # nano.settings selfrole add
                if setting == "add":
                    # Checks if role amount is passed
                    amount = len(handler.get_selfroles(message.guild.id))
                    if amount >= SELFROLE_MAX:
                        await message.channel.send(trans.get("MSG_SELFROLE_TOO_MANY", lang).format(SELFROLE_MAX))
                        return

                    role = await self.resolve_role(arg, message, lang)

                    nano_user = utils.find(lambda me: me.id == client.user.id, message.guild.members)
                    if not nano_user:
                        log_to_file("SELFROLE: Nano Member is NONE", "bug")
                        return

                    # Checks role position
                    # perms = self.can_access_role(nano_user, role)
                    perms = await self.try_accessing_role(nano_user, role)
                    if not perms:
                        await message.channel.send(trans.get("MSG_SELFROLE_INACCESSIBLE", lang).format(role.name))
                        return

                    r_name = role.name

                    # Check if this role is already a selfrole
                    if self.handler.is_selfrole(message.guild.id, r_name):
                        await message.channel.send(trans.get("MSG_SELFROLE_ALR_EX", lang))
                        return

                    self.handler.add_selfrole(message.guild.id, r_name)
                    await message.channel.send(trans.get("MSG_SELFROLE_ADMIN_ADDED", lang))

                # nano.settings selfrole remove
                elif setting == "remove":
                    role = await self.resolve_role(arg, message, lang)
                    r_name = role.name

                    if not self.handler.is_selfrole(message.guild.id, r_name):
                        await message.channel.send(trans.get("MSG_SELFROLE_REMOVE_NOT_PRESENT", lang))
                        return

                    self.handler.remove_selfrole(message.guild.id, r_name)
                    await message.channel.send(trans.get("MSG_SELFROLE_ADMIN_REMOVED", lang).format(r_name))

            # nano.settings defaultchannel
            elif setting == "defaultchannel":
                if len(message.channel_mentions) == 0:
                    # User wants to reset the channel
                    if is_disabled(arg):
                        handler.set_custom_channel(message.guild.id, "logchannel", None)
                        def_chan = await self.default_channel(message.guild)
                        await message.channel.send(trans.get("MSG_SETTINGS_DEFCHAN_RESET", lang).format(def_chan.name))
                        return

                    # No channel mention / parameter
                    else:
                        await message.channel.send(trans.get("ERROR_NO_CHMENTION", lang))
                        return

                chan = message.channel_mentions[0]

                self.handler.set_defaultchannel(message.guild, chan.id)
                await message.channel.send(trans.get("MSG_SETTINGS_DEFCHAN_SET", lang).format(chan.name))

            else:
                # Requires special preparation
                spl = raw.rsplit(" ", maxsplit=1)
                setting, arg = spl[0], spl[1]

                # Set word/spam/invite filter
                # Pre-parsed into a list
                if matches_iterable(setting, trans.get("MSG_SETTINGS_WF_OPTIONS", lang)):
                    decision = matches_iterable(arg)
                    handler.update_moderation_settings(message.guild.id, setting, decision)

                    await message.channel.send(trans.get("MSG_SETTINGS_WORD", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

                elif matches_iterable(setting, trans.get("MSG_SETTINGS_SF_OPTIONS", lang)):
                    decision = matches_iterable(arg)
                    handler.update_moderation_settings(message.guild.id, setting, decision)

                    await message.channel.send(trans.get("MSG_SETTINGS_SPAM", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

                elif matches_iterable(setting, trans.get("MSG_SETTINGS_IF_OPTIONS", lang)):
                    decision = matches_iterable(arg)
                    handler.update_moderation_settings(message.guild.id, setting, decision)

                    await message.channel.send(trans.get("MSG_SETTINGS_INVITE", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

                else:
                    await message.channel.send(trans.get("MSG_SETTINGS_NOT_A_SETTING", lang).format(setting))

        # nano.displaysettings
        elif startswith("nano.displaysettings"):
            settings = handler.get_server_data(message.guild)

            # Parse blacklisted channels
            blacklisted_c = settings.get("blacklist")
            if not blacklisted_c:
                blacklisted_c = "> " + trans.get("MSG_SETTINGS_NO_BLACKLIST", lang)

            else:
                # Builds a list
                blacklisted = []
                for ch_id in blacklisted_c:
                    channel_r = utils.find(lambda c: c.id == ch_id, message.guild.channels)

                    if not channel_r:
                        self.handler.remove_channel_blacklist(message.guild.id, ch_id)
                        continue

                    blacklisted.append(channel_r.name)

                blacklisted_c = ", ".join(blacklisted)

            # Generic messages
            ON = "* " + trans.get("INFO_ON", lang)
            OFF = "* " + trans.get("INFO_OFF", lang)
            DISABLED = "> " + trans.get("INFO_DISABLED", lang)

            # Filters
            spam_filter = ON if settings.get(SPAMFILTER_SETTING) else OFF
            word_filter = ON if settings.get(WORDFILTER_SETTING) else OFF
            invite_filter = ON if settings.get(INVITEFILTER_SETTING) else OFF

            # Log channel
            l_obj = await self.handle_log_channel(message.guild)
            if l_obj is None:
                log_channel = DISABLED
            else:
                log_channel = "[{}]({})".format(l_obj.name, l_obj.id)

            # Default channel
            d_channel = await self.default_channel(message.guild)
            if is_disabled(d_channel):
                d_channel = DISABLED
            else:
                d_channel = "[{}]({})".format(d_channel.name, d_channel.id)

            msg_join = settings.get("welcomemsg")
            if is_disabled(msg_join):
                msg_join = DISABLED
            msg_leave = settings.get("leavemsg")
            if is_disabled(msg_leave):
                msg_leave = DISABLED
            msg_ban = settings.get("banmsg")
            if is_disabled(msg_ban):
                msg_ban = DISABLED
            msg_kick = settings.get("kickmsg")
            if is_disabled(msg_kick):
                msg_kick = DISABLED

            sett = trans.get("MSG_SETTINGS_DISPLAY", lang).format(prefix, blacklisted_c, spam_filter,
                                                                  word_filter, invite_filter, log_channel, d_channel)
            msgs = trans.get("MSG_SETTINGS_DISPLAY_2", lang).format(msg_join, msg_leave, msg_kick, msg_ban)

            # Send, depending on the length
            if (len(sett) + len(msgs)) > 2000:
                # Send individually
                try:
                    await message.channel.send(sett)
                    await message.channel.send(msgs)
                except HTTPException:
                    await message.channel.send(trans.get("ERROR_MSG_TOO_LONG", lang))

            else:
                # Send in one piece
                await message.channel.send(sett + "\n" + msgs)


        # nano.blacklist
        elif startswith("nano.blacklist"):
            setting = message.content[len("nano.blacklist "):].strip(" ").split(" ")[0]

            # nano.blacklist add
            if setting == "add":
                if len(handler.get_blacklists(message.guild.id)) >= BLACKLIST_MAX:
                    await message.channel.send(trans.get("MSG_BLACKLIST_TOO_MANY", lang))
                    return

                if len(message.channel_mentions) == 0:
                    await message.channel.send(trans.get("ERROR_NO_CHMENTION", lang))
                    return

                chan_id = message.channel_mentions[0].id

                self.handler.add_channel_blacklist(message.guild.id, chan_id)
                await message.channel.send(trans.get("MSG_BLACKLIST_ADDED", lang).format(chan_id))

            # nano.blacklist remove
            elif setting == "remove":
                if len(message.channel_mentions) == 0:
                    await message.channel.send(trans.get("ERROR_NO_CHMENTION", lang))
                    return

                chan_id = message.channel_mentions[0].id

                if not handler.is_blacklisted(message.guild.id, chan_id):
                    await message.channel.send(trans.get("MSG_BLACKLIST_DOESNT_EXIST", lang))
                    return

                handler.remove_channel_blacklist(message.guild.id, chan_id)
                await message.channel.send(trans.get("MSG_BLACKLIST_REMOVED", lang).format(chan_id))

            # nano.blacklist list
            elif setting == "list":
                lst = self.handler.get_blacklists(message.guild.id)

                if not lst:
                    await message.channel.send(trans.get("MSG_BLACKLIST_NONE", lang))
                    return

                # Verifies channels
                names = []
                for ch_id in lst:
                    channel = message.guild.get_channel(int(ch_id))
                    # If channel was deleted, remove it from the list
                    if not channel:
                        self.handler.remove_channel_blacklist(message.guild.id, ch_id)
                    else:
                        names.append("`{}`".format(channel.name))

                if not names:
                    await message.channel.send(trans.get("MSG_BLACKLIST_NONE", lang))
                    return

                await message.channel.send(trans.get("MSG_BLACKLIST_LIST", lang).format(" ".join(names)))

        # nano.serverreset
        elif startswith("nano.serverreset"):
            confirm = trans.get("INFO_CONFIRM", lang)
            await message.channel.send(trans.get("MSG_RESET_CONFIRM", lang).format(confirm))

            def is_author(c):
                return c.author == message.author and c.channel == message.channel and c.content == confirm
            try:
                await client.wait_for("message", check=is_author, timeout=15)
            except asyncio.TimeoutError:
                await message.channel.send(trans.get("MSG_RESET_CONFIRM_TIMEOUT", lang))
                return

            handler.reset_server(message.guild)
            await message.channel.send(trans.get("MSG_RESET_DONE", lang))

        # nano.changeprefix
        elif startswith("nano.changeprefix"):
            pref = message.content[len("nano.changeprefix "):]

            # Replaces special characters!
            pref = parse_special_chars(pref)

            if not pref:
                await message.channel.send(trans.get("MSG_PREFIX_PLS_ARGUMENTS", lang))
                return

            # Max prefix length
            if len(pref) > PREFIX_MAX:
                await message.channel.send(trans.get("ERROR_PREFIX_TOO_LONG", lang).format(PREFIX_MAX))
                return

            self.handler.change_prefix(message.guild, pref)

            await message.channel.send(trans.get("MSG_PREFIX_CHANGED", lang).format(pref))

        # !setup, nano.setup
        elif startswith(prefix + "setup", "nano.setup"):
            MSG_TIMEOUT = 60

            YES = trans.get("INFO_YES", lang)
            YES_L = YES.lower()
            NO = trans.get("INFO_NO", lang)

            OK = trans.get("INFO_OK", lang)
            NONE = trans.get("INFO_NONE", lang)
            DONE = trans.get("INFO_DONE", lang)

            ENABLED = trans.get("INFO_ENABLED", lang)
            DISABLED = trans.get("INFO_DISABLED", lang)

            # Padded strings
            YES_PD, NO_PD = apply_string_padding((YES, NO))

            DONE_EXPR = StandardEmoji.OK + " " + DONE
            IGNORED_EXPR = StandardEmoji.GREEN_FAIL + " " + OK
            EN_EXPR = StandardEmoji.OK + " " + ENABLED
            DIS_EXPR = StandardEmoji.GREEN_FAIL + " " + DISABLED

            async def timeout():
                await message.channel.send(trans.get("MSG_SETUP_TIMEOUT", lang).format(MSG_TIMEOUT))

            def must_be_author(c):
                return c.author == message.author

            await message.channel.send(trans.get("MSG_SETUP_WELCOME", lang))
            await asyncio.sleep(3)


            # FIRST MESSAGE
            # Q: Do you want to reset all current settings?
            msg_one = trans.get("MSG_SETUP_RESET", lang).format(yes=YES_PD, no=NO_PD)
            one = await message.channel.send(msg_one)

            # Wait for first response
            try:
                ch1 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            # User confirmed the action
            else:
                if ch1.content.lower().strip(" ") == YES_L:
                    handler.server_setup(message.guild)

                    # Edit message to confirm action
                    edit = msg_one + "\n\n " + DONE_EXPR
                    await one.edit(content=edit)

                else:
                    # Edit message to confirm action
                    edit = msg_one + "\n\n " + IGNORED_EXPR
                    await one.edit(content=edit)


            # SECOND MESSAGE
            # Q: What prefix do you want?
            PREF_PD = apply_string_padding((trans.get("MSG_SETUP_PREFIX_TEXT", lang), ))
            msg_two = trans.get("MSG_SETUP_PREFIX", lang).format(prefix=PREF_PD)
            two = await message.channel.send(msg_two)

            # Second check, does not need yes/no filter
            try:
                ch2 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            else:
                if len(ch2.content) > 50:
                    await message.channel.send(trans.get("ERROR_PREFIX_TOO_LONG", lang))
                    return

                pref = ch2.content.strip(" ")
                handler.change_prefix(message.guild, pref)

                # Edit to show that the prefix has been changed
                edit = msg_two + "\n\n{} - **{}**".format(DONE_EXPR, pref)
                await two.edit(content=edit)


            # THIRD MESSAGE
            # Q: What message would you like to see when a person joins your server?
            TEXT_PD, NONE_PD = apply_string_padding((trans.get("MSG_SETUP_JOINMSG_TEXT", lang), NONE))
            msg_three = trans.get("MSG_SETUP_JOINMSG", lang).format(text=TEXT_PD, none=NONE_PD)
            three = await message.channel.send(msg_three)

            try:
                ch3 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            else:
                welcome_msg = ch3.content.strip(" ")

                # Set the welcome msg to appropriate value
                if is_disabled(welcome_msg):
                    handler.update_var(message.guild.id, "welcomemsg", None)
                    edit = msg_three + "\n\n " + DIS_EXPR
                else:
                    handler.update_var(message.guild.id, "welcomemsg", welcome_msg)
                    edit = "{}\n\n{} {}".format(msg_three, StandardEmoji.OK, trans.get("INFO_UPDATED", lang))

                # Again: edit to show that the welcome msg has been changed
                await three.edit(content=edit)


            # FOURTH MESSAGE
            # Q: Spam filter
            msg_four = trans.get("MSG_SETUP_SPAM", lang).format(yes=YES_PD, no=NO_PD)
            four = await message.channel.send(msg_four)

            # Fourth check
            try:
                ch4 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            else:
                if ch4.content.lower().strip(" ") == YES_L:
                    handler.update_moderation_settings(message.guild.id, "filterspam", True)
                    edit = msg_four + "\n\n " + EN_EXPR
                else:
                    handler.update_moderation_settings(message.guild.id, "filterspam", False)
                    edit = msg_four + "\n\n" + DIS_EXPR

                # Edit to show that filtering is changed
                await four.edit(content=edit)


            # FIFTH MESSAGE
            # Q: swearing filter
            msg_five = trans.get("MSG_SETUP_SWEARING", lang).format(yes=YES_PD, no=NO_PD)
            five = await message.channel.send(msg_five)

            # Wait for response
            try:
                ch5 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            else:
                if ch5.content.lower().strip(" ") == YES_L:
                    handler.update_moderation_settings(message.guild.id, "filterwords", True)
                    edit = msg_four + "\n\n " + EN_EXPR
                else:
                    handler.update_moderation_settings(message.guild.id, "filterwords", False)
                    edit = msg_four + "\n\n " + DIS_EXPR

                # Edit to show that filtering is changed
                await five.edit(content=edit)


            # SIXTH (LAST) MESSAGE
            # Q: What channel would you like to use for logging?
            CHANNEL_PD, NONE_PD1 = apply_string_padding((trans.get("MSG_SETUP_LOGCHANNEL_MENTION", lang), NONE))

            msg_six = trans.get("MSG_SETUP_LOGCHANNEL", lang).format(mention=CHANNEL_PD, none=NONE_PD1)
            six = await message.channel.send(msg_six)

            try:
                ch6 = await client.wait_for("message", check=must_be_author, timeout=MSG_TIMEOUT)
            except asyncio.TimeoutError:
                await timeout()
                return

            else:
                # Parses channel
                channel = ch6.content.strip(" ")

                # Disabling works in both languages
                if channel.lower() == NONE or is_disabled(channel.lower()):
                    handler.set_custom_channel(message.guild.id, "logchannel", None)

                    # Edit to show that filtering is changed
                    edit = msg_six + "\n\n{} {}".format(StandardEmoji.OK_BLUE, trans.get("MSG_SETUP_LOGCHANNEL_DISABLED", lang))
                    await six.edit(content=edit)

                else:
                    if len(ch6.channel_mentions) != 0:
                        handler.set_custom_channel(message.guild.id, "logchannel", ch6.channel_mentions[0].id)
                    else:
                        await message.channel.send(trans.get("MSG_SETUP_LOGCHANNEL_INVALID", lang))
                        return

                    # Edit to show that filtering is changed
                    edit = msg_six + "\n\n{} {}".format(StandardEmoji.OK_BLUE, trans.get("MSG_SETUP_LOGCHANNEL_SET", lang).format(ch6.channel_mentions[0].name))
                    await six.edit(content=edit)

            # FINAL MESSAGE, formats with new prefix
            msg_final = trans.get("MSG_SETUP_COMPLETE", lang).replace("_", str(ch2.content))
            await message.channel.send(msg_final)

    async def on_member_remove(self, member, **_):
        # check for softban
        if self.timer.is_guild_ban(member.guild.id, member.id):
            return "return"

        # check for normal ban
        # Prevents double messages
        elif member.id in self.bans:
            self.bans.remove(member.id)
            return "return"

    async def on_reaction_add(self, reaction, user, **kwargs):
        await self.list.handle_reaction(reaction, user, **kwargs)


class NanoPlugin:
    name = "Admin Commands"
    version = "33"

    handler = Admin
    events = {
        "on_message": 10,
        "on_member_remove": 4,
        "on_reaction_add": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
