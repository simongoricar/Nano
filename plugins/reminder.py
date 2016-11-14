# coding=utf-8
import time
import os
import asyncio
import logging
from pickle import load, dumps
from discord import Message, Client, DiscordException
from data.utils import resolve_time, convert_to_seconds, is_valid_command, is_empty
from data.stats import MESSAGE

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

DEFAULT_REMINDER_LIMIT = 2

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


class ReminderHandler():
    def __init__(self, client, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop

        self.reminders = {}

        self.wait = False

    def lock(self):
        self.wait = True

    def release(self):
        self.wait = False

    async def wait(self):
        while self.wait:
            await asyncio.sleep(0.01)

    def is_active(self):
        return bool(self.reminders)

    def get_reminders(self, user):
        return self.reminders.get(user.id)

    def remove_all_reminders(self, user):
        if self.reminders.get(user.id):
            self.reminders[user.id] = []

    def remove_reminder(self, user, reminder):
        if self.reminders.get(user.id):

            for c, rm in enumerate(self.reminders[user.id]):
                if reminder == rm.get("raw"):
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
            return len(self.reminders[user.id]) > limit+1

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

        raw = str(content)
        content = ":alarm_clock: You asked me to remind you: \n```{}```".format(content)

        # Add the reminder to the list
        if not self.reminders.get(author.id):
            self.reminders[author.id] = [{"full_time": tim, "content": content, "raw": raw, "receiver": channel,
                                          "time_created": int(t), "time_target": int(tim + t), "author": author.id}]
        else:
            self.reminders[author.id].append({"full_time": tim, "content": content, "raw": raw, "receiver": channel,
                                              "time_created": int(t), "time_target": int(tim + t), "author": author.id})

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
            log.debug("Dispatching")
            await self.client.send_message(reminder.get("receiver"), reminder.get("content"))
        except DiscordException:
            pass

    async def start_monitoring(self):
        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for user in self.reminders.values():
                for reminder in user:

                    # If enough time has passed, send the reminder
                    if reminder.get("time_target") <= last_time:

                        await self.dispatch(reminder)

                        try:
                            self.reminders[reminder.get("author")].remove(reminder)
                        except KeyError:
                            pass

            # And tick.
            last_time = await self.tick(last_time)


class Reminder:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.reminder = ReminderHandler(self.client, self.loop)

        # Uses the cache if it exists

        if os.path.isfile("cache/reminders.temp"):

            # Removes the file if it is empty
            if is_empty("cache/reminders.temp"):
                os.remove("cache/reminders.temp")

            # or uses it
            else:
                log.info("Using reminders.cache")

                with open("cache/reminders.temp", "rb") as vote_cache:
                    rem = load(vote_cache)

                os.remove("cache/reminders.temp")

                # Sets the reminders to the state before restart
                self.reminder.reminders = rem

        self.loop.create_task(self.reminder.start_monitoring())

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
                ttl = reminder.get("time_target") - time.time()
                rem.append("➤ {} (in **{}**)".format(reminder.get("raw"), resolve_time(ttl)))

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

    async def on_shutdown(self, **_):
        # Saves the state
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        if self.reminder.is_active():
            with open("cache/reminders.temp", "wb") as cache:
                print(self.reminder.reminders)
                cache.write(dumps(self.reminder.reminders))  # Save instance of ReminderHandler to be used on the next boot


class NanoPlugin:
    _name = "Reminder Commands"
    _version = "0.2.2"

    handler = Reminder
    events = {
        "on_message": 10,
        "on_shutdown": 5,
        # type : importance
    }
