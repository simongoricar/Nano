# coding=utf-8
import asyncio
import logging
import time
import datetime
from discord import Message, utils, Client, DiscordException, Embed, Colour
from data.serverhandler import ServerHandler
from data.utils import convert_to_seconds, get_decision, is_valid_command, StandardEmoji

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS

error_hierarchy = StandardEmoji.WARNING + " You are not allowed to mess with this role (you are lower in the \"hierarchy\"). ¯\_(ツ)_/¯"

CMD_LIMIT = 35

valid_commands = [
    "_welcomemsg", "_kickmsg", "_banmsg", "_leavemsg",
    "_nuke", "_kick", "_ban", "_unban", "_softban", "_unmute",
    "_mute", "_user", "_role add", "_role remove", "_role replaceall",
    "_cmd add", "_cmd remove", "_cmd list", "_cmd status",
    "nano.settings", "nano.displaysettings",
    "nano.admins add", "nano.admins remove", "nano.admins list", "_setup", "nano.setup",
    "nano.serverreset", "nano.changeprefix"
]


class SoftBanScheduler:
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
        self.bans.pop(user.id)

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
            for ban in self.bans.values():

                # If enough time has passed, send the reminder
                if ban.get("time_target") <= last_time:

                    await self.dispatch(ban)

                    try:
                        self.bans[ban.get("author")].remove(ban)
                    except KeyError:
                        pass

            # And tick.
            last_time = await self.tick(last_time)


