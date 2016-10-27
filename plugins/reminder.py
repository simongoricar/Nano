# coding=utf-8
import time
import asyncio
import logging
from discord import Message, Client
from data.utils import resolve_time, convert_to_seconds, is_valid_command
from data.stats import MESSAGE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CONSTANTS

DEFAULT_REMINDER_LIMIT = 1

remind_help = "**Remind help**\n`_remind me in [sometime]: [message]` - reminds you in your DM\n" \
              "`_remind here in [sometime]: [message]` - reminds everyone in current channel"

valid_commands = [
    "_remind here in",
    "_remind me in",
    "_remind help",
    "_remind list",
    "_reminder list",
    "_remind remove",
]

# Functions


class RemindHandler:
    def __init__(self, client, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop

        self.reminders = {}

        self.must_wait = False

    def wait(self):
        self.must_wait = True

    def wait_release(self):
        self.must_wait = False

    def get_reminders(self, user):
        return self.reminders.get(user.id)

    def remove_all_reminders(self, user):
        if self.reminders.get(user.id):
            self.reminders[user.id] = []

    def remove_reminder(self, user, rem):
        if self.reminders.get(user.id):

            for c, rm in enumerate(self.reminders[user.id]):
                if rem == rm[0] or rem == rm[1]:
                    self.reminders[user.id].pop(c)
                    return True

        return False

    def check_reminders(self, user, limit=DEFAULT_REMINDER_LIMIT):
        """
        True == ok
        False = not ok
        :param user: User or Member
        :param limit: reminder limit
        :return: bool
        """
        if self.reminders.get(user.id):
            if len(self.reminders[user.id]) > limit+1:
                return True

            else:
                return False
        else:
            return True

    def set_reminder(self, channel, author, content, tim):
        """
        Sets a reminder
        :param channel: Where to send this
        :param author: Who is the author
        :param content: String : message
        :param tim: time (int)
        :return: bool indicating success
        """
        t = time.time()

        if not self.check_reminders(author):
            return -1

        tim = convert_to_seconds(tim)

        if not (5 < tim < 172800):  # 5 sec to 2 days
            return False

        # Add the reminder to the list
        if not self.reminders.get(author.id):
            self.reminders[author.id] = [[tim, content, int(round(t, 0))]]
        else:
            self.reminders[author.id].append([tim, content, int(round(t, 0))])

        fulltext = ":alarm_clock: Reminder: \n```{}```".format(content)

        ttl = tim - (time.time() - t)

        # Creates a coroutine task
        self.schedule(channel, fulltext, ttl, author.id)

        return True

    def schedule(self, channel, content, tim, uid):
        self.loop.create_task(self._schedule(channel, content, tim, uid))

    async def _schedule(self, channel, content, tim, uid):
        logger.info("Event scheduled")
        await asyncio.sleep(tim)

        if not [rem for rem in self.reminders.get(uid) if rem[0] == tim]:
            logger.debug("Reminder deleted before execution, quitting")
            return

        while self.must_wait:
            await asyncio.sleep(0.1)

        try:
            logger.debug("Dispatching")
            await self.client.send_message(channel, content)

        # This MUST be done in all cases
        finally:
            self.reminders[uid] = [a for a in self.reminders[uid] if a[0] != tim]


class Reminder:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.reminder = RemindHandler(self.client, self.loop)

    async def on_message(self, message, **kwargs):
        client = self.client
        prefix = kwargs.get("prefix")

        assert isinstance(message, Message)
        assert isinstance(client, Client)

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # !remind me in [time]:[reminder]
        if startswith(prefix + "remind me in"):
            args = str(message.content)[len(prefix + "remind me in "):].strip().split(":")

            if not args[0].isnumeric():
                ttr = convert_to_seconds(args[0])
            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.author, message.author, args[1], ttr)

            if resp == -1:
                await client.send_message(message.channel,
                                          "You have exceeded the maximum amount of reminders (**1** at once).")

            elif resp is False:
                await client.send_message(message.channel, "Not a valid time range (5 seconds to 2 days")

            else:
                await client.send_message(message.channel, "Reminder set :)")

        # !remind here in [time]:[reminder]
        elif startswith(prefix + "remind here in"):
            args = str(message.content)[len(prefix + "remind here in "):].strip().split(":")

            if not args[0].isnumeric():
                ttr = convert_to_seconds(args[0])
            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.channel, message.author, args[1].strip(), ttr)

            if resp == -1:
                await client.send_message(message.channel,
                                          "You have exceeded the maximum amount of reminders (**1** at once).")

            elif resp is False:
                await client.send_message(message.channel, "Not a valid time range (5 seconds to 2 days")

            else:
                await client.send_message(message.channel, "Reminder set :)")

        # !remind list
        elif startswith(prefix + "remind list", prefix + "reminder list"):
            reminders = self.reminder.get_reminders(message.author)

            if not reminders:
                await client.send_message(message.channel, "You have not set any reminders.")
                return

            rem = []
            for reminder in reminders:
                # Gets the remaining time
                ttl = reminder[0] - (time.time() - reminder[2])
                rem.append("➤ {} (in **{}**)".format(reminder[1], resolve_time(ttl)))

            await client.send_message(message.channel, "Your reminders:\n" + "\n".join(rem))

        # !remind remove
        elif startswith(prefix + "remind remove"):
            r_name = message.content[len(prefix + "remind remove"):].strip()

            if r_name == "all":
                self.reminder.remove_all_reminders(message.author)

            else:
                r_resp = self.reminder.remove_reminder(message.author, r_name)

                if not r_resp:
                    await client.send_message(message.channel, "No reminder with such content.")
                else:
                    await client.send_message(message.channel, "Reminder removed.")

        # !remind help
        elif startswith(prefix + "remind", prefix + "remind help"):
            await client.send_message(message.channel, remind_help.replace("_", prefix))


class NanoPlugin:
    _name = "Reminder Commands"
    _version = 0.1

    handler = Reminder
    events = {
        "on_message": 10
        # type : importance
    }
