# coding=utf-8
import asyncio
import datetime
import logging
import time

from typing import Union
from discord import Message, utils, Client, Embed, Colour, DiscordException, HTTPException, Object, errors as derrors

from data.serverhandler import INVITEFILTER_SETTING, SPAMFILTER_SETTING, WORDFILTER_SETTING
from data.stats import WRONG_ARG
from data.utils import convert_to_seconds, matches_list, is_valid_command, StandardEmoji, decode, resolve_time, log_to_file, is_disabled, IgnoredException


#####
# Administration plugin
# Mostly Nano settings
#####

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS
CMD_LIMIT = 40
CMD_LIMIT_T = 40
CMD_LIMIT_A = 500
TICK_DURATION = 15

# 15 seconds
REMINDER_MIN = 15
# 5 Days
REMINDER_MAX = 5 * 24 * 60 * 60

# Maximum age (in seconds) of a message that should be kept in cache
MAX_MSG_AGE = 60 * 3
MAX_MSG_AGE = 20

commands = {
    "_ban": {"desc": "Bans a member.", "use": "[command] [mention]", "alias": "nano.ban"},
    "nano.ban": {"desc": "Bans a member.", "use": "User: [command] [mention]", "alias": "_ban"},
    "_kick": {"desc": "Kicks a member.", "use": "[command] [mention]", "alias": "nano.kick"},
    "nano.kick": {"desc": "Kicks a member", "use": "[command] [mention]", "alias": "_kick"},
    "_unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "nano.unban"},
    "nano.unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "_unban"},
    "_softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "[command] @mention/username | [time] or [command] @mention [time]", "alias": None},
    "_cmd add": {"desc": "Adds a command to the server.", "use": "[command] command|response", "alias": None},
    "_cmd remove": {"desc": "Removes a command from the server.", "use": "[command] command", "alias": None},
    "_cmd status": {"desc": "Displays how many commands you have and how many more you can register.", "use": "[command] command", "alias": None},
    "_cmd list": {"desc": "Returns a server-specific command list.", "use": "[command] (page number)", "alias": None},

    "_mute": {"desc": "Mutes the user - deletes all future messages from the user until he/she is un-muted.", "use": "[command] [mention or name]", "alias": None},
    "_unmute": {"desc": "Un-mutes the user (see mute help for more info).", "use": "[command] [mention or name]", "alias": None},
    "_muted": {"desc": "Displays a list of all members currently muted.", "use": None, "alias": None},
    # "_purge": {"desc": "Deletes the messages from the specified user in the last x messages", "use": "[command] [amount] [user name]", "alias": None},

    "_setup": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "use": None, "alias": "nano.setup"},
    "nano.setup": {"desc": "Helps admins set up basic settings for the bot (guided setup).", "use": None, "alias": "_setup"},
    "_user": {"desc": "Displays info about the user", "use": "[command] [@mention or name]", "alias": None},
    "_welcomemsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @user, ':server' = server name", "use": "[command] [content]", "alias": "_joinmsg"},
    "_joinmsg": {"desc": "Sets the message sent when a member joins the server.\nFormatting: ':user' = @user, ':server' = server name", "use": "[command] [content]", "alias": "_welcomemsg"},
    "_banmsg": {"desc": "Sets the message sent when a member is banned.\nFormatting: ':user' = user name", "use": "[command] [content]", "alias": None},
    "_kickmsg": {"desc": "Sets the message sent when a member is kicked.\nFormatting: ':user' = user name", "use": "[command] [content]", "alias": None},
    "_leavemsg": {"desc": "Sets the message sent when a member leaves the server.\nFormatting: ':user' = user name", "use": "[command] [content]", "alias": None},
    "_nuke": {"desc": "Nukes (deletes) last x messages. (keep in mind that you can only nuke messages up to 2 weeks old)", "use": None, "alias": None},

    "nano.blacklist add": {"desc": "Adds a channel to command blacklist.", "use": "[command] [channel name]", "alias": None},
    "nano.blacklist remove": {"desc": "Removes a channel from command blacklist", "use": "[command] [channel name]", "alias": None},
    "nano.blacklist list": {"desc": "Shows all blacklisted channels on this server", "use": "[command]", "alias": None},

    "nano.settings": {"desc": "Sets server settings like word, spam, invite filtering, log channel and selfrole.\nPossible setting keyords: wordfilter, spamfilter, invitefilter, logchannel, selfrole, defaultchannel", "use": "[command] [setting] True/False", "alias": None},
    "nano.displaysettings": {"desc": "Displays all server settings.", "use": None, "alias": None},
    "nano.changeprefix": {"desc": "Changes the prefix on the server.", "use": "[command] prefix", "alias": None},
    "nano.serverreset": {"desc": "Resets all server settings to the default.", "use": None, "alias": None},

    "_role add": {"desc": "Adds a role to the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role remove": {"desc": "Removes a role from the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role replaceall": {"desc": "Replace all roles with the specified one for a user.", "use": "[command] [role name] [mention]", "alias": None},

    "_language": {"desc": "Displays the current language you're using. \nSee `_language list` for available languages or use `_language set [language_code] to set your language.", "use": "[command] [argument]", "alias": None},
    "_language list": {"desc": "Lists all available languages", "use": "[command]", "alias": None},
    "_language set": {"desc": "Sets the language for the current server.", "use": "[command] [language_code]", "alias": None}
}

class RedisSoftBanScheduler:
    def __init__(self, client, handler, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop
        self.redis = handler.get_plugin_data_manager(namespace="softban")

    def get_ban(self, user_id):
        return self.redis.hgetall(user_id)

    def get_all_bans(self):
        return [self.get_ban(decode(a).strip("softban:")) for a in self.redis.scan_iter("*")]

    def remove_ban(self, user):
        if self.redis.exists(user.id):
            self.loop.create_task(self.dispatch(self.get_ban(user.id)))
            self.redis.remove(user.id)

    def set_softban(self, server, user, tim):
        t = time.time()

        if not str(tim).isdigit():
            tim = convert_to_seconds(tim)
        else:
            tim = int(tim)

        if not (REMINDER_MIN <= tim <= REMINDER_MAX):
            return False

        # Add the reminder to the list
        payload = {"member": user.id, "server": server.id, "time_target": int(t + tim)}

        return self.redis.hmset(user.id, payload)

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

    async def dispatch(self, reminder):
        try:
            logger.debug("Dispatching")
            await self.client.unban(Object(id=reminder.get("server")), Object(id=reminder.get("member")))
        except DiscordException as e:
            logger.warning(e)

    async def start_monitoring(self):
        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for ban in self.get_all_bans():
                # If time is up, send the reminder
                if int(ban.get("time_target", 0)) <= last_time:
                    await self.dispatch(ban)
                    self.redis.delete(ban.get("member"))

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
        if sum([len(a) for a in cmd_list[c_page]]) > 1250:
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
        if sum([len(a) for a in cmd_list[c_page]]) > 15:
            c_page += 1
            cmd_list[c_page] = []

        cmd_list[c_page].append("➤ " + str(item))

    # dict(page_index:[lines], etc...), total_pages
    return cmd_list, c_page

class CommandListReactions:
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

    async def new_message(self, message, page, cmds):
        # Ignore if there is only one page
        if len(cmds.keys()) == 1:
            return

        # Adds reactions for navigation
        await self.client.add_reaction(message, CommandListReactions.UP)
        await self.client.add_reaction(message, CommandListReactions.DOWN)

        # Caches data into MessageTracker
        data = {
            "page": int(page),
            "serv_id": message.server.id,
            "cmds": cmds
        }

        self.track.set_message_data(message.id, data)

    async def handle_reaction(self, reaction, user, **kwargs):
        # Ignore reactions from self
        if user.id == self.client.user.id:
            return

        msg = reaction.message
        lang = kwargs.get("lang")

        # Get and verify data existence
        data = self.track.get_message_data(msg.id)
        if not data:
            return

        c_page = data.get("page")
        page_amount = len(data.get("cmds").keys())

        # Default to down, even though it should always change
        # True - up
        # False - down
        up_down = None
        for react in msg.reactions:

            if react.count > 1:
                if react.emoji == CommandListReactions.UP:
                    up_down = True
                    break
                elif react.emoji == CommandListReactions.DOWN:
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

            page = data.get("cmds").get(c_page - 1)
            c_page -= 1

        # False - goes down one page
        else:
            # Can't go lower
            if c_page + 1 >= page_amount:
                return

            page = data.get("cmds").get(c_page + 1)
            c_page += 1

        # Reset reactions and edit message
        await self.client.clear_reactions(msg)

        new_msg = self.trans.get("MSG_CMD_LIST", lang).format(c_page + 1, page_amount, "\n".join(page))
        await self.client.edit_message(msg, new_msg)

        await self.client.add_reaction(msg, CommandListReactions.UP)
        await self.client.add_reaction(msg, CommandListReactions.DOWN)

        # Updates the page counter
        data["page"] = c_page
        self.track.set_message_data(msg.id, data)

class MuteListReactions:
    __slots__ = (
        "client", "handler", "trans", "track"
    )

    # Emojis to react with
    UP = "\U000023EB"
    DOWN = "\U000023EC"

    def __init__(self, client, handler, trans):
        self.client = client
        self.handler = handler
        self.trans = trans

        self.track = MessageTracker()

    async def new_message(self, message, page: int, mute_list: dict):
        # Ignore if there is only one page
        if len(mute_list) == 1:
            return

        # Adds reactions for navigation
        await self.client.add_reaction(message, MuteListReactions.UP)
        await self.client.add_reaction(message, MuteListReactions.DOWN)

        # Caches data into MessageTracker
        data = {
            "page": int(page),
            "serv_id": message.server.id,
            "mutes": mute_list
        }

        self.track.set_message_data(message.id, data)

    async def handle_reaction(self, reaction, user, **kwargs):
        # Ignore reactions from self
        if user.id == self.client.user.id:
            return

        msg = reaction.message
        lang = kwargs.get("lang")

        # Get and verify data existence
        data = self.track.get_message_data(msg.id)
        if not data:
            return

        c_page = data.get("page")
        page_amount = len(data.get("mutes").keys())

        # Default to down, even though it should always change
        # True - up
        # False - down
        up_down = None
        for react in msg.reactions:

            if react.count > 1:
                if react.emoji == MuteListReactions.UP:
                    up_down = True
                    break
                elif react.emoji == MuteListReactions.DOWN:
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

            page = data.get("mutes").get(c_page - 1)
            c_page -= 1

        # False - goes down one page
        else:
            # Can't go lower
            if c_page + 1 >= page_amount:
                return

            page = data.get("mutes").get(c_page + 1)
            c_page += 1

        # Reset reactions and edit message
        await self.client.clear_reactions(msg)

        new_msg = self.trans.get("MSG_MUTE_LIST", lang).format(c_page + 1, page_amount, "\n".join(page))
        await self.client.edit_message(msg, new_msg)

        await self.client.add_reaction(msg, MuteListReactions.UP)
        await self.client.add_reaction(msg, MuteListReactions.DOWN)

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

        self.timer = RedisSoftBanScheduler(self.client, self.handler, self.loop)
        self.loop.create_task(self.timer.start_monitoring())

        self.cmd = CommandListReactions(self.client, self.handler, self.trans)
        self.mute = MuteListReactions(self.client, self.handler, self.trans)

        self.loop.create_task(self.cmd.track.start_monitoring())
        self.loop.create_task(self.mute.track.start_monitoring())

        self.bans = []

    async def resolve_role(self, name, message, lang):
        role = utils.find(lambda r: r.name == name, message.server.roles)

        # No such role - couldn't find by name
        if not role:
            # Try role mentions
            if len(message.role_mentions) != 0:
                role = message.role_mentions[0]
            else:
                await self.client.send_message(message.channel, self.trans.get("ERROR_NO_SUCH_ROLE", lang))
                return None

        return role

    async def resolve_user(self, name, message, lang, no_error=False):
        # Tries @mentions
        if len(message.mentions) > 0:
            return message.mentions[0]

        # If there's no mentions and no name provided
        if name is None:
            if no_error:
                return None
            else:
                await self.client.send_message(message.channel, self.trans.get("ERROR_NO_MENTION", lang))
                raise IgnoredException

        # No mentions, username is provided
        user = utils.find(lambda u: u.name == name, message.server.members)
        if not user:
            if no_error:
                return None
            else:
                await self.client.send_message(message.channel, self.trans.get("ERROR_NO_USER", lang))
                raise IgnoredException

        return user

    @staticmethod
    async def handle_def_channel(server, channel_id):
        if is_disabled(channel_id):
            return server.default_channel
        else:
            return utils.find(lambda c: c.id == channel_id, server.channels)

    async def on_message(self, message, **kwargs):
        client = self.client
        handler = self.handler
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        assert isinstance(message, Message)
        assert isinstance(client, Client)


        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix=prefix):
            return

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # !nuke
        if startswith(prefix + "nuke"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            amount = str(message.content)[len(prefix + "nuke "):]

            try:
                amount = int(amount) + 1  # Includes the sender's message
            except ValueError:
                await client.send_message(message.channel, trans.get("ERROR_NOT_NUMBER", lang))
                return

            await client.delete_message(message)
            await client.send_message(message.channel, trans.get("MSG_NUKE_PURGING", lang))

            additional = ""

            try:
                await client.purge_from(message.channel, limit=amount)
            except derrors.HTTPException:
                additional = trans.get("MSG_NUKE_OLD", lang)

            # Show success
            m = await client.send_message(message.channel, trans.get("MSG_NUKE_PURGED", lang).format(amount - 1) + additional)
            # Wait 1.5 sec and delete the message
            await asyncio.sleep(1.5)
            await client.delete_message(m)

        # !kick
        elif startswith(prefix + "kick") and not startswith(prefix + "kickmsg"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return

            name = message.content[len(prefix + "kick "):]
            user = await self.resolve_user(name, message, lang)

            if user.id == client.user.id:
                await client.send_message(message.channel, trans.get("MSG_KICK_NANO", lang))
                return

            await client.kick(user)
            await client.send_message(message.channel, handler.get_var(message.server.id, "kickmsg").replace(":user", user.name))

        # !ban
        elif startswith(prefix + "ban") and not startswith(prefix + "banmsg"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "kick "):]
            user = await self.resolve_user(name, message, lang)

            if user.id == client.user.id:
                await client.send_message(message.channel, trans.get("MSG_BAN_NANO", lang))
                return

            confirm = trans.get("INFO_CONFIRM", lang)
            await client.send_message(message.channel, trans.get("MSG_BAN_USER", lang).format(user.name, confirm))

            followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                     timeout=15, content=confirm)

            if followup is None:
                await client.send_message(message.channel, trans.get("MSG_BAN_TIMEOUT", lang))
                return

            self.bans.append(user.id)
            await client.ban(user, delete_message_days=0)

        # !unban
        elif startswith(prefix + "unban"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "unban "):]

            if not name:
                await client.send_message(message.channel, trans.get("MSG_UNBAN_WRONG_USAGE", lang).format(prefix))
                return

            user = None
            for ban in await self.client.get_bans(message.server):
                if ban.name == name:
                    user = ban

            if not user:
                await client.send_message(message.channel, trans.get("MSG_UNBAN_NO_BAN", lang))
                return

            await client.unban(message.server, user)
            await client.send_message(message.channel, trans.get("MSG_UNBAN_SUCCESS", lang).format(name))

        # !softban @mention/username | [time]
        elif startswith(prefix + "softban"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            cut = message.content[len(prefix + "softban "):]

            try:
                name, tim = cut.split("|")
                name, tim = name.strip(" "), tim.strip(" ")
            # In case the value can't be unpacked: no |
            except ValueError:
                if len(message.mentions) == 0:
                    await client.send_message(message.channel, trans.get("MSG_SOFTBAN_PLSMENTION", lang))
                    return

                # Alternate method: @mention [time] (without |)
                name = message.mentions[0].name
                tim = cut.replace("<@{}>".format(message.mentions[0].id), "").strip(" ")

                if tim == "":
                    await client.send_message(message.channel, trans.get("MSG_SOFTBAN_NO_TIME", lang))
                    return

            user = await self.resolve_user(name, message, lang)

            total_seconds = convert_to_seconds(tim)

            self.timer.set_softban(message.server, user, total_seconds)
            await client.ban(user, delete_message_days=0)

            await client.send_message(message.channel, trans.get("MSG_SOFTBAN_SUCCESS", lang).format(user.name, resolve_time(total_seconds, lang)))

        # !mute list
        elif startswith(prefix + "mute list"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            mutes = handler.get_mute_list(message.server)
            page = message.content[len(prefix + "mute list "):].strip(" ")
            if page:
                try:
                    page -= 1
                except ValueError:
                    await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                    return

            else:
                page = 0

            if mutes:
                # Verifies the presence of users
                muted_ppl = []
                for u_id in mutes:
                    usr = utils.find(lambda b: b.id == u_id, message.server.members)
                    if usr:
                        muted_ppl.append(usr.name)

                mute_list, m_page = make_pages_from_list(muted_ppl)

                final = trans.get("MSG_MUTE_LIST", lang).format(page + 1, m_page + 1, "\n".join(mute_list[page]))

                msg = await client.send_message(message.channel, final)
                await self.mute.new_message(msg, page, mute_list)

            else:
                await client.send_message(message.channel, trans.get("MSG_MUTE_NONE", lang))

        # !mute
        elif startswith(prefix + "mute"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "mute "):]
            user = await self.resolve_user(name, message, lang)

            if message.server.owner.id == user.id:
                await client.send_message(message.channel, trans.get("MSG_MUTE_OWNER", lang))
                return

            if message.author.id == user.id:
                await client.send_message(message.channel, trans.get("MSG_MUTE_SELF", lang))
                return

            handler.mute(message.server, user.id)
            await client.send_message(message.channel, trans.get("MSG_MUTE_SUCCESS", lang).format(user.name))

        # !unmute
        elif startswith(prefix + "unmute"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_MOD", lang))
                return "return"

            name = message.content[len(prefix + "unmute "):]

            # In case an admin wishes to unmute everyone
            if name == trans.get("INFO_ALL", lang):
                conf = trans.get("INFO_CONFIRM", lang)

                await client.send_message(message.channel, trans.get("MSG_UNMUTE_ALL_CONFIRM", lang).format(conf))
                followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                         timeout=15, content=conf)

                if followup is None:
                    await client.send_message(message.channel, trans.get("MSG_UNMUTE_TIMEOUT", lang))
                    return

                mutes = handler.get_mute_list(message.server)
                for user_id in mutes:
                    handler.unmute(user_id, message.server.id)

                await client.send_message(message.channel, trans.get("MSG_UNMUTE_MASS_DONE", lang))
                return

            # Normal unmuting
            user = await self.resolve_user(name, message, lang)
            handler.unmute(user.id, message.server.id)

            await client.send_message(message.channel,trans.get("MSG_UNMUTE_SUCCESS", lang).format(user.name))

        # END of mod commands

        ################################
        # PERMISSION CHECK (only admins)
        ################################
        if not handler.can_use_admin_commands(message.author, message.server):
            await client.send_message(message.channel, trans.get("PERM_ADMIN", lang))
            return

        # Users from here forth must be admins

        # !joinmsg
        if startswith(prefix + "joinmsg"):
            change = message.content[len(prefix + "joinmsg "):]

            if is_disabled(change):
                handler.update_var(message.server.id, "welcomemsg", None)
                await client.send_message(message.channel, trans.get("MSG_JOIN_DISABLED", lang))

            else:
                handler.update_var(message.server.id, "welcomemsg", change)
                await client.send_message(message.channel, trans.get("MSG_JOIN", lang))

        # !welcomemsg
        elif startswith(prefix + "welcomemsg"):
            change = message.content[len(prefix + "welcomemsg "):]

            if not change:
                await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            if is_disabled(change):
                handler.update_var(message.server.id, "welcomemsg", None)
                await client.send_message(message.channel, trans.get("MSG_JOIN_DISABLED", lang))

            else:
                handler.update_var(message.server.id, "welcomemsg", change)
                await client.send_message(message.channel, trans.get("MSG_JOIN", lang))

        # !banmsg
        elif startswith(prefix + "banmsg"):
            change = message.content[len(prefix + "banmsg "):]

            if not change:
                await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            if is_disabled(change):
                handler.update_var(message.server.id, "banmsg", None)
                await client.send_message(message.channel, trans.get("MSG_BAN_DISABLED", lang))

            else:
                handler.update_var(message.server.id, "banmsg", change)
                await client.send_message(message.channel, trans.get("MSG_BAN", lang))

        # !kickmsg
        elif startswith(prefix + "kickmsg"):
            change = message.content[len(prefix + "kickmsg "):]

            if not change:
                await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            if is_disabled(change):
                handler.update_var(message.server.id, "kickmsg", None)
                await client.send_message(message.channel, trans.get("MSG_KICK_DISABLED", lang))

            else:
                handler.update_var(message.server.id, "kickmsg", change)
                await client.send_message(message.channel, trans.get("MSG_KICK", lang))

        # !leavemsg
        elif startswith(prefix + "leavemsg"):
            change = message.content[len(prefix + "leavemsg "):]

            if not change:
                await client.send_message(message.channel, trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            if is_disabled(change):
                handler.update_var(message.server.id, "leavemsg", None)
                await client.send_message(message.channel, trans.get("MSG_LEAVE_DISABLED", lang))

            else:
                handler.update_var(message.server.id, "leavemsg", change)
                await client.send_message(message.channel, trans.get("MSG_LEAVE", lang))

        # !user
        elif startswith(prefix + "user"):
            # Selects the proper user
            if len(message.mentions) == 0:
                name = message.content[len(prefix + "user "):]
                member = utils.find(lambda u: u.name == name, message.server.members)

            else:
                member = message.mentions[0]

            # If the member does not exist
            if not member:
                await client.send_message(message.channel, trans.get("ERROR_NO_USER", lang))
                return

            # Gets info
            name = member.name
            mid = member.id
            bot = ":robot:" if member.bot else ":cowboy:"

            # Just removes the @ in @everyone
            role = str(member.top_role).rstrip("@")

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
            embed.set_author(name="{} #{}".format(name, member.discriminator), icon_url=member.avatar_url)

            embed.add_field(name=trans.get("MSG_USERINFO_STATUS", lang), value=status)
            embed.add_field(name=trans.get("MSG_USERINFO_MENTION", lang), value=member.mention)
            embed.add_field(name=trans.get("MSG_USERINFO_ID", lang), value=mid)
            embed.add_field(name=trans.get("MSG_USERINFO_TYPE", lang), value=bot)
            embed.add_field(name=trans.get("MSG_USERINFO_TOPROLE", lang), value=role)
            embed.add_field(name=trans.get("MSG_USERINFO_CREATION", lang), value=account_created)

            embed.set_image(url=member.avatar_url)

            embed.set_footer(text=trans.get("MSG_USERINFO_DATEGOT", lang).format(
                datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %B %Y")))

            await client.send_message(message.channel, trans.get("MSG_USERINFO_USER", lang), embed=embed)

        # !role
        elif startswith(prefix + "role"):
            # This selects the proper user
            if len(message.mentions) == 0:
                await client.send_message(message.channel, trans.get("ERROR_NO_MENTION", lang))
                return

            elif len(message.mentions) > 2:
                await client.send_message(message.channel, trans.get("ERROR_MENTION_ONE", lang))
                return

            else:
                user = message.mentions[0]

            # Checks if the user is permitted to change this role (can only change roles lower in the hierarchy)
            def is_lower(user_role, selected_role):
                return user_role.position >= selected_role.position

            # Combines both
            def can_change_role(member_a, selected_role):
                return is_lower(member_a.top_role, selected_role)

            # Branching

            if startswith(prefix + "role add "):
                a_role = str(message.content[len(prefix + "role add "):]).split("<")[0].strip()

                role = await self.resolve_role(a_role, message, lang)
                # Error is already hanled by resolve_role
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, trans.get("PERM_HIERARCHY", lang))
                    return

                await client.add_roles(user, role)
                await client.send_message(message.channel, trans.get("INFO_DONE", lang) + StandardEmoji.OK)

            elif startswith(prefix + "role " + "remove "):
                a_role = str(message.content[len(prefix + "role remove "):]).split("<")[0].strip()

                role = await self.resolve_role(a_role, message, lang)
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, trans.get("PERM_HIERARCHY", lang))
                    return

                await client.remove_roles(user, role)
                await client.send_message(message.channel, trans.get("INFO_DONE", lang) + StandardEmoji.OK)

            elif startswith(prefix + "role replaceall "):
                a_role = str(message.content[len(prefix + "role replaceall "):]).split("<")[0].strip()

                role = await self.resolve_role(a_role, message, lang)
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, trans.get("PERM_HIERARCHY", lang))
                    return

                await client.replace_roles(user, role)
                await client.send_message(message.channel, trans.get("INFO_DONE", lang) + StandardEmoji.OK)

        # !cmd add
        elif startswith(prefix + "cmd add"):
            try:
                cut = str(message.content)[len(prefix + "cmd add "):].split("|")

                if len(cut) != 2:
                    await client.send_message(message.channel, trans.get("MSG_CMD_WRONG_PARAMS", lang).format(prefix))
                    return

                if len(handler.get_custom_commands(message.server)) >= CMD_LIMIT:
                    await client.send_message(message.channel, trans.get("MSG_CMD_LIMIT_EXCEEDED", lang).format(CMD_LIMIT))
                    return

                trigger = cut[0].strip(" ")
                resp = cut[1]

                if len(trigger) >= CMD_LIMIT_T:
                    await client.send_message(message.channel, trans.get("MSG_CMD_NAME_TOO_LONG", lang).format(CMD_LIMIT_T, len(trigger)))
                    return
                elif len(resp) >= CMD_LIMIT_A:
                    await client.send_message(message.channel, trans.get("MSG_CMD_RESPONSE_TOO_LONG", lang).format(CMD_LIMIT_A, len(resp)))
                    return

                handler.set_command(message.server, trigger, resp)

                await client.send_message(message.channel, trans.get("MSG_CMD_ADDED", lang).format(cut[0].strip(" ")))

            except (KeyError or IndexError):
                await client.send_message(message.channel, trans.get("MSG_CMD_SEPARATE", lang))

        # !cmd remove
        elif startswith(prefix + "cmd remove"):
            cut = str(message.content)[len(prefix + "cmd remove "):]
            success = handler.remove_command(message.server, cut)

            final = trans.get("INFO_OK", lang) + StandardEmoji.OK if success else trans.get("MSG_CMD_REMOVE_FAIL", lang)

            await client.send_message(message.channel, final)

        # !cmd list
        elif startswith(prefix + "cmd list"):
            page = str(message.content)[len(prefix + "cmd list"):].strip(" ")

            try:
                page = int(page) - 1
                if page < 0: page = 0
            except ValueError:
                page = 0

            custom_cmds = handler.get_custom_commands(message.server)

            if not custom_cmds:
                await client.send_message(message.channel, trans.get("MSG_CMD_NO_CUSTOM", lang).format(prefix))
                return

            cmd_list, c_page = make_pages_from_dict(custom_cmds)
            final = trans.get("MSG_CMD_LIST", lang).format(page + 1, c_page + 1, "\n".join(cmd_list[page]))

            try:
                msg_list = await client.send_message(message.channel, final)
                await self.cmd.new_message(msg_list, page, cmd_list)
            except HTTPException:
                await client.send_message(message.channel, trans.get("MSG_CMD_LIST_TOO_LONG", lang))
                raise

        # !cmd status
        elif startswith(prefix + "cmd status"):
            cc = handler.get_custom_commands(message.server)
            percent = int((len(cc) / CMD_LIMIT) * 100)

            await client.send_message(message.channel, trans.get("MSG_CMD_STATUS", lang).format(len(cc), CMD_LIMIT, percent))

        elif startswith(prefix + "language"):
            cut = str(message.content)[len(prefix + "language "):].strip(" ")

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

                await client.send_message(message.channel, trans.get("MSG_LANG_LIST", lang).format("\n".join(lang_list)))

            elif cut.startswith("set"):
                to_set = cut[len("set "):].strip(" ").lower()

                if not self.trans.is_language_code(to_set):
                    # Try to find the language by name
                    to_set = self.trans.find_language_code(to_set)
                    if not to_set:
                        await client.send_message(message.channel, trans.get("MSG_LANG_NOT_AVAILABLE", lang))
                        return

                self.handler.set_lang(message.server.id, to_set)

                msg = trans.get("MSG_LANG_SET", lang).format(to_set, trans.get("INFO_HELLO", to_set))
                await client.send_message(message.channel, msg)

            else:
                resp = trans.get("MSG_LANG_CURRENT", lang).format(lang, self.trans.meta.get(lang).get("name"), prefix)
                await client.send_message(message.channel, resp)

        # nano.settings
        elif startswith("nano.settings"):
            try:
                cut = str(message.content)[len("nano.settings "):].split(" ", 1)
            except IndexError:
                return

            if len(cut) != 2:
                await client.send_message(message.channel, trans.get("MSG_SETTINGS_WRONG_USAGE", lang).format(prefix))
                return

            user_set = cut[0]

            # Set logchannel
            if matches_list(user_set, "logchannel"):
                chan_id = cut[1].replace("<#", "").replace(">", "")

                # When the channel is disabled
                if is_disabled(chan_id):
                    await client.send_message(message.channel, trans.get("MSG_SETTINGS_LOGCHANNEL_DISABLED", lang))
                    handler.update_var(message.server.id, "logchannel", None)
                    return

                chan = utils.find(lambda chann: chann.id == chan_id, message.server.channels)
                if not chan:
                    await client.send_message(message.channel, trans.get("ERROR_NOT_CHANNEL", lang))
                    return

                if chan.type == chan.type.voice:
                    await client.send_message(message.channel, trans.get("MSG_SETTINGS_NOT_TEXT", lang))
                    return

                # At this point, the channel should be valid
                handler.update_var(message.server.id, "logchannel", chan_id)
                await client.send_message(message.channel, trans.get("MSG_SETTINGS_LOGCHANNEL_SET", lang).format(chan.name))

            # Set allowed selfrole role
            elif matches_list(user_set, "selfrole"):
                if len(message.role_mentions) != 0:
                    selfrole_name = message.role_mentions[0].name
                    raw_role = message.role_mentions[0]
                else:
                    selfrole_name = str(cut[1])
                    raw_role = utils.find(lambda r: r.name == selfrole_name, message.server.roles)

                # If user wants to disable the role with None, Disabled, etc.., ignore existence checks
                if is_disabled(selfrole_name):
                    self.handler.set_selfrole(message.server.id, None)
                    await client.send_message(message.channel, trans.get("MSG_SETTINGS_SELFROLE_DISABLED", lang))
                    return

                if not raw_role:
                    await client.send_message(message.channel, trans.get("ERROR_INVALID_ROLE_NAME", lang))
                    return

                # Checks role position
                nano_user = utils.find(lambda me: me.id == client.user.id, message.server.members)
                if not nano_user:
                    log_to_file("SELFROLE: Nano Member is NONE", "bug")
                    return

                try:
                    await client.add_roles(nano_user, raw_role)
                    await client.remove_roles(nano_user, raw_role)
                except derrors.Forbidden:
                    await client.send_message(message.channel, StandardEmoji.WARNING + trans.get("MSG_SETTINGS_SELFROLE_INACCESSIBLE", lang).format(raw_role.name))
                    return

                self.handler.set_selfrole(message.server.id, selfrole_name)
                await client.send_message(message.channel, trans.get("MSG_SETTINGS_SELFROLE_SET", lang).format(selfrole_name))

            elif matches_list(user_set, "defaultchannel"):
                # TODO clean up
                if len(message.channel_mentions) != 1:
                    chan = str(message.content[len("nano.settings defaultchannel "):])

                    if not chan or not is_disabled(chan):
                        await client.send_message(message.channel, trans.get("ERROR_NO_CHMENTION", lang))
                        return
                    else:
                        # This case runs only, if is_disabled returns True
                        chan_id = None

                else:
                    chan = message.channel_mentions[0]
                    chan_id = chan.id

                self.handler.set_defaultchannel(message.server, chan_id)

                if chan_id:
                    await client.send_message(message.channel, trans.get("MSG_SETTINGS_DEFCHAN_SET", lang).format(chan.name))
                else:
                    await client.send_message(message.channel, trans.get("MSG_SETTINGS_DEFCHAN_RESET", lang).format(message.server.default_channel.name))

            # Otherwise, set word/spam/invite filter
            elif matches_list(user_set, "word filter", "wordfilter"):
                decision = matches_list(cut[1])
                handler.update_moderation_settings(message.server, cut[0], decision)

                await client.send_message(message.channel, trans.get("MSG_SETTINGS_WORD", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            elif matches_list(user_set, "spam filter", "spamfilter"):
                decision = matches_list(cut[1])
                handler.update_moderation_settings(message.server, cut[0], decision)

                await client.send_message(message.channel, trans.get("MSG_SETTINGS_SPAM", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            elif matches_list(user_set, "filterinvite", "filterinvites", "invitefilter"):
                decision = matches_list(cut[1])
                handler.update_moderation_settings(message.server, cut[0], decision)

                await client.send_message(message.channel, trans.get("MSG_SETTINGS_INVITE", lang).format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            else:
                await client.send_message(message.channel, trans.get("MSG_SETTINGS_NOT_A_SETTING", lang).format(user_set))

        # nano.displaysettings
        elif startswith("nano.displaysettings"):
            settings = handler.get_server_data(message.server)

            blacklisted_c = settings.get("blacklist")
            if not blacklisted_c:
                blacklisted_c = trans.get("MSG_SETTINGS_NO_BLACKLIST", lang)

            else:
                blacklisted = []
                for ch_id in blacklisted_c:
                    channel_r = utils.find(lambda c: c.id == ch_id, message.server.channels)

                    if not channel_r:
                        self.handler.remove_channel_blacklist(message.server, ch_id)
                        continue

                    blacklisted.append(channel_r.name)

                blacklisted_c = ",".join(blacklisted)


            ON = trans.get("INFO_ON", lang)
            OFF = trans.get("INFO_OFF", lang)
            DISABLED = trans.get("INFO_DISABLED", lang)

            spam_filter = ON if settings.get(SPAMFILTER_SETTING) else OFF
            word_filter = ON if settings.get(WORDFILTER_SETTING) else OFF
            invite_filter = ON if settings.get(INVITEFILTER_SETTING) else OFF

            log_channel = settings.get("logchannel") or DISABLED
            selfrole = settings.get("selfrole") or DISABLED

            log_channel_name = utils.find(lambda a: a.id == log_channel, message.server.channels)
            log_channel_name = "({})".format(log_channel_name) if log_channel_name else ""

            d_channel = await self.handle_def_channel(message.server, settings.get("dchan"))
            if is_disabled(d_channel):
                d_channel = DISABLED
            else:
                d_channel = "{} ({})".format(d_channel.id, d_channel.name)

            msg_join = settings.get("welcomemsg") or DISABLED
            msg_leave = settings.get("leavemsg") or DISABLED
            msg_ban = settings.get("banmsg") or DISABLED
            msg_kick = settings.get("kickmsg") or DISABLED

            final = trans.get("MSG_SETTINGS_DISPLAY", lang).format(blacklisted_c, spam_filter, word_filter, invite_filter,
                                                                   log_channel, log_channel_name, d_channel, settings.get("prefix"), selfrole,
                                                                   msg_join, msg_leave, msg_ban, msg_kick)

            await client.send_message(message.channel, final)

        # IMPORTANT!
        # ADMIN ADDING HAS BEEN COMPLETELY REMOVED in 3.4!

        elif startswith("nano.blacklist"):
            if startswith("nano.blacklist add"):
                name = str(message.content[len("nano.blacklist add "):])

                if name.startswith("<#"):
                    ch_id = name.replace("<#", "").replace(">", "")
                    if not ch_id.isnumeric():
                        await client.send_message(message.channel, trans.get("ERROR_MISSING_CHANNEL", lang))
                        self.stats.add(WRONG_ARG)
                        return

                    channel = utils.find(lambda ch: ch.id == ch_id, message.server.channels)

                else:
                    channel = utils.find(lambda ch: ch.name == name, message.server.channels)

                if not channel:
                    await client.send_message(message.channel, trans.get("ERROR_MISSING_CHANNEL", lang))
                    self.stats.add(WRONG_ARG)
                    return

                self.handler.add_channel_blacklist(message.server, channel.id)

                await client.send_message(message.channel, trans.get("MSG_BLACKLIST_ADDED", lang).format(channel.id))

            elif startswith("nano.blacklist remove"):
                name = str(message.content[len("nano.blacklist remove "):])

                if name.startswith("<#"):
                    ch_id = name.replace("<#", "").replace(">", "")
                    if not ch_id.isnumeric():
                        await client.send_message(message.channel, trans.get("ERROR_MISSING_CHANNEL", lang))
                        self.stats.add(WRONG_ARG)
                        return

                    channel = utils.find(lambda chan: chan.id == ch_id, message.server.channels)

                else:
                    channel = utils.find(lambda chan: chan.name == name, message.server.channels)

                if not channel:
                    await client.send_message(message.channel, trans.get("ERROR_MISSING_CHANNEL", lang))
                    self.stats.add(WRONG_ARG)
                    return

                res = self.handler.remove_channel_blacklist(message.server, channel.id)

                if res:
                    await client.send_message(message.channel, trans.get("MSG_BLACKLIST_REMOVED", lang).format(channel.name))
                else:
                    await client.send_message(message.channel, trans.get("MSG_BLACKLIST_REMOVE_FAIL", lang))

            elif startswith("nano.blacklist list"):
                lst = self.handler.get_blacklist(message.server)

                names = []
                for ch in lst:
                    channel = utils.find(lambda c: c.id == ch, message.server.channels)
                    if not channel:
                        self.handler.remove_channel_blacklist(message.server, ch)
                    else:
                        names.append("`{}`".format(channel.name))

                if names:
                    await client.send_message(message.channel, trans.get("MSG_BLACKLIST_LIST", lang).format(" ".join(names)))
                else:
                    await client.send_message(message.channel, trans.get("MSG_BLACKLIST_NONE", lang))

        # nano.reset
        elif startswith("nano.serverreset"):
            CONF = trans.get("INFO_CONFIRM", lang)
            await client.send_message(message.channel, trans.get("MSG_RESET_CONFIRM", lang).format(CONF))

            followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                     timeout=15, content=CONF)

            if followup is None:
                await client.send_message(message.channel, trans.get("MSG_RESET_CONFIRM_TIMEOUT", lang))

            handler.server_setup(message.server)

            await client.send_message(message.channel, trans.get("MSG_RESET_DONE", lang))

        # nano.changeprefix
        elif startswith("nano.changeprefix"):
            pref = message.content[len("nano.changeprefix "):]

            if len(pref) > 25:
                await client.send_message(message.channel, trans.get("ERROR_PREFIX_TOO_LONG", lang))
                return

            self.handler.change_prefix(message.server, pref)

            await client.send_message(message.channel, trans.get("MSG_PREFIX_CHANGED", lang).format(pref))

        # !setup, nano.setup
        elif startswith(prefix + "setup", "nano.setup"):
            auth = message.author
            MSG_TIMEOUT = 35

            YES = trans.get("INFO_YES", lang)
            NO = trans.get("INFO_NO", lang)
            NONE = trans.get("INFO_NONE", lang)

            async def timeout(msg):
                await client.send_message(msg.channel, trans.get("MSG_SETUP_TIMEOUT", lang))

            msg_intro = trans.get("MSG_SETUP_WELCOME", lang)
            await client.send_message(message.channel, msg_intro)
            await asyncio.sleep(2)

            # FIRST MESSAGE
            # Q: Do you want to reset all current settings?
            msg_one = trans.get("MSG_SETUP_RESET", lang).format(YES, NO)
            await client.send_message(message.channel, msg_one)

            # First check

            def check_yes1(msg):
                # yes or no
                if str(msg.content).lower().strip(" ") == YES:
                    handler.server_setup(message.server)

                return True

            ch1 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes1)
            if ch1 is None:
                await timeout(message)
                return

            # SECOND MESSAGE
            # Q: What prefix do you want?
            msg_two = trans.get("MSG_SETUP_PREFIX", lang)
            await client.send_message(message.channel, msg_two)

            # Second check, does not need yes/no filter
            ch2 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch2 is None:
                await timeout(message)
                return

            if ch2.content:
                if len(ch2.content) > 50:
                    await client.send_message(message.channel, trans.get("ERROR_PREFIX_TOO_LONG", lang))
                    return

                handler.change_prefix(message.server, str(ch2.content).strip(" "))

            # THIRD MESSAGE
            # Q: What message would you like to see when a person joins your server?
            msg_three = trans.get("MSG_SETUP_JOINMSG", lang)
            await client.send_message(message.channel, msg_three)

            ch3 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch3 is None:
                await timeout(message)
                return

            if is_disabled(ch3.content.strip(" ").lower()):
                handler.update_var(message.server.id, "welcomemsg", None)
            else:
                handler.update_var(message.server.id, "welcomemsg", str(ch3.content))

            # FOURTH MESSAGE
            msg_four = trans.get("MSG_SETUP_SPAM", lang).format(YES, NO)
            await client.send_message(message.channel, msg_four)

            # Fourth check

            def check_yes3(msg):
                # yes or no

                if str(msg.content).lower().strip(" ") == YES:
                    handler.update_moderation_settings(message.server, "filterspam", True)
                else:
                    handler.update_moderation_settings(message.server, "filterspam", False)

                return True

            ch4 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes3)
            if ch4 is None:
                await timeout(message)
                return

            # FIFTH MESSAGE
            msg_five = trans.get("MSG_SETUP_SWEARING", lang).format(YES, NO)
            await client.send_message(message.channel, msg_five)

            # Fifth check check

            def check_yes4(msg):
                # yes or no

                if str(msg.content).lower().strip(" ") == YES:
                    handler.update_moderation_settings(message.server, "filterwords", True)
                else:
                    handler.update_moderation_settings(message.server, "filterwords", False)

                return True

            ch5 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes4)
            if ch5 is None:
                await timeout(message)
                return

            # LAST MESSAGE
            msg_six = trans.get("MSG_SETUP_LOGCHANNEL", lang).format(NONE)
            await client.send_message(message.channel, msg_six)

            ch6 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch6 is None:
                await timeout(message)
                return

            else:
                # Parses channel
                channel = str(ch6.content)

                if channel.lower() == NONE or is_disabled(channel.lower()):
                    handler.update_var(message.server.id, "logchannel", None)
                    await client.send_message(message.channel, trans.get("MSG_SETUP_LOGCHANNEL_DISABLED", lang))

                else:
                    if channel.startswith("<#"):
                        channel = channel.replace("<#", "").replace(">", "")

                    handler.update_var(message.server.id, "logchannel", channel)
                    await client.send_message(message.channel, trans.get("MSG_SETUP_LOGCHANNEL_SET", lang).format(channel))

            msg_final = trans.get("MSG_SETUP_COMPLETE", lang).replace("_", str(ch2.content))

            await client.send_message(message.channel, msg_final)

    async def on_member_remove(self, member, **_):
        # check for softban
        if self.timer.get_ban(member.id):
            return "return"

        # check for normal ban
        elif member.id in self.bans:
            self.bans.remove(member.id)
            return "return"

    async def on_reaction_add(self, reaction, user, **kwargs):
        await self.cmd.handle_reaction(reaction, user, **kwargs)
        await self.mute.handle_reaction(reaction, user, **kwargs)

class NanoPlugin:
    name = "Admin Commands"
    version = "0.3.4"

    handler = Admin
    events = {
        "on_message": 10,
        "on_member_remove": 4,
        "on_reaction_add": 10,
        # type : importance
    }
