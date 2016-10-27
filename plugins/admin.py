# coding=utf-8
import asyncio
import logging
import time
from discord import Message, utils, Client
from data.serverhandler import ServerHandler
from data.utils import convert_to_seconds, get_decision, is_valid_command

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS

error_hierarchy = ":warning: You are not allowed to mess with this role (you are lower in the \"hierarchy\"). ¯\_(ツ)_/¯"

CHECK_MARK = ":white_check_mark:"
CROSS_MARK = ":negative_squared_cross_mark:"

valid_commands = [
    "_welcomemsg", "_kickmsg", "_banmsg", "_leavemsg",
    "_nuke", "_kick", "_ban", "_unban", "_softban", "_unmute",
    "_mute", "_user", "_role add", "_role remove", "_role replaceall",
    "_cmd add", "_cmd remove", "_cmd list", "nano.settings", "nano.displaysettings",
    "nano.admins add", "nano.admins remove", "nano.admins list"
]


class SoftBanTimer:
    def __init__(self, client, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop

        self.events = {}

        self.must_wait = False

    def wait(self):
        self.must_wait = True

    def wait_release(self):
        self.must_wait = False

    def get_reminders(self, user):
        return self.events.get(user.id)

    def remove_all_reminders(self, user):
        if self.events.get(user.id):
            self.events[user.id] = []

    def remove_reminder(self, user, rem):
        if self.events.get(user.id):

            for c, rm in enumerate(self.events[user.id]):
                if rem == rm[0] or rem == rm[1]:
                    self.events[user.id].pop(c)
                    return True

        return False

    def set_softban(self, server, user, tim):
        t = time.time()

        tim = convert_to_seconds(tim)

        if not (5 < tim < 259200):  # 5 sec to 3 days
            return False

        # Add the reminder to the list
        if not self.events.get(server.id):
            self.events[server.id] = []

        if self.events.get(server.id).get(user.id):
            return False

        self.events[user.id] = [tim, int(round(t, 0))]

        ttl = tim - (time.time() - t)

        # Creates a coroutine task to unban that person
        self.schedule(server, ttl, user)

        return True

    def schedule(self, server, user, ttl):
        self.loop.create_task(self._schedule(server, user, ttl))

    async def _schedule(self, server, user, ttl):
        logger.info("Event scheduled")
        await asyncio.sleep(ttl)

        if not [user for user in self.events.get(server.id) if user[0] == ttl]:
            logger.debug("Task deleted before execution, quitting")
            return

        while self.must_wait:
            await asyncio.sleep(0.1)

        try:
            await self.client.unban(server, user)

        # This MUST be done in all cases
        finally:
            self.events[server.id] = [a for a in self.events[server.id] if a[0] != ttl]


class Admin:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.timer = SoftBanTimer(self.client, self.loop)

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
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if not handler.can_use_restricted_commands(message.author, message.channel.server):
            return

        # !welcomemsg
        if startswith(prefix + "welcomemsg"):
            print("ok")
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
            m = await client.send_message(message.channel, "Purged {} messages :white_check_mark:".format(amount - 1))
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
                return

            await client.send_message(message.channel,
                                      "Are you sure you want to ban " + user.name + "? Confirm by replying 'CONFIRM'.")

            followup = await client.wait_for_message(author=message.author, channel=message.channel,
                                                     timeout=15, content="CONFIRM")

            if followup is None:
                await client.send_message(message.channel, "Confirmation not received, NOT banning :upside_down:")

            else:
                await client.ban(user, delete_message_days=0)
                await client.send_message(message.channel,
                                          handler.get_var(message.channel.server.id, "banmsg").replace(":user",
                                                                                                       user.name))

        # !unban
        # but wait, you cant really mention the person so this is practically useless lmao
        #elif startswith(prefix + "unban"):
        #    if len(message.mentions) >= 1:
        #        user = message.mentions[0]
        #
        #    else:
        #        user_name = str(str(message.content)[len(prefix + "kick "):])
        #
        #        user = utils.find(lambda u: u.name == str(user_name), message.channel.server.members)
        #
        #    if not user:
        #        return
        #
        #    await client.unban(user)
        #    await client.send_message(message.channel, "{} has been unbanned.".format(user.name))

        # !softban
        elif startswith(prefix + "softban"):

            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to softban.")
                return

            user = message.mentions[0]
            tim = message.content[len(prefix + "softban "):].replace("<@{}>".format(user.id), "").strip()

            await client.ban(user)

            self.timer.set_softban(message.channel.server, user, tim)

            await client.send_message(message.channel, "{} has been softbanned.".format(user.name))

        # !mute list
        elif startswith(prefix + "mute list"):
            mutes = handler.mute_list(message.server)

            if mutes:
                final = "Muted members: \n" + ", ".join(["`{}`".format(u) for u in mutes])
            else:
                final = "No members are muted."

            await client.send_message(message.channel, final)

        # !mute
        elif startswith(prefix + "mute"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to mute.")
                return

            user = message.mentions[0]

            handler.mute(user)

            await client.send_message(message.channel,
                                      "**{}** can now not speak here. :zipper_mouth:".format(user.name))

        # !unmute
        elif startswith(prefix + "unmute"):
            if len(message.mentions) == 0:
                await client.send_message(message.channel, "Please mention the member you want to unmute.")
                return

            user = message.mentions[0]

            handler.unmute(user)

            await client.send_message(message.channel, "**{}** can now speak here again :rofl:".format(user.name))

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
                await client.send_message(message.channel, ":warning: Member does not exist.")
                return

            # Gets info
            name = member.name
            mid = member.id
            avatar = str(member.avatar_url)

            is_bot = ":robot:" if member.bot else ""

            role = member.top_role
            account_created = member.created_at
            status = "Online" if member.status.online or member.status.idle else "Offline"

            # Filter @everyone out
            if role == "@everyone":
                role = "None"

            # 'Compiles' info
            final = "User: **{}** #{} {}\n➤ Status: {}\n➤ Id: `{}`\n➤ Avatar: {}\n\n➤ Top role_: **{}**\n" \
                    "➤ Created at: `{}`".format(name, member.discriminator, is_bot, status, mid,
                                                avatar, role, account_created)

            await client.send_message(message.channel, final)

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
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "remove "):
                a_role = str(message.content[len(prefix + "role remove "):]).split("<")[0].strip()
                role = utils.find(lambda r: r.name == a_role, message.channel.server.roles)

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.remove_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

            elif startswith(prefix + "role " + "replaceall "):
                a_role = str(message.content[len(prefix + "role replaceall "):]).split("<")[0].strip()
                role = utils.find(lambda r: r.name == a_role, message.channel.server.roles)

                if not can_change_role(message.author, role):
                    await client.send_message(message.channel, error_hierarchy)
                    return

                await client.replace_roles(user, role)
                await client.send_message(message.channel, "Done :white_check_mark: ")

        # !cmd add
        elif startswith(prefix + "cmd add"):
            try:
                cut = str(message.content)[len(prefix + "cmd add "):].split("|")
                handler.update_command(message.server, cut[0], cut[1])

                await client.send_message(message.channel, "Command '{}' added.".format(cut[0]))

            except (KeyError or IndexError):
                await client.send_message(message.channel,
                                          ":no_entry_sign: Wrong args, separate command and response with |")

        # !cmd remove
        elif startswith(prefix + "cmd remove"):
            cut = str(message.content)[len(prefix + "cmd remove "):]
            handler.remove_command(message.server, cut)

            await client.send_message(message.channel, "Ok :white_check_mark: ")

        # !cmd list
        elif startswith(prefix + "cmd list"):
            custom_cmds = handler.get_custom_commands(message.server)

            if not custom_cmds:
                await client.send_message(message.channel, "No custom commands on this server. "
                                                           "Add one with `_cmd add trigger|response`!".replace("_",
                                                                                                               prefix))

                return

            final = "\n".join(["{} : {}".format(name, content) for name, content in custom_cmds.items()])

            await client.send_message(message.channel, "*Custom commands:*\n" + final)

        # nano.settings
        elif startswith("nano.settings"):
            try:
                cut = str(message.content)[len("nano.settings "):].rsplit(" ", 1)
            except IndexError:
                return

            try:
                value = handler.update_moderation_settings(message.channel.server, cut[0], get_decision(cut[1]))
            except IndexError:
                # stat.pluswrongarg()
                return

            if get_decision(cut[0], ("word filter", "filter words", "wordfilter")):
                await client.send_message(message.channel, "Word filter {}".format(CHECK_MARK if value else CROSS_MARK))

            elif get_decision(cut[0], ("spam filter", "spamfilter", "filter spam")):
                await client.send_message(message.channel, "Spam filter {}".format(CHECK_MARK if value else CROSS_MARK))

            elif get_decision(cut[0], ("filterinvite", "filterinvites", "invite removal", "invite filter")):
                await client.send_message(message.channel,
                                          "Invite filter {}".format(CHECK_MARK if value else CROSS_MARK))

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


                    # /todo nano.serversetup


class NanoPlugin:
    _name = "Admin Commands"
    _version = 0.1

    handler = Admin
    events = {
        "on_message": 10
        # type : importance
    }