class Admin:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.timer = SoftBanScheduler(self.client, self.loop)
        self.loop.create_task(self.timer.start_monitoring())

        self.bans = []

    async def on_message(self, message, **kwargs):
        prefix = kwargs.get("prefix")
        client = self.client
        handler = self.handler

        assert isinstance(message, Message)
        assert isinstance(handler, ServerHandler)
        assert isinstance(client, Client)

        # Check if this is a valid command
        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return

        def startswith(*msg):
            for om in msg:
                if message.content.startswith(om):
                    return True

            return False

        if not handler.can_use_restricted_commands(message.author, message.channel.server):
            await client.send_message(message.channel, StandardEmoji.WARNING + " You do not have the correct permissions to use this command (must be a server admin).")
            return

        # !welcomemsg
        if startswith(prefix + "welcomemsg"):
            change = message.content[len(prefix + "welcomemsg "):]
            handler.update_var(message.channel.server.id, "welcomemsg", change)

            await client.send_message(message.channel, "Welcome message has been updated :smile:")

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

        # !nuke
        elif startswith(prefix + "nuke"):
            amount = str(message.content)[len(prefix + "nuke "):]

            try:
                amount = int(amount) + 1  # Includes the sender's message
            except ValueError:
                await client.send_message(message.channel, "Must be a number.")
                return

            await client.delete_message(message)

            await client.send_message(message.channel, "Purging last {} messages... :boom:".format(amount - 1))
            await client.purge_from(message.channel, limit=amount)

            # Show success
            m = await client.send_message(message.channel, "Purged {} messages {}".format(StandardEmoji.OK, amount - 1))
            # Wait 1.5 sec and delete the message
            await asyncio.sleep(1.5)
            await client.delete_message(m)

        # !kick
        elif startswith(prefix + "kick"):
            if len(message.mentions) >= 1:
                user = message.mentions[0]

            else:
                user_name = str(str(message.content)[len(prefix + "kick "):])

                user = utils.find(lambda u: u.name == str(user_name), message.channel.server.members)

            if not user:
                return

            await client.kick(user)
            await client.send_message(message.channel,
                                      handler.get_var(message.channel.server.id, "kickmsg").replace(":user", user.name))

        # !ban
        elif startswith(prefix + "ban"):
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
            name = message.content[len(prefix + "unban "):]

            user = None
            for ban in await self.client.get_bans(message.server):
                if ban.name == name:
                    user = ban

            if not user:
                await client.send_message(message.channel, StandardEmoji.WARNING + " Could not unban: user with such name does not exist.")
                return

            await client.unban(message.server, user)
            await client.send_message(message.channel, "**{}** has been unbanned.".format(user.name))

        # !softban
        elif startswith(prefix + "softban"):

            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to softban.")
                return

            user = message.mentions[0]
            tim = message.content[len(prefix + "softban "):].replace("<@{}>".format(user.id), "").strip()

            await client.ban(user, delete_message_days=0)

            self.timer.set_softban(message.channel.server, user, tim)

            await client.send_message(message.channel, "{} has been softbanned.".format(user.name))

        # !mute list
        elif startswith(prefix + "mute list"):
            mutes = handler.mute_list(message.server)

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
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to mute.")
                return

            user = message.mentions[0]

            if message.server.owner.id == user.id:
                await client.send_message(message.channel, StandardEmoji.WARNING + " You cannot mute the owner of the server.")
                return

            elif message.author.id == user.id:
                await client.send_message(message.channel, "Trying to mute yourself? Not gonna work " + StandardEmoji.ROFL)

            handler.mute(user)

            await client.send_message(message.channel,
                                      "**{}** can now not speak here. {}".format(user.name, StandardEmoji.ZIP_MOUTH))

        # !unmute
        elif startswith(prefix + "unmute"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to unmute.")
                return

            user = message.mentions[0]

            handler.unmute(user)

            await client.send_message(message.channel, "**{}** can now speak here again {}".format(user.name, StandardEmoji.ROFL))

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

            if startswith(prefix + "role " + "add "):
                a_role = str(message.content[len(prefix + "role add "):]).split("<")[0].strip()
                role = utils.find(lambda r: r.name == a_role, message.channel.server.roles)

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.add_roles(user, role)
                await client.send_message(message.channel, "Done " + StandardEmoji.OK)

            elif startswith(prefix + "role " + "remove "):
                a_role = str(message.content[len(prefix + "role remove "):]).split("<")[0].strip()
                role = utils.find(lambda r: r.name == a_role, message.channel.server.roles)

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.remove_roles(user, role)
                await client.send_message(message.channel, "Done " + StandardEmoji.OK)

            elif startswith(prefix + "role " + "replaceall "):
                a_role = str(message.content[len(prefix + "role replaceall "):]).split("<")[0].strip()
                role = utils.find(lambda r: r.name == a_role, message.channel.server.roles)

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

                if len(handler.get_custom_commands(message.server)) + 1 >= CMD_LIMIT:
                    await client.send_message(message.channel, "{} You have reached the maximum limit of custom commands ({}).".format(StandardEmoji.WARNING, CMD_LIMIT))
                    return

                handler.update_command(message.server, cut[0].strip(" "), cut[1])

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
            custom_cmds = handler.get_custom_commands(message.server)

            if not custom_cmds:
                await client.send_message(message.channel, "No custom commands on this server. "
                                                           "Add one with `_cmd add trigger|response`!".replace("_",
                                                                                                               prefix))

                return

            final = "\n".join(["{} : {}".format(name, content) for name, content in custom_cmds.items()])

            await client.send_message(message.channel, "*Custom commands:*\n```" + final + "```")

        # !cmd status
        elif startswith(prefix + "cmd status"):
            cc = handler.get_custom_commands(message.server)
            percent = int((len(cc) / CMD_LIMIT) * 100)

            await client.send_message(message.channel, "You have **{}** out of *{}* custom commands (*{}%*)".format(len(cc), CMD_LIMIT, percent))

        # nano.settings
        elif startswith("nano.settings"):
            # todo optimize this
            try:
                cut = str(message.content)[len("nano.settings "):].rsplit(" ", 1)
            except IndexError:
                return

            if get_decision(cut[0], "logchannel", "log channel", "logging channel"):
                handler.update_var(message.server.id, "logchannel", cut[1])
                await client.send_message(message.channel,
                                          "Log channel set to {} {}".format(cut[1], ":ok_hand:"))

                return

            try:
                value = handler.update_moderation_settings(message.channel.server, cut[0], get_decision(cut[1]))
            except IndexError:
                # stat.pluswrongarg()
                return

            if get_decision(cut[0], "word filter", "filter words", "wordfilter"):
                await client.send_message(message.channel, "Word filter {}".format(StandardEmoji.OK if value else StandardEmoji.GREEN_FAIL))

            elif get_decision(cut[0], "spam filter", "spamfilter", "filter spam"):
                await client.send_message(message.channel, "Spam filter {}".format(StandardEmoji.OK if value else StandardEmoji.GREEN_FAIL))

            elif get_decision(cut[0], "filterinvite", "filterinvites", "invite removal", "invite filter", "invitefilter"):
                await client.send_message(message.channel,
                                          "Invite filter {}".format(StandardEmoji.OK if value else StandardEmoji.GREEN_FAIL))

            else:
                await client.send_message(message.channel, "Not a setting. (wordfilter/spamfilter/invitefilter)")

        # nano.displaysettings
        elif startswith("nano.displaysettings"):
            settings = handler.get_server_data(message.server.id)

            blacklisted_c = ",".join(settings.get("blacklisted"))
            if not blacklisted_c:
                blacklisted_c = "None"

            spam_filter = "On" if settings.get("filterspam") else "Off"
            word_filter = "On" if settings.get("filterwords") else "Off"
            invite_filter = "On" if settings.get("filterinvite") else "Off"

            log_channel = settings.get("logchannel") if settings.get("logchannel") else "None"

            msg_join = settings.get("welcomemsg")
            msg_leave = settings.get("leavemsg")
            msg_ban = settings.get("banmsg")
            msg_kick = settings.get("kickmsg")

            final = """**Settings for current server:**```css
Blacklisted channels: {}
Spam filter: {}
Word filter: {}
Invite removal: {}
Log channel: {}
Prefix: {}```
Messages:
➤ Join: `{}`
➤ Leave: `{}`
➤ Ban: `{}`
➤ Kick: `{}`""".format(blacklisted_c, spam_filter, word_filter, invite_filter, log_channel, settings.get("prefix"),
                       msg_join, msg_leave, msg_ban, msg_kick)

            await client.send_message(message.channel, final)

        # nano.admins add
        elif startswith("nano.admins add"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the person you want to add.")
                return

            elif len(message.mentions) == 1:
                member = message.mentions[0]

            else:
                await client.send_message(message.channel, "One at a time :)")
                return

            handler.add_admin(message.server, member)

            await client.send_message(message.channel, "Added **{}** to admins.".format(member.name))

        # nano.admins remove
        elif startswith("nano.admins remove"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the person you want to add.")
                return

            elif len(message.mentions) == 1:
                member = message.mentions[0]

            else:
                await client.send_message(message.channel, "One at a time :)")
                return

            handler.remove_admin(message.server, member)

            await client.send_message(message.channel, "Removed **{}** from admins".format(member.name))

        # nano.admins list
        elif startswith("nano.admins list"):
            admins = handler.get_admins(message.server)

            if len(admins) == 0:
                await client.send_message(message.channel, "There are no Nano admins on this server.")

            else:
                final = ""

                for usr in admins:
                    user = utils.find(lambda u: u.id == usr, message.channel.server.members)
                    final += "{}, ".format(user.name)

                # Remove last comma and space
                final = final.strip(", ")

                if len(admins) == 1:
                    await client.send_message(message.channel, "**" + final + "** is the only admin here.")
                else:
                    await client.send_message(message.channel, "**Admins:** " + final)

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

            self.handler.change_prefix(message.server, pref)

            await client.send_message(message.channel, "Prefix has been changed to {} :ok_hand:".format(pref))

        # !setup, nano.setup
        elif startswith(prefix + "setup", "nano.setup"):
            auth = message.author

            async def timeout(msg):
                await client.send_message(msg.channel,
                                          "You ran out of time :upside_down: (FYI: the timeout is 35 seconds)")

            msg_intro = "**SERVER SETUP**\nYou have started the server setup. It consists of a few steps, " \
                        "where you will be prompted to answer.\n**Let's get started, shall we?**"
            await client.send_message(message.channel, msg_intro)
            await asyncio.sleep(2)

            # FIRST MESSAGE
            msg_one = "Do you want to reset all bot-related settings for this server?\n" \
                      "(this includes spam and swearing protection, admin list, blacklisted channels, \n" \
                      "log channel, prefix, welcome, ban and kick message). **yes / no**"
            await client.send_message(message.channel, msg_one)

            # First check

            def check_yes1(msg):
                # yes or no
                if str(msg.content).lower().strip(" ") == "yes":
                    handler.server_setup(message.channel.server)

                return True

            ch1 = await client.wait_for_message(timeout=35, author=auth, check=check_yes1)
            if ch1 is None:
                timeout(message)
                return

            # SECOND MESSAGE
            msg_two = "What prefix would you like to use for all commands?\n" \
                      "Type that prefix.\n(prefix example: **!** 'translates to' `!help`, `!ping`, ...)"
            await client.send_message(message.channel, msg_two)

            # Second check, does not need yes/no filter
            ch2 = await client.wait_for_message(timeout=35, author=auth)
            if ch2 is None:
                timeout(message)
                return

            if ch2.content:
                handler.change_prefix(message.channel.server, str(ch2.content).strip(" "))

            # THIRD MESSAGE
            msg_three = "What would you like me to say when a person joins your server?\n" \
                        "Reply with that message or with None if you want to disable welcome messages. \n" \
                        "(:user translates to a mention of the joined user; for example -> :user, welcome to this server!)"
            await client.send_message(message.channel, msg_three)

            ch3 = await client.wait_for_message(timeout=35, author=auth)
            if ch3 is None:
                timeout(message)
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

            ch3 = await client.wait_for_message(timeout=35, author=auth, check=check_yes3)
            if ch3 is None:
                timeout(message)
                return

            # FIFTH MESSAGE
            msg_five = """Would you like me to filter swearing? **yes / no**"""
            await client.send_message(message.channel, msg_five)

            # Fifth check check

            def check_yes4(msg):
                # yes or no

                if str(msg.content).lower().strip(" ") == "yes":
                    handler.update_moderation_settings(message.channel.server, "filterwords", True)
                else:
                    handler.update_moderation_settings(message.channel.server, "filterwords", False)

                return True

            ch4 = await client.wait_for_message(timeout=35, author=auth, check=check_yes4)
            if ch4 is None:
                timeout(message)
                return

            msg_final = """**This concludes the basic server setup.**
But there are a few more settings to set up if you need'em:
➤ channel blacklisting - `nano.blacklist add/remove channel_name`
➤ kick message - `_kickmsg message`
➤ ban message - `_banmsg message`

The prefix can simply be changed again with `nano.changeprefix prefix`.
Admin commands can only be used by people with a role named "Nano Admin". If you do not want to assign roles, use `nano.admins add @mention`.

You and all admins can also add/remove/list custom commands with `_cmd add/remove/list command|response`.
For a list of all commands, use `_cmds`.""".replace("_", str(ch2.content))

            await client.send_message(message.channel, msg_final)

    async def on_member_remove(self, member, **_):
        # check for softban
        if self.timer.get_ban(member):
            return "return"

        # check for normal ban
        elif member.id in self.bans:
            self.bans.remove(member.id)
            return "return"


class NanoPlugin:
    _name = "Admin Commands"
    _version = "0.2.3"

    handler = Admin
    events = {
        "on_message": 10,
        "on_member_remove": 4
        # type : importance
    }
