# coding=utf-8
import time
import os
import asyncio
import logging
import importlib
from pickle import load, dumps
from discord import Message, Client, DiscordException, Object, User
from data.utils import resolve_time, convert_to_seconds, is_valid_command, is_empty, StandardEmoji, decode, gen_id
from data.stats import MESSAGE, WRONG_ARG

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

DEFAULT_REMINDER_LIMIT = 2
TICK_DURATION = 15
EXCEEDED_REMINDER_LIMIT = "{} You have exceeded the maximum amount of reminders (**{}** at once).".format(StandardEmoji.WARNING, DEFAULT_REMINDER_LIMIT)

REMINDER_PERSONAL = "personal"
REMINDER_CHANNEL = "channel"

remind_help = "**Remind help**\n`_remind me in [sometime]: [message]` - reminds you in your DM\n" \
              "`_remind here in [sometime]: [message]` - reminds everyone in current channel"

commands = {
    "_remind": {"desc": "General module for timers\nSubcommands: remind me in, remind here in, remind list, remind remove", "use": None, "alias": None},
    "_remind me in": {"desc": "Adds a reminder (reminds you in dm)", "use": "[command] [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind here in": {"desc": "Adds a reminder (reminds everybody in current channel)", "use": "[command] [time (ex: 3h 5min)] : [message]", "alias": None},
    "_remind list": {"desc": "Displays all ongoing timers.", "use": None, "alias": "_reminder list"},
    "_reminder list": {"desc": "Displays all ongoing timers.", "use": None, "alias": "_remind list"},
    "_remind help": {"desc": "Displays help for reminders.", "use": None, "alias": None},
    "_remind remove": {"desc": "Removes a timer with supplied description or time (or all timers with 'all')", "use": "[command] [timer description or time in sec]", "alias": None},
}

valid_commands = commands.keys()

# Functions


class LegacyReminderHandler:
    def __init__(self, client, _, loop=asyncio.get_event_loop()):
        self.client = client
        self.loop = loop

        self.reminders = {}

        self.wait = False

    def get_reminder_amount(self):
        return len(self.reminders)

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

    def remove_reminder(self, user_id, reminder):
        if self.reminders.get(user_id):

            for c, rm in enumerate(self.reminders[user_id]):
                if reminder == rm.get("raw"):
                    self.reminders[user_id].pop(c)
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
        content = "{} You asked me to remind you: \n```{}```".format(StandardEmoji.ALARM, content)

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


class RedisReminderHandler:
    """
    Datatype: Hash

    reminder:<SERVER_ID> =>

                    Key: Randomly generated if
                    Value: Json-encoded
                    --------------------------
                    Values:
                            full_time: Reminder length
                            content: Formatted content to send
                            receiver: User/Channel id
                            time_created: unix epoch time
                            time_target: time_created + full_time
                            author: author id
                            raw: raw content

    """
    def __init__(self, client, handler, loop=asyncio.get_event_loop()):
        self.redis = handler.get_plugin_data_manager(namespace="reminder")

        self.loop = loop
        self.client = client
        self.wait = False

        try:
            self.json = importlib.import_module("ujson")
        except ImportError:
            self.json = importlib.import_module("json")

    def get_reminder_amount(self):
        return len(self.get_all_reminders())

    def is_active(self):
        return bool(self.get_all_reminders())

    def get_reminders(self, user_id):
        if self.redis.exists(user_id):
            return {int(idd): self.json.loads(a) for idd, a in self.redis.hgetall(user_id).items()}
        else:
            return []

    def get_all_reminders(self):
        return [self.get_reminders(decode(a).strip("reminder:")) for a in self.redis.scan_iter("*")]

    def remove_all_reminders(self, user):
        if self.redis.exists(user.id):
            self.redis.delete(user.id)

    def remove_reminder(self, user_id, reminder_id):
        if self.redis.exists(user_id):
            return self.redis.hdel(user_id, reminder_id)

        return False

    def check_reminders(self, user):
        """
        True == ok
        False = not ok
        :param user: User or Member
        :return: success
        """
        if self.redis.exists(user.id):
            return bool(len(self.get_reminders(user.id)) <= DEFAULT_REMINDER_LIMIT)

        else:
            return True

    def set_reminder(self, channel, author, content, tim, reminder_type=REMINDER_PERSONAL):
        """
        Sets a reminder
        :param channel: Where to send this
        :param author: Who is the author
        :param content: String : message
        :param tim: time (int)
        :param reminder_type: type of reminder (personal or channel)
        :return: success
        """
        t = time.time()

        if not self.check_reminders(author):
            return -1

        tim = convert_to_seconds(tim)
        if not (5 <= tim < 172800):  # Allowed reminder duration: 5 sec to 2 days
            return False

        raw = str(content)

        if reminder_type == REMINDER_PERSONAL:
            template = "{} You asked me to remind you:\n```{}```"
        else:
            template = "{} Timer is up!\n```{}```"

        content = template.format(StandardEmoji.ALARM, content)

        # Add the reminder to the list
        rm_id = gen_id(length=12)
        tree = {"full_time": tim, "content": content, "receiver": channel.id, "time_created": int(t),
                "time_target": int(tim + t), "author": author.id, "raw": raw, "type": reminder_type}
        field = self.json.dumps(tree)

        print("New reminder: {} to {}".format(raw, channel.id))

        return self.redis.hset(author.id, rm_id, field)

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

    async def dispatch(self, rem):
        try:
            log.debug("Dispatching")

            if rem.get("type") == REMINDER_PERSONAL:
                receiver = User(id=rem.get("receiver"))
            else:
                receiver = Object(id=rem.get("receiver"))

            await self.client.send_message(receiver, rem.get("content"))
        except DiscordException as e:
            log.warning(e)

    async def start_monitoring(self):
        last_time = time.time()

        while True:
            # Iterate through users and their reminders
            for user in self.get_all_reminders():
                for rm_id, reminder in user.items():
                    # If enough time has passed, send the reminder
                    if reminder.get("time_target") <= last_time:

                        await self.dispatch(reminder)
                        self.remove_reminder(reminder.get("author"), rm_id)

            # And tick.
            last_time = await self.tick(last_time)


class Reminder:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.legacy = kwargs.get("legacy")

        if self.legacy:
            self.reminder = LegacyReminderHandler(self.client, self.loop)

            # Uses the cache if it exists

            if os.path.isfile("cache/reminders.temp"):
                # Removes the file if it is empty
                if is_empty("cache/reminders.temp"):
                    os.remove("cache/reminders.temp")
                else:
                    log.info("Using reminders.cache")

                    with open("cache/reminders.temp", "rb") as vote_cache:
                        rem = load(vote_cache)

                    # 3.1.5 : disabled
                    # os.remove("cache/reminders.temp")
                    # Sets the reminders to the state before restart
                    self.reminder.reminders = rem

        else:
            self.reminder = RedisReminderHandler(self.client, self.handler, self.loop)

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

            if len(args) != 2:
                await client.send_message(message.channel, "Incorrect command use. See `_help remind me in` for usage".replace("_", prefix))
                self.stats.add(WRONG_ARG)
                return

            content = str(args[1]).strip(" ")

            if not args[0].isnumeric():
                ttr = convert_to_seconds(args[0])
            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.author, message.author, content, ttr, reminder_type=REMINDER_PERSONAL)

            if resp == -1:
                await client.send_message(message.channel, EXCEEDED_REMINDER_LIMIT)

            elif resp is False:
                await client.send_message(message.channel, "Not a valid time range (5 seconds to 2 days")

            else:
                await client.send_message(message.channel, "Reminder set :)")

        # !remind here in [time]:[reminder]
        elif startswith(prefix + "remind here in"):
            args = str(message.content)[len(prefix + "remind here in "):].strip().split(":")

            if len(args) != 2:
                await client.send_message(message.channel, "Incorrect command use. See `_help remind here in` for usage".replace("_", prefix))
                self.stats.add(WRONG_ARG)
                return

            content = str(args[1]).strip(" ")

            if not args[0].isnumeric():
                ttr = convert_to_seconds(args[0])
            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.channel, message.author, content, ttr, reminder_type=REMINDER_CHANNEL)

            if resp == -1:
                await client.send_message(message.channel, EXCEEDED_REMINDER_LIMIT)

            elif resp is False:
                await client.send_message(message.channel, "Not a valid time range (5 seconds to 2 days")

            else:
                await client.send_message(message.channel, "Reminder set :)")

        # !remind list
        elif startswith(prefix + "remind list", prefix + "reminder list"):
            reminders = self.reminder.get_reminders(message.author.id)

            if not reminders:
                await client.send_message(message.channel, "You don't have any reminders.")
                return

            rem = []
            for reminder in reminders.values():
                # Gets the remaining time
                ttl = reminder.get("time_target") - time.time()

                cont = self.nano.get_plugin("commons").get("instance").at_everyone_filter(reminder.get("raw"), message.author, message.server)

                if (ttl != abs(ttl)) or ttl == 0:
                    when = "**soon™**"
                else:
                    when = "in **{}**".format(resolve_time(ttl))

                rem.append("➤ {} ({})".format(cont, when))

            await client.send_message(message.channel, "Your reminders:\n" + "\n".join(rem))

        # !remind remove
        elif startswith(prefix + "remind remove"):
            r_name = message.content[len(prefix + "remind remove"):].strip()

            if r_name == "all":
                self.reminder.remove_all_reminders(message.author)

            else:
                r_resp = self.reminder.remove_reminder(message.author.id, r_name)

                if not r_resp:
                    await client.send_message(message.channel, "No reminder with such content.")
                else:
                    await client.send_message(message.channel, "Reminder removed.")

        # !remind help
        elif startswith(prefix + "remind", prefix + "remind help"):
            await client.send_message(message.channel, remind_help.replace("_", prefix))

    async def on_shutdown(self, **_):
        if not self.legacy:
            return

        # Saves the state
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        if self.reminder.is_active():
            with open("cache/reminders.temp", "wb") as cache:
                print(self.reminder.reminders)
                cache.write(dumps(self.reminder.reminders))  # Save instance of ReminderHandler to be used on the next boot
        else:
            try:
                os.remove("cache/reminders.temp")
            except OSError:
                pass


class NanoPlugin:
    name = "Reminder Commands"
    version = "0.2.3"

    handler = Reminder
    events = {
        "on_message": 10,
        "on_shutdown": 5,
        # type : importance
    }
