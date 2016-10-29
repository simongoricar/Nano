# coding=utf-8
import threading
import os
from datetime import datetime

# Threading helper


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


# Singleton


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def resolve_time(tm):
    try:
        tm = int(round(tm, 0))
    except TypeError:
        return None

    days = 0
    hours = 0
    minutes = 0

    while True:
        if tm >= 86400:  # 1 Day
            days += 1
            tm -= 86400

        elif tm >= 3600:  # 1 hour
            hours += 1
            tm -= 3600

        elif tm >= 60:  # 1 minute
            minutes += 1
            tm -= 60

        else:
            break

    def get(t, name):
        return "{} {}".format(t, name) if t else ""

    def comma(statement):
        return ", " if statement else ""

    # Ayy lmao
    return "{}{}{}{}{}{}{}".format(get(days, "days"), comma(days and hours),
                                   get(hours, "hours"), comma(hours and minutes),
                                   get(minutes, "minutes"),
                                   " and " if minutes and tm else "",
                                   get(int(round(tm, 0)), "seconds")).strip(" ")


possibilities = [
    "s", "sec",
    "m", "min",
    "h", "hr",
    "d", "day"]

def convert_to_seconds(string):
    if str(string).isnumeric():
        return int(string)

    cp = str(string).split(" ")

    for c, el in enumerate(cp):
        try:
            if cp[c + 1] in possibilities:
                cp[c] = str(el + cp.pop(c + 1))
        except IndexError:
            pass

    total_seconds = 0
    for el in cp:
        el = str(el).replace(" ", "").replace("\n", "")

        if el.endswith("s"):
            total_seconds += int(el[:-1])
        elif el.endswith("sec"):
            total_seconds += int(el[:-3])

        elif el.endswith("m"):
            total_seconds += int(el[:-1]) * 60
        elif el.endswith("min"):
            total_seconds += int(el[:-3]) * 60

        elif el.endswith("hr"):
            total_seconds += int(el[:-2]) * 60 * 60
        elif el.endswith("h"):
            total_seconds += int(el[:-1]) * 60 * 60

        elif el.endswith("d"):
            total_seconds += int(el[:-1]) * 60 * 60 * 24
        elif el.endswith("day"):
            total_seconds += int(el[:-3]) * 60 * 60 * 24

    # Seconds
    return int(total_seconds)

words = (
    "on",
    "enabled",
    "enable",
    "turn on",
    "true",
)


def get_decision(content, wrd=words):
    return str(content).lower().startswith(wrd)


def is_valid_command(msg, commands, **kwargs):
    if not kwargs.get("prefix"):
        prefix = "!"
    else:
        prefix = kwargs.get("prefix")

    def has(message):
        for command in commands:
            command = command.replace("_", prefix)

            if str(message).startswith(command):
                return True

        return False

    return has(msg)


def log_to_file(content):
    with open("data/log.txt", "a") as file:
        date = datetime.now()
        cn = date.strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)
        file.write(cn + "\n")


def is_empty(path):
    if os.path.isfile(path):
        return os.stat(path).st_size == 0

    else:
        return False
