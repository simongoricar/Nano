# coding=utf-8
import asyncio
import logging
import time
import datetime
from discord import Message, utils, Client, Embed, Colour, DiscordException, HTTPException, Object, errors as derrors
from data.serverhandler import LegacyServerHandler, RedisServerHandler, INVITEFILTER_SETTING, SPAMFILTER_SETTING, WORDFILTER_SETTING
from data.stats import WRONG_ARG
from data.utils import convert_to_seconds, get_decision, is_valid_command, StandardEmoji, decode, resolve_time, log_to_file, is_disabled

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS

error_hierarchy = StandardEmoji.WARNING + " You are not allowed to mess with this role (you are lower in the \"hierarchy\"). ¯\_(ツ)_/¯"
CHANNEL_NOT_FOUND = "Channel could not be found."

not_admin = " You do not have the correct permissions to use this command (must be an admin)."
not_mod = " You do not have the correct permissions to use this command (must be a mod)."

CMD_LIMIT = 40
TICK_DURATION = 15

PREFIX_TOO_LONG = StandardEmoji.WARNING + " Prefix is too long! Maximum length is 100 characters."

commands = {
    "_ban": {"desc": "Bans a member.", "use": "[command] [mention]", "alias": "nano.ban"},
    "nano.ban": {"desc": "Bans a member.", "use": "User: [command] [mention]", "alias": "_ban"},
    "_kick": {"desc": "Kicks a member.", "use": "[command] [mention]", "alias": "nano.kick"},
    "nano.kick": {"desc": "Kicks a member", "use": "[command] [mention]", "alias": "_kick"},
    "_unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "nano.unban"},
    "nano.unban": {"desc": "Unbans a member.", "use": "[command] [mention]", "alias": "_unban"},
    "_softban": {"desc": "Temporarily bans a member (for time formatting see reminders)", "use": "[command] [time]|@mention", "alias": None},
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

    "nano.settings": {"desc": "Sets server settings like word, spam, invite filtering, log channel and selfrole.\nPossible setting keyords: wordfilter, spamfilter, invitefilter, logchannel, selfrole", "use": "[command] [setting] True/False", "alias": None},
    "nano.displaysettings": {"desc": "Displays all server settings.", "use": None, "alias": None},
    "nano.changeprefix": {"desc": "Changes the prefix on the server.", "use": "[command] prefix", "alias": None},
    "nano.serverreset": {"desc": "Resets all server settings to the default.", "use": None, "alias": None},

    "_role add": {"desc": "Adds a role to the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role remove": {"desc": "Removes a role from the user.", "use": "[command] [role name] [mention]", "alias": None},
    "_role replaceall": {"desc": "Replace all roles with the specified one for a user.", "use": "[command] [role name] [mention]", "alias": None},
}


class LegacySoftBanScheduler:
    def __init__(self, client, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop

        self.bans = {}

        self.wait = False

    def lock(self):
        self.wait = True

    def release(self):
        self.wait = False

    async def wait(self):
        while self.wait:
            await asyncio.sleep(0.01)

    def get_ban(self, user):
        return self.bans.get(user.id)

    def remove_ban(self, user):
        self.loop.create_task(self.dispatch(self.bans.get(user.id)))
        self.bans.pop(user.id, None)

    def set_softban(self, server, user, tim):
        t = time.time()

        tim = convert_to_seconds(tim)

        if not (5 < tim < 172800):  # 5 sec to 2 days
            return False

        # Add the reminder to the list
        self.bans[user.id] = {"member": user, "server": server, "time_target": int(t + tim)}

        return True

    @staticmethod
    async def tick(last_time):
        """
        Very simple implementation of a self-correcting tick system
        :return: None
        """
        current_time = time.time()
        delta = 1 - (current_time - last_time)

        await asyncio.sleep(delta)

        return time.time()

    async def dispatch(self, reminder):
        try:
            logger.debug("Dispatching")
            await self.client.unban(reminder.get("server"), reminder.get("member"))
        except DiscordException:
            pass

    async def start_monitoring(self):
        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for ban in list(self.bans.values()):

                # If enough time has passed, send the reminder
                if ban.get("time_target") <= last_time:

                    await self.dispatch(ban)

                    try:
                        self.bans[ban.get("author")].remove(ban)
                    except KeyError:
                        pass

            # And tick.
            last_time = await self.tick(last_time)


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

        if not (5 <= tim < 172800):  # 5 sec to 2 days
            return False

        # Add the reminder to the list
        payload = {"member": user.id, "server": server.id, "time_target": int(t + tim)}

        return self.redis.hmset(user.id, payload)

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
                # If enough time has passed, send the reminder
                if int(ban.get("time_target", 0)) <= last_time:
                    await self.dispatch(ban)
                    self.redis.delete(ban.get("member"))

            # And tick.
            last_time = await self.tick(last_time)


class Admin:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.legacy = kwargs.get("legacy")

        if self.legacy:
            self.timer = LegacySoftBanScheduler(self.client, self.loop)
        else:
            self.timer = RedisSoftBanScheduler(self.client, self.handler, self.loop)

        self.loop.create_task(self.timer.start_monitoring())

        self.bans = []

    async def resolve_role(self, name, message):
        role = utils.find(lambda r: r.name == name, message.channel.server.roles)

        if not role:
            # Try role mentions
            if len(message.role_mentions) != 0:
                role = message.role_mentions[0]
            else:
                await self.client.send_message(message.channel, StandardEmoji.WARNING + " Role does not exist!")
                return None

        return role

    async def on_message(self, message, **kwargs):
        prefix = kwargs.get("prefix")
        client = self.client
        handler = self.handler

        assert isinstance(message, Message)
        assert isinstance(handler, (LegacyServerHandler, RedisServerHandler))
        assert isinstance(client, Client)

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix=prefix):
            return

        def startswith(*msg):
            for om in msg:
                if message.content.startswith(om):
                    return True

            return False

        # !nuke
        if startswith(prefix + "nuke"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            amount = str(message.content)[len(prefix + "nuke "):]

            try:
                amount = int(amount) + 1  # Includes the sender's message
            except ValueError:
                await client.send_message(message.channel, "Must be a number.")
                return

            await client.delete_message(message)
            await client.send_message(message.channel, "Purging last {} messages... :boom:".format(amount - 1))

            additional = ""

            try:
                await client.purge_from(message.channel, limit=amount)
            except derrors.HTTPException:
                additional = "(some mesages were older than 2 weeks, so they were not deleted)"

            # Show success
            m = await client.send_message(message.channel, "Purged {} messages {} {}".format(StandardEmoji.OK, amount - 1, additional))
            # Wait 1.5 sec and delete the message
            await asyncio.sleep(1.5)
            await client.delete_message(m)

        # !kick
        elif startswith(prefix + "kick") and not startswith(prefix + "kickmsg"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:
                user_name = str(str(message.content)[len(prefix + "kick "):])

                user = utils.find(lambda u: u.name == str(user_name), message.channel.server.members)

            if not user:
                await client.send_message(message.channel, StandardEmoji.WARNING + " User does not exist.")
                return

            if user.id == client.user.id:
                await client.send_message(message.channel, "Nice try " + StandardEmoji.SMILEY)

            await client.kick(user)
            await client.send_message(message.channel,
                                      handler.get_var(message.channel.server.id, "kickmsg").replace(":user", user.name))

        # !ban
        elif startswith(prefix + "ban") and not startswith(prefix + "banmsg"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:
                user_name = str(str(message.content)[len(prefix + "ban "):])

                user = utils.find(lambda u: u.name == str(user_name), message.channel.server.members)

            if not user:
                await client.send_message(message.channel, StandardEmoji.WARNING + " User does not exist.")
                return

            await client.send_message(message.channel,
                                      "Are you sure you want to ban " + user.name + "? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                     timeout=15, content="CONFIRM")

            if followup is None:
                await client.send_message(message.channel, "Confirmation not received, NOT banning :upside_down:")

            else:
                self.bans.append(user.id)

                await client.ban(user, delete_message_days=0)

        # !unban
        elif startswith(prefix + "unban"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            name = message.content[len(prefix + "unban "):]

            user = None
            for ban in await self.client.get_bans(message.server):
                if ban.name == name:
                    user = ban

            if not user:
                await client.send_message(message.channel, StandardEmoji.WARNING + " User does not exist.")
                return

            await client.unban(message.server, user)
            await client.send_message(message.channel, "**{}** has been unbanned.".format(user.name))

        # !softban [time]|@mention
        elif startswith(prefix + "softban"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            if len(message.mentions) != 1:
                await client.send_message(message.channel, "Please mention the member you want to softban. (only one)")
                return

            user = message.mentions[0]
            tim = str(message.content[len(prefix + "softban "):])

            if tim.find("|") != -1:
                tim = tim[:tim.find("|")].strip(" ")
            else:
                await client.send_message(message.channel, "Please delimit time and @mention with |")
                return

            parsed_time = convert_to_seconds(tim)

            self.timer.set_softban(message.channel.server, user, parsed_time)
            await client.ban(user, delete_message_days=0)

            await client.send_message(message.channel, "{} has been softbanned for: {}".format(user.name, resolve_time(parsed_time)))

        # !mute list
        elif startswith(prefix + "mute list"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            mutes = handler.get_mute_list(message.server)

            if mutes:
                muted_ppl = []
                for a in mutes:
                    usr = utils.find(lambda b: b.id == a, message.server.members)
                    if usr:
                        muted_ppl.append(usr.name)

                final = "Muted members: \n" + "\n".join(["➤ {}".format(u) for u in muted_ppl])

            else:
                final = "No members are muted on this server."

            await client.send_message(message.channel, final)

        # !mute
        elif startswith(prefix + "mute"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to mute.")
                return

            user = message.mentions[0]

            if message.server.owner.id == user.id:
                await client.send_message(message.channel, StandardEmoji.WARNING + " You cannot mute the owner of the server.")
                return

            elif message.author.id == user.id:
                await client.send_message(message.channel, "Trying to mute yourself? Not gonna work " + StandardEmoji.ROFL)

            handler.mute(message.server, user.id)

            await client.send_message(message.channel,
                                      "**{}** can now not speak here. {}".format(user.name, StandardEmoji.ZIP_MOUTH))

        # !unmute
        elif startswith(prefix + "unmute"):
            if not handler.is_mod(message.author, message.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_mod)
                return "return"

            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to unmute.")
                return

            user = message.mentions[0]

            handler.unmute(user)

            await client.send_message(message.channel, "**{}** can now speak here again {}".format(user.name, StandardEmoji.ROFL))

        else:
            if not handler.can_use_restricted_commands(message.author, message.channel.server):
                await client.send_message(message.channel, StandardEmoji.WARNING + not_admin)
                return

        # !joinmsg
        if startswith(prefix + "joinmsg"):
            change = message.content[len(prefix + "joinmsg "):]
            handler.update_var(message.channel.server.id, "welcomemsg", change)

            await client.send_message(message.channel, "Join message has been updated :smile:")

        # !welcomemsg
        if startswith(prefix + "welcomemsg"):
            change = message.content[len(prefix + "welcomemsg "):]
            handler.update_var(message.channel.server.id, "welcomemsg", change)

            await client.send_message(message.channel, "Join message has been updated :smile:")

        # !banmsg
        elif startswith(prefix + "banmsg"):
            change = message.content[len(prefix + "banmsg "):]
            handler.update_var(message.channel.server.id, "banmsg", change)

            await client.send_message(message.channel, "Ban message has been updated :smile:")

        # !kickmsg
        elif startswith(prefix + "kickmsg"):
            change = message.content[len(prefix + "kickmsg "):]
            handler.update_var(message.channel.server.id, "kickmsg", change)

            await client.send_message(message.channel, "Kick message has been updated :smile:")

        # !leavemsg
        elif startswith(prefix + "leavemsg"):
            change = message.content[len(prefix + "leavemsg "):]
            handler.update_var(message.channel.server.id, "leavemsg", change)

            await client.send_message(message.channel, "Leave message has been updated :smile:")



        # !user
        elif startswith(prefix + "user"):
            # Selects the proper user
            if len(message.mentions) == 0:
                name = message.content[len(prefix + "user "):]
                member = utils.find(lambda u: u.name == name, message.channel.server.members)

            else:
                member = message.mentions[0]

            # If the member does not exist
            if not member:
                await client.send_message(message.channel, "Member does not exist.")
                return

            # Gets info
            name = member.name
            mid = member.id
            bot = ":robot:" if member.bot else ":cowboy:"

            # Just removes the @ in @everyone
            role = str(member.top_role).rstrip("@")

            account_created = str(member.created_at).rsplit(".")[0]
            status = str(member.status).capitalize()

            if status == "Online":
                color = Colour.green()
            elif status == "Idle":
                color = Colour.gold()
            elif status == "Offline":
                color = Colour.darker_grey()
            else:
                color = Colour.red()

            embed = Embed(colour=color)
            embed.set_author(name="{} #{}".format(name, member.discriminator), icon_url=member.avatar_url)

            embed.add_field(name="Status", value=status)
            embed.add_field(name="Mention", value=member.mention)
            embed.add_field(name="Id", value=mid)
            embed.add_field(name="Account Type", value=bot)
            embed.add_field(name="Top Role", value=role)
            embed.add_field(name="Account Creation Date", value=account_created)

            embed.set_image(url=member.avatar_url)

            embed.set_footer(text="Data got at {} UTC".format(
                datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %B %Y")))

            await client.send_message(message.channel, "**User info:**", embed=embed)

        # !role
        elif startswith(prefix + "role"):
            # This selects the proper user
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention someone.")
                return

            elif len(message.mentions) >= 2:
                await client.send_message(message.channel, "Please mention only one person at a time.")
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

                role = await self.resolve_role(a_role, message)
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.add_roles(user, role)
                await client.send_message(message.channel, "Done " + StandardEmoji.OK)

            elif startswith(prefix + "role " + "remove "):
                a_role = str(message.content[len(prefix + "role remove "):]).split("<")[0].strip()

                role = await self.resolve_role(a_role, message)
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.remove_roles(user, role)
                await client.send_message(message.channel, "Done " + StandardEmoji.OK)

            elif startswith(prefix + "role replaceall "):
                a_role = str(message.content[len(prefix + "role replaceall "):]).split("<")[0].strip()

                role = await self.resolve_role(a_role, message)
                if not role:
                    return

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.replace_roles(user, role)
                await client.send_message(message.channel, "Done " + StandardEmoji.OK)

        # !cmd add
        elif startswith(prefix + "cmd add"):
            try:
                cut = str(message.content)[len(prefix + "cmd add "):].split("|")

                if len(cut) != 2:
                    await client.send_message(message.channel, "Incorrect parameters.\n`_cmd add trigger|response`".replace("_", prefix))
                    return

                if len(handler.get_custom_commands(message.server)) >= CMD_LIMIT:
                    await client.send_message(message.channel, "{} You have reached the maximum limit of custom commands ({}).".format(StandardEmoji.WARNING, CMD_LIMIT))
                    return

                trigger = cut[0].strip(" ")
                resp = cut[1]

                if len(trigger) >= 80:
                    await client.send_message(message.channel, "{} Your command name is too long (max. 80, you got {})".format(StandardEmoji.WARNING, len(trigger)))
                    return
                elif len(resp) >= 500:
                    await client.send_message(message.channel, "{} Your command response is too long (max. 500, you got {})".format(StandardEmoji.WARNING, len(resp)))
                    return

                handler.set_command(message.server, trigger, resp)

                await client.send_message(message.channel, "Command '{}' added.".format(cut[0].strip(" ")))

            except (KeyError or IndexError):
                await client.send_message(message.channel,
                                          ":no_entry_sign: Wrong args, separate command and response with |")

        # !cmd remove
        elif startswith(prefix + "cmd remove"):
            cut = str(message.content)[len(prefix + "cmd remove "):]
            success = handler.remove_command(message.server, cut)

            final = "Ok " + StandardEmoji.OK if success else "Failed to remove command (does not exist) " + StandardEmoji.WARNING

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
                await client.send_message(message.channel, "No custom commands on this server. "
                                                           "Add one with `_cmd add trigger|response`!".replace("_", prefix))
                return

            buff = ["{} : {}".format(name, content) for name, content in custom_cmds.items()]
            final = [buff.pop(0)]
            while buff:
                for cmd in buff:
                    last_item = final[len(final)-1]
                    # Gets last item in list
                    if (len(last_item) + len(cmd)) > 1500:
                        final.append(cmd)
                    else:
                        final[len(final)-1] += "\n{}".format(cmd)

                    buff.remove(cmd)

            final = "Custom commands: (page **{}**/{})\n```{}```".format(page + 1, len(final), final[page])

            try:
                await client.send_message(message.channel, final)
            except HTTPException:
                await client.send_message(message.channel, "Your commands are too long to display. Consider cleaning "
                                                           "some of them or ask the bot owner to do it for you "
                                                           "if you don't remember the commands.")

        # !cmd status
        elif startswith(prefix + "cmd status"):
            cc = handler.get_custom_commands(message.server)
            percent = int((len(cc) / CMD_LIMIT) * 100)

            await client.send_message(message.channel, "You have **{}** out of *{}* custom commands (*{}%*)".format(len(cc), CMD_LIMIT, percent))

        # nano.settings
        elif startswith("nano.settings"):
            # todo optimize this
            try:
                cut = str(message.content)[len("nano.settings "):].split(" ", 1)
            except IndexError:
                return

            if len(cut) != 2:
                await client.send_message(message.channel, "Incorrect usage, see `_help nano.settings`.".format(prefix))
                return

            user_set = cut[0]

            # Set logchannel
            if get_decision(user_set, "logchannel"):
                chan_id = cut[1].replace("<#", "").replace(">", "")

                chan = utils.find(lambda chann: chann.id == chan_id, message.server.channels)

                if not chan:
                    await client.send_message(message.channel, "Not a channel.")
                    return

                if chan.type == chan.type.voice:
                    await client.send_message(message.channel, "Log channel cannot be a voice channel! Nice try :smile:")
                    return

                handler.update_var(message.server.id, "logchannel", chan_id)
                await client.send_message(message.channel, "Log channel set to **{}** {}".format(chan.name, StandardEmoji.PERFECT))

                return

            # Set allowed selfrole role
            elif get_decision(user_set, "selfrole", "self role"):
                if len(message.role_mentions) != 0:
                    selfrole_name = message.role_mentions[0].name
                    raw_role = message.role_mentions[0]
                else:
                    selfrole_name = str(cut[1])
                    raw_role = utils.find(lambda r: r.name == selfrole_name, message.server.roles)

                # If user wants to disable the role with None, Disabled, etc.., ignore existence checks
                if is_disabled(selfrole_name):
                    self.handler.set_selfrole(message.server.id, None)
                    await client.send_message(message.channel, StandardEmoji.OK + " Selfrole disabled.")
                    return

                if not raw_role:
                    await client.send_message(message.channel, StandardEmoji.WARNING + " Invalid role name!")
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
                    await client.send_message(message.channel, StandardEmoji.WARNING + " **{}** is inaccessible (could be higher than Nano's top role"
                                                                                       " or Nano does not have the permission 'Manage Roles')".format(raw_role.name))
                    return

                self.handler.set_selfrole(message.server.id, selfrole_name)
                await client.send_message(message.channel, StandardEmoji.OK + " Selfrole set to **{}**".format(selfrole_name))

                return

            # Otherwise, set word/spam/invite filter
            decision = get_decision(cut[1])

            # Does not do anything if there is no relevant setting
            handler.update_moderation_settings(message.channel.server, cut[0], decision)

            if get_decision(user_set, "word filter", "wordfilter"):
                await client.send_message(message.channel, "Word filter {}".format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            elif get_decision(user_set, "spam filter", "spamfilter"):
                await client.send_message(message.channel, "Spam filter {}".format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            elif get_decision(user_set, "filterinvite", "filterinvites", "invitefilter"):
                await client.send_message(message.channel,
                                          "Invite filter {}".format(StandardEmoji.OK if decision else StandardEmoji.GREEN_FAIL))

            else:
                await client.send_message(message.channel, "**{}** is not a setting. Should be one of: "
                                                           "logchannel, selfrole, invitefilter, wordfilter, spamfilter.".format(user_set))

        # nano.displaysettings
        elif startswith("nano.displaysettings"):
            settings = handler.get_server_data(message.server)

            blacklisted_c = settings.get("blacklist")
            if not blacklisted_c:
                blacklisted_c = "No blacklists"

            else:
                blacklisted = []
                for ch_id in blacklisted_c:
                    channel_r = utils.find(lambda c: c.id == ch_id, message.server.channels)

                    if not channel_r:
                        self.handler.remove_channel_blacklist(message.server, ch_id)
                        continue

                    blacklisted.append(channel_r.name)
                blacklisted_c = ",".join(blacklisted)

            spam_filter = "On" if settings.get(SPAMFILTER_SETTING) else "Off"
            word_filter = "On" if settings.get(WORDFILTER_SETTING) else "Off"
            invite_filter = "On" if settings.get(INVITEFILTER_SETTING) else "Off"

            log_channel = settings.get("logchannel") or "Disabled"
            selfrole = settings.get("selfrole") or "Disabled"

            channel_name = utils.find(lambda a: a.id == log_channel, message.server.channels)
            channel_name = "({})".format(channel_name) if channel_name else ""

            msg_join = settings.get("welcomemsg") or "Disabled"
            msg_leave = settings.get("leavemsg") or "Disabled"
            msg_ban = settings.get("banmsg") or "Disabled"
            msg_kick = settings.get("kickmsg") or "Disabled"

            final = """**Settings for current server:**```
Blacklisted channels: {}
Spam filter: {}
Word filter: {}
Invite removal: {}
Log channel: {} {}
Prefix: {}
Selfrole: {}```
Messages:
➤ Join: `{}`
➤ Leave: `{}`
➤ Ban: `{}`
➤ Kick: `{}`""".format(blacklisted_c, spam_filter, word_filter, invite_filter, log_channel, channel_name, settings.get("prefix"),
                       selfrole, msg_join, msg_leave, msg_ban, msg_kick)

            await client.send_message(message.channel, final)

        # IMPORTANT!
        # ADMIN ADDING HAS BEEN COMPLETELY REMOVED in 3.4!

        elif startswith("nano.blacklist"):
            if startswith("nano.blacklist add"):
                name = str(message.content[len("nano.blacklist add "):])

                if name.startswith("<#"):
                    ch_id = name.replace("<#", "").replace(">", "")
                    if not ch_id.isnumeric():
                        await client.send_message(message.channel, CHANNEL_NOT_FOUND)
                        self.stats.add(WRONG_ARG)
                        return

                    channel = utils.find(lambda ch: ch.id == ch_id, message.server.channels)

                else:
                    channel = utils.find(lambda ch: ch.name == name, message.server.channels)

                if not channel:
                    await client.send_message(message.channel, CHANNEL_NOT_FOUND)
                    self.stats.add(WRONG_ARG)
                    return

                self.handler.add_channel_blacklist(message.server, channel.id)

                await client.send_message(message.channel, "Successfully added <#{}> to the blacklist {}".format(channel.id, StandardEmoji.PERFECT))

            elif startswith("nano.blacklist remove"):
                name = str(message.content[len("nano.blacklist remove "):])

                if name.startswith("<#"):
                    ch_id = name.replace("<#", "").replace(">", "")
                    if not ch_id.isnumeric():
                        await client.send_message(message.channel, CHANNEL_NOT_FOUND)
                        self.stats.add(WRONG_ARG)
                        return

                    channel = utils.find(lambda chan: chan.id == ch_id, message.server.channels)

                else:
                    channel = utils.find(lambda chan: chan.name == name, message.server.channels)

                if not channel:
                    await client.send_message(message.channel, CHANNEL_NOT_FOUND)
                    self.stats.add(WRONG_ARG)
                    return

                res = self.handler.remove_channel_blacklist(message.server, channel.id)

                if res:
                    await client.send_message(message.channel, "Channel blacklist for {} removed {}".format(channel.name, StandardEmoji.PERFECT))
                else:
                    await client.send_message(message.channel, "Channel blacklist could not be removed. Does it even exist?")

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
                    await client.send_message(message.channel, "Blacklisted channels:\n{}".format(" ".join(names)))
                else:
                    await client.send_message(message.channel, "There are no blacklisted channels on this channel. " + StandardEmoji.NORMAL_SMILE)

        # nano.reset
        elif startswith("nano.serverreset"):
            await client.send_message(message.channel, StandardEmoji.WARNING + " Are you sure you want to reset all Nano-related sever settings to default? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                     timeout=15, content="CONFIRM")

            if followup is None:
                await client.send_message(message.channel, "Confirmation not received, NOT resetting :upside_down:")

            handler.server_setup(message.server)

            await client.send_message(message.channel, "Reset. :white_StandardEmoji.OK: ")

        # nano.changeprefix
        elif startswith("nano.changeprefix"):
            pref = message.content[len("nano.changeprefix "):]

            if len(pref) > 25:
                await client.send_message(message.channel, PREFIX_TOO_LONG)
                return

            self.handler.change_prefix(message.server, pref)

            await client.send_message(message.channel, "Prefix has been changed to {} :ok_hand:".format(pref))

        # !setup, nano.setup
        elif startswith(prefix + "setup", "nano.setup"):
            auth = message.author
            MSG_TIMEOUT = 35

            async def timeout(msg):
                await client.send_message(msg.channel,
                                          "You ran out of time :upside_down: (FYI: the timeout is 35 seconds)")

            msg_intro = "**SERVER SETUP**\nYou have started the server setup. It consists of a few steps, " \
                        "where you will be prompted to answer. Because you started the setup, only your answers will be taken into account.\n" \
                        "**Let's get started, shall we?**"
            await client.send_message(message.channel, msg_intro)
            await asyncio.sleep(2)

            # FIRST MESSAGE
            # Q: Do you want to reset all current settings?
            msg_one = "Do you want to reset all bot-related settings for this server?\n" \
                      "(this includes spam and swearing protection, admin list, blacklisted channels, \n" \
                      "log channel, prefix, welcome, ban and kick messages). **yes / no**"
            await client.send_message(message.channel, msg_one)

            # First check

            def check_yes1(msg):
                # yes or no
                if str(msg.content).lower().strip(" ") == "yes":
                    handler.server_setup(message.channel.server)

                return True

            ch1 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes1)
            if ch1 is None:
                await timeout(message)
                return

            # SECOND MESSAGE
            # Q: What prefix do you want?
            msg_two = "What prefix would you like to use for all commands?\n" \
                      "Type that prefix.\n(prefix example: **!** 'translates to' `!help`, `!ping`, ...)"
            await client.send_message(message.channel, msg_two)

            # Second check, does not need yes/no filter
            ch2 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch2 is None:
                await timeout(message)
                return

            if ch2.content:
                if len(ch2.content) > 50:
                    await client.send_message(message.channel, PREFIX_TOO_LONG)
                    return

                handler.change_prefix(message.channel.server, str(ch2.content).strip(" "))

            # THIRD MESSAGE
            # Q: What message would you like to see when a person joins your server?
            msg_three = "What would you like me to say when a person joins your server?\n" \
                        "Reply with that message or with None if you want to disable welcome messages. \n" \
                        "(:user translates to a mention of the joined user; for example -> :user, welcome to this server!)"
            await client.send_message(message.channel, msg_three)

            ch3 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch3 is None:
                await timeout(message)
                return

            if ch3.content.strip(" ").lower() == "none":
                handler.update_var(message.server.id, "welcomemsg", None)
            else:
                handler.update_var(message.server.id, "welcomemsg", str(ch3.content))

            # FOURTH MESSAGE
            msg_four = """Would you like me to filter spam? **yes / no**"""
            await client.send_message(message.channel, msg_four)

            # Fourth check

            def check_yes3(msg):
                # yes or no

                if str(msg.content).lower().strip(" ") == "yes":
                    handler.update_moderation_settings(message.channel.server, "filterspam", True)
                else:
                    handler.update_moderation_settings(message.channel.server, "filterspam", False)

                return True

            ch4 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes3)
            if ch4 is None:
                await timeout(message)
                return

            # FIFTH MESSAGE
            msg_five = """Would you like me to filter swearing? (beware of false positives)  **yes / no**"""
            await client.send_message(message.channel, msg_five)

            # Fifth check check

            def check_yes4(msg):
                # yes or no

                if str(msg.content).lower().strip(" ") == "yes":
                    handler.update_moderation_settings(message.channel.server, "filterwords", True)
                else:
                    handler.update_moderation_settings(message.channel.server, "filterwords", False)

                return True

            ch5 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth, check=check_yes4)
            if ch5 is None:
                await timeout(message)
                return

            # LAST MESSAGE
            msg_six = "What channel would you like to use for logging? channel name/None"
            await client.send_message(message.channel, msg_six)

            ch6 = await client.wait_for_message(timeout=MSG_TIMEOUT, author=auth)
            if ch6 is None:
                await timeout(message)
                return

            else:
                # Parses channel
                channel = str(ch6.content)

                if channel.lower() == "None":
                    handler.update_var(message.server.id, "logchannel", "None")
                    await client.send_message(message.channel, "Logging has been disabled.")

                else:
                    if channel.startswith("<#"):
                        channel = channel.replace("<#", "").replace(">", "")

                    handler.update_var(message.server.id, "logchannel", channel)
                    await client.send_message(message.channel, "Log channel has been set to '{}'".format(channel))

            msg_final = """**This concludes the basic server setup.**
But there are a few more settings to set up if you need'em:
➤ channel blacklisting - `nano.blacklist add/remove channel_name`
➤ join message - `_welcomemsg message`
➤ leave message - `_leavemsg message`

The prefix can simply be changed again with `nano.changeprefix prefix`.
Admin and mod commands can only be used by people with a role named "Nano Admin"/"Nano Mod".

You and all admins can also add/remove/list custom commands with `_cmd add/remove/list command|response`.
For a list of all commands and their explanations, use `_cmds`.""".replace("_", str(ch2.content))

            await client.send_message(message.channel, msg_final)

    async def on_member_remove(self, member, **_):
        # check for softban
        if self.timer.get_ban(member.id):
            return "return"

        # check for normal ban
        elif member.id in self.bans:
            self.bans.remove(member.id)
            return "return"


class NanoPlugin:
    name = "Admin Commands"
    version = "0.3.3"

    handler = Admin
    events = {
        "on_message": 10,
        "on_member_remove": 4
        # type : importance
    }
