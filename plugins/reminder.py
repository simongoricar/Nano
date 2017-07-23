# coding=utf-8
import asyncio
import importlib
import logging
import time

from discord import Message, Client, DiscordException, Object, User

from data.stats import MESSAGE, WRONG_ARG
from data.utils import resolve_time, convert_to_seconds, is_valid_command, decode, gen_id

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

DEFAULT_REMINDER_LIMIT = 2
TICK_DURATION = 15

REMINDER_PERSONAL = "personal"
REMINDER_CHANNEL = "channel"

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

class RedisReminderHandler:
    """
    Data type: Hash

    reminder:<USER_ID> =>

                    Key: Randomly generated
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
    def __init__(self, client, handler, trans, loop=asyncio.get_event_loop()):
        self.redis = handler.get_plugin_data_manager(namespace="reminder")

        self.loop = loop
        self.client = client
        self.trans = trans
        self.wait = False

        try:
            self.json = importlib.import_module("ujson")
        except ImportError:
            self.json = importlib.import_module("json")

    def get_reminder_amount(self):
        return len(self.get_all_reminders())

    def is_active(self):
        return bool(self.get_all_reminders())

    def prepare_remind_content(self, content, lang):
        # Used for find_id_from_content
        return self.trans.get("MSG_REMINDER_PRIVATE", lang).format(content), \
               self.trans.get("MSG_REMINDER_CHANNEL", lang).format(content)

    def prepare_private(self, content, lang):
        return self.trans.get("MSG_REMINDER_PRIVATE", lang).format(content)

    def prepare_channel(self, content, lang):
        return self.trans.get("MSG_REMINDER_CHANNEL", lang).format(content)

    def get_reminders(self, user_id):
        if self.redis.exists(user_id):
            return {int(idd): self.json.loads(a) for idd, a in self.redis.hgetall(user_id).items()}
        else:
            return {}

    def get_all_reminders(self):
        return [self.get_reminders(decode(a).strip("reminder:")) for a in self.redis.scan_iter("*")]

    def find_id_from_content(self, user, content, lang):
        reminders = self.get_reminders(user)
        private_ann, channel_ann = self.prepare_remind_content(content, lang)

        for rem_id, rem_content in reminders.items():
            if rem_content.get("content") == private_ann or rem_content.get("content") == channel_ann:
                return rem_id

        return None

    def remove_all_reminders(self, user):
        if self.redis.exists(user.id):
            self.redis.delete(user.id)

    def remove_reminder(self, user_id, rem_id):
        return self.redis.hdel(user_id, rem_id)

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

    def set_reminder(self, channel, author, content, tim, lang, reminder_type=REMINDER_PERSONAL):
        """
        Sets a reminder
        :param channel: Where to send this
        :param author: Who is the author
        :param content: String : message
        :param tim: time (int)
        :param reminder_type: type of reminder (personal or channel)
        :param lang: language used in that server
        :return: bool
        """
        t = time.time()

        if not self.check_reminders(author):
            return -1

        tim = convert_to_seconds(tim)
        if not (5 <= tim < 172800):  # Allowed reminder duration: 5 sec to 2 days
            return False

        raw = str(content)

        if reminder_type == REMINDER_PERSONAL:
            content = self.prepare_private(content, lang)
        else:
            content = self.prepare_channel(content, lang)

        # Add the reminder to the list
        rm_id = gen_id(length=12)
        tree = {"full_time": tim, "content": content, "receiver": channel.id, "time_created": int(t),
                "time_target": int(tim + t), "author": author.id, "raw": raw, "type": reminder_type}
        field = self.json.dumps(tree)

        log.info("New reminder: {} to {}".format(raw, channel.id))

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
        self.trans = kwargs.get("trans")

        self.reminder = RedisReminderHandler(self.client, self.handler, self.trans, self.loop)

        self.loop.create_task(self.reminder.start_monitoring())

    async def on_message(self, message, **kwargs):
        client = self.client
        prefix = kwargs.get("prefix")

        trans = self.trans
        lang = kwargs.get("lang")

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
                await client.send_message(message.channel, trans.get("MSG_REMINDER_WU_ME", lang).format(prefix))
                self.stats.add(WRONG_ARG)
                return

            content = str(args[1]).strip(" ")

            if not args[0].isnumeric():
                if "[" in args[0]:
                    # When people actually do !remind here in [1h 32min]: omg why
                    await client.send_message(message.channel, trans.get("MSG_REMINDER_NO_BRACKETS", lang))
                    return

                try:
                    ttr = convert_to_seconds(args[0])
                except ValueError:
                    await client.send_message(message.channel, trans.get("MSG_REMINDER_INVALID_FORMAT", lang))
                    return

            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.author, message.author, content, ttr, lang, reminder_type=REMINDER_PERSONAL)

            if resp == -1:
                await client.send_message(message.channel, trans.get("MSG_REMIDNER_LIMIT_EXCEEDED", lang).format(DEFAULT_REMINDER_LIMIT))

            elif resp is False:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_INVALID_RANGE", lang))

            else:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_SET", lang))

        # !remind here in [time]:[reminder]
        elif startswith(prefix + "remind here in"):
            args = str(message.content)[len(prefix + "remind here in "):].strip().split(":")

            if len(args) != 2:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_WU_HERE", lang).format(prefix))
                self.stats.add(WRONG_ARG)
                return

            content = str(args[1]).strip(" ")

            if not args[0].isnumeric():
                try:
                    ttr = convert_to_seconds(args[0])
                except ValueError:
                    await client.send_message(message.channel, trans.get("MSG_REMINDER_NO_PARTIALS", lang))
                    return
            else:
                ttr = int(args[0])

            resp = self.reminder.set_reminder(message.channel, message.author, content, ttr, lang, reminder_type=REMINDER_CHANNEL)

            if resp == -1:
                await client.send_message(message.channel, trans.get("MSG_REMIDNER_LIMIT_EXCEEDED", lang).format(DEFAULT_REMINDER_LIMIT))

            elif resp is False:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_INVALID_RANGE", lang))

            else:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_SET", lang))

        # !remind list
        elif startswith(prefix + "remind list", prefix + "reminder list"):
            reminders = self.reminder.get_reminders(message.author.id)

            if not reminders:
                await client.send_message(message.channel, trans.get("MSG_REMINDER_LIST_NONE", lang))
                return

            rem = []
            for reminder in reminders.values():
                # Gets the remaining time
                ttl = reminder.get("time_target") - time.time()

                cont = self.nano.get_plugin("commons").get("instance").at_everyone_filter(reminder.get("raw"), message.author, message.server)

                if (ttl != abs(ttl)) or ttl == 0:
                    when = trans.get("MSG_REMINDER_SOON", lang)
                else:
                    when = "in **{}**".format(resolve_time(ttl, lang))

                rem.append("➤ {} ({})".format(cont, when))

            await client.send_message(message.channel, trans.get("MSG_REMINDER_LIST", lang).format("\n".join(rem)))

        # !remind remove
        elif startswith(prefix + "remind remove"):
            r_name = message.content[len(prefix + "remind remove"):].strip()

            if r_name == "all":
                self.reminder.remove_all_reminders(message.author)
                await client.send_message(message.channel, trans.get("MSG_REMINDER_DELETE_ALL", lang))

            else:
                r_resp = self.reminder.remove_reminder(message.author.id, r_name)

                if not r_resp:
                    await client.send_message(message.channel, trans.get("MSG_REMINDER_DELETE_NONE", lang))
                else:
                    await client.send_message(message.channel, trans.get("MSG_REMINDER_DELETE_SUCCESS", lang))

        # !remind help
        elif startswith(prefix + "remind", prefix + "remind help"):
            await client.send_message(message.channel, trans.get("MSG_REMINDER_HELP", lang).replace("_", prefix))


class NanoPlugin:
    name = "Reminder Commands"
    version = "0.2.3"

    handler = Reminder
    events = {
        "on_message": 10,
        # type : importance
    }
