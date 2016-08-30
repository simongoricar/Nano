# coding=utf-8

import threading
import time
import logging
import asyncio

__author__ = "DefaltSimon"

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

possibilites = [
    "s", "sec", "secs", "seconds",
    "m", "min", "mins",
    "h", "hr", "hours",
    "d", "day", "days"
]

def resolve_time(tm):
    try:
        tm = int(round(tm, 0))
    except TypeError:
        return None

    days = 0
    hours = 0
    minutes = 0

    while True:
        if tm >= 86400: # 1 Day
            days += 1
            tm -= 86400

        elif tm >= 3600: # 1 hour
            hours += 1
            tm -= 3600

        elif tm >= 60: # 1 minute
            minutes += 1
            tm -= 60

        else:
            break

    def get(t, name):
        if t:
            return "{} {}".format(t, name)
        else:
            return ""

    def comma(statement):
        if statement:
            return ", "
        else:
            return ""

    # Ayy lmao
    return "{}{}{}{}{}{}{}".format(get(days, "days"), comma(days and hours),
                                     get(hours, "hours"), comma(hours and minutes),
                                     get(minutes, "minutes"),
                                     " and " if minutes and tm else "",
                                     get(int(round(tm, 0)), "seconds")).strip(" ")



def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class InvalidParameters(Exception):
    def __init__(self, *args, **kwargs):
        pass

class ReminderLimitExceeded(Exception):
    def __init__(self, *args, **kwargs):
        pass


class Reminder:
    def __init__(self, client, loop=asyncio.get_event_loop()):
        #assert isinstance(client, Client) or isinstance(client, Nano)

        self.client = client
        self.loop = loop

        self.reminders = {}

        self.must_wait = False

    def wait(self):
        self.must_wait = True

    def wait_release(self):
        self.must_wait = False


    def _update_client(self, client):
        self.client = client

    def _update_loop(self, loop):
        self.loop = loop

    def _dispatch(self, fn, *args, **kwargs):
        log.info("Dispatching scheduled event")

        self.loop.create_task(fn(*args, **kwargs))

    @staticmethod
    def convert_to_seconds(content):
        stri = str(content).split(" ")

        for c, el in enumerate(stri):
            try:
                if stri[c+1] in possibilites:
                    stri[c] = str(el + stri.pop(c+1))
            except IndexError:
                pass

        s = 0
        for el in stri:
            el = str(el).replace(" ", "").replace("\n", "")

            if el.endswith("s"):
                s += int(el[:-1])
            elif el.endswith("sec"):
                s += int(el[:-3])


            elif el.endswith("m"):
                s += int(el[:-1]) * 60
            elif el.endswith("min"):
                s += int(el[:-3]) * 60

            elif el.endswith("hr"):
                s += int(el[:-2]) * 60 * 60
            elif el.endswith("h"):
                s += int(el[:-1]) * 60 * 60

            elif el.endswith("d"):
                s += int(el[:-1]) * 60 * 60 * 24
            elif el.endswith("day"):
                s += int(el[:-3]) * 60 * 60 * 24

        # Seconds
        return int(s)

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

    def check_reminders(self, user, limit=2):
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

    def remind_in_sec(self, channel, author, content, tim):

        t = time.time()

        #if isinstance(channel, PrivateChannel) or isinstance(channel, User) or isinstance(channel, Member):
        #    typ = "PM"
        #elif isinstance(channel, Channel):
        #    typ = "Ann"
        #else:
        #    raise InvalidParameters

        if not self.check_reminders(author):
            raise ReminderLimitExceeded

        if not self.reminders.get(author.id):
            self.reminders[author.id] = [ [tim, content, int(round(t, 0))] ]
        else:
            self.reminders[author.id].append([tim, content, int(round(t, 0))])

        fulltext = ":alarm_clock: Reminder: \n```{}```".format(content)

        try:
            tim = int(tim)
        except ValueError:
            tim = self.convert_to_seconds(tim)

        if not (5 < tim < 259200):  # 5 sec to 3 days
            return False

        # Threaded
        self.schedule(channel, fulltext, round(float(tim - (time.time() - t)), 0), uid=author.id, tstamp=int(round(t, 0)))

        return True

    @threaded
    def schedule(self, channel, content, tim, uid, tstamp):
        time.sleep(tim)

        if not [a for a in self.reminders[uid] if a[2] == tstamp]:
            log.info("Reminder deleted before execution, quitting")
            return

        while self.must_wait:
            time.sleep(0.1)

        self._dispatch(self.client.send_message, channel, content)

        self.reminders[uid] = [a for a in self.reminders[uid] if a[2] != tstamp]


class TimedBan:
    def __init__(self, client=None, loop=asyncio.get_event_loop()):
        self.data = {}

        self.loop = loop
        self.client = client

    def _set_loop(self, loop):
        self.loop = loop

    def _set_client(self, client):
        self.client = client

    def _dispatch(self, fn, *args, **kwargs):
        log.info("Dispatching scheduled event")

        self.loop.create_task(fn(*args, **kwargs))

    def get_bans(self, sid):
        return self.data.get(sid)

    def remove_ban(self, sid, member):
        if self.data.get(sid):
            self.data[sid].pop(member.id)

    @threaded
    def schedule(self, server, member, tim):
        time.sleep(tim)

        self._dispatch(self.client.unban, server, member)
        self.data[server.id].pop(member.id)


    def time_ban(self, server, member, tim):

        otim = int(tim)

        try:
            tim = int(tim)
        except TypeError:
            tim = Reminder.convert_to_seconds(tim)

        if not self.data.get(server.id):
            self.data[server.id] = {member.id : otim}
        else:
            self.data[server.id].update({member.id : otim})

        self._dispatch(self.client.ban, server, member)

        self.schedule(server, member, tim)

        return True