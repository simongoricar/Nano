# coding=utf-8
import threading
import os
import uuid
from datetime import datetime
from typing import Iterable

from .translations import TranslationManager

# Threading helper (OBSOLETE)


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class IgnoredException(Exception):
    """
    An exception that will be ignored (for flow control)
    """
    pass

# Singleton


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class StandardEmoji:
    """
    Includes standard emojis to use
    """
    # Success indicators
    OK = ":white_check_mark:"
    OK_BLUE = ":ballot_box_with_check:"
    GREEN_FAIL = ":negative_squared_cross_mark:"
    CROSS = ":x:"
    WARNING = ":warning:"
    PERFECT = ":ok_hand:"

    # Face emojis
    SMILEY = ":smiley:"
    SMILE = ":smile:"
    TONGUE = ":stuck_out_tongue:"
    THINKING = ":thinking:"
    SCREAM = ":scream:"
    CRY = ":sob:"
    EXPRESSIONLESS = ":expressionless:"
    FROWN = ":frowning:"
    FROWN2 = ":frowning2:"
    SLEEP = ":sleeping:"

    ZIP_MOUTH = ":zipper_mouth:"
    ROFL = ":rofl:"

    # Other
    THUMBS_UP = ":+1:"
    MUSCLE = ":muscle:"
    BOT = ":robot:"
    ALIEN = ":alien:"
    SPY = ":spy:"
    ALARM = ":alarm_clock:"
    NO_ENTRY = ":no_entry_sign:"
    WINK = ":wink:"


class BotEmoji:
    BOT_TAG = "<:botTag:230105988211015680>"

    ONLINE = "<:online:313956277808005120>"
    OFFLINE = "<:offline:313956277237710868>"
    AWAY = "<:away:313956277220802560>"
    DND = "<:dnd:313956276893646850>"
    STREAMING = "<:streaming:313956277132853248>"
    INVISIBLE = "<:invisible:313956277107556352>"

    DISCORD = "<:discord:314003252830011395>"
    UPDATE = "<:update:264184209617321984>"
    PARTNER = "<:partner:314068430556758017>"
    HYPE_SQUAD = "<:hypesquad:314068430854684672>"
    NITRO = "<:nitro:314068430611415041>"
    STAFF = "<:staff:314068430787706880>"
    GIF = "<:gif:314068430624129039>"
    STAFF_TOOLS = "<:stafftools:314348604095594498>"

    YOUTUBE = "<:youtube:314349922885566475>"
    YT_GAMING = "<:ytgaming:314349923132899338>"
    TWITTER = "<:twitter:314349922877046786>"
    REDDIT = "<:reddit:314349923103670272>"
    SKYPE = "<:skype:314349923107602432>"
    STEAM = "<:steam:314349923044687872>"
    TWITCH = "<:twitch:314349922755411970>"
    LEAGUE_OF_LEGENDS = "<:league:314349922902343681>"
    BATTLE_NET = "<:battlenet:314349923006939136>"
    SOUNDCLOUD = "<:soundcloud:314349923090825216>"
    CHECK = "<:check:314349398811475968>"
    MARK_X = "<:xmark:314349398824058880>"
    EMPTY = "<:empty:314349398723264512>"


tr = TranslationManager()

def resolve_time(tm, lang):
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

    fields = []
    if days:
        fields.append("{} {}".format(days, tr.get("TIME_DAYS", lang)))
    if hours:
        fields.append("{} {}".format(hours, tr.get("TIME_HOURS", lang)))
    if minutes:
        fields.append("{} {}".format(minutes, tr.get("TIME_MINUTES", lang)))

    last = "{} {}".format(int(tm), tr.get("TIME_SECONDS", lang))
    and_lit = " and " if fields else ""

    return ", ".join(fields) + and_lit + last


possibilities = [
    "s", "sec", "seconds",
    "m", "min", "minutes",
    "h", "hr", "hours",
    "d", "day", "days"]


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

        if el.endswith("seconds"):
            total_seconds += int(el[:-7])
            continue
        elif el.endswith("minutes"):
            total_seconds += int(el[:-7]) * 60
            continue
        elif el.endswith("hours"):
            total_seconds += int(el[:-5]) * 60 * 60
            continue
        elif el.endswith("days"):
            total_seconds += int(el[:-4]) * 60 * 60 * 24
            continue

        elif el.endswith("secs"):
            total_seconds += int(el[:-4])

        elif el.endswith("sec"):
            total_seconds += int(el[:-3])

        elif el.endswith("m"):
            total_seconds += int(el[:-1]) * 60
        elif el.endswith("min"):
            total_seconds += int(el[:-3]) * 60
        elif el.endswith("mins"):
            total_seconds += int(el[:-4]) * 60

        elif el.endswith("hr"):
            total_seconds += int(el[:-2]) * 60 * 60
        elif el.endswith("h"):
            total_seconds += int(el[:-1]) * 60 * 60
        elif el.endswith("hrs"):
            total_seconds += int(el[:-3]) * 60 * 60

        elif el.endswith("d"):
            total_seconds += int(el[:-1]) * 60 * 60 * 24
        elif el.endswith("day"):
            total_seconds += int(el[:-3]) * 60 * 60 * 24

        elif el.endswith("s"):
            total_seconds += int(el[:-1])

    # Seconds
    return int(total_seconds)

words = (
    "on",
    "enabled",
    "enable",
    "turn on",
    "true",
)


def matches_list(content, *lst):
    if not lst:
        lst = words

    return str(content).lower().startswith(lst)


def is_valid_command(msg: str, commands: Iterable, prefix: str):
    for command in commands:
        command = command.replace("_", prefix)

        if msg.startswith(command):
            return True

    return False


def log_to_file(content, type_="log"):
    fn = "data/bugs.txt" if type_ == "bug" else "data/log.txt"

    with open(fn, "a") as file:
        cn = datetime.now().strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)

        try:
            file.write(cn + "\n")
        except UnicodeEncodeError as ev:
            file.write("Error while writing to file, UnicodeEncodeError: {}".format(ev))


def is_empty(path):
    if os.path.isfile(path):
        return os.stat(path).st_size == 0

    else:
        return False

none_ux = [
    "none", "false", "off", "disabled", "default", "disable"
]


def is_disabled(ct, lang=None):
    if ct is None or ct == "":
        return True

    # Language-sensitive disabling
    disables = list(none_ux)
    if lang:
        disables.append(tr.get("INFO_DISABLED"))
        disables.append(tr.get("INFO_DISABLED_A"))

    for a in none_ux:
        if str(ct).lower().startswith(a):
            return True

    return False


def invert_num(integer: int):
    return int(str(integer)[::-1])


def invert_str(str_: str):
    return str(str_[::-1])


def split_every(content, num):
    return [content[i:i + num] for i in range(0, len(content), num)]

# Needed for redis


def decode(c):
    if c is None:
        return None

    return boolify(decode_auto(c))


def bin2bool(c):
    if isinstance(c, bytes):
        c = c.decode()

    if c == 0:
        return False
    if c >= 1:
        return True

    return c

def boolify(s):
    if s == "True":
        return True
    if s == "False":
        return False
    if s == "None":
        return None

    return s


def decode_auto(some):
    if isinstance(some, bytes):
        return decode_auto(some.decode())

    if isinstance(some, str):
        # Autoconvert IDs to int
        if some.isnumeric():
            return int(some)

        return boolify(some)

    if isinstance(some, int):
        return some

    if isinstance(some, dict):
        return dict(map(decode_auto, some.items()))
    if isinstance(some, tuple):
        return tuple(map(decode_auto, some))
    if isinstance(some, list):
        return list(map(decode_auto, some))
    if isinstance(some, set):
        return set(map(decode_auto, some))

    # In case it's some other type
    return some


def gen_id(length=38):
    return int(str(uuid.uuid4().int)[:length])


def chunks(item, n):
    for i in range(0, len(item), n):
        yield item[i:i + n]


def add_dots(content, max_len=55, ending="[...]"):
    if not len(content) > max_len:
        return content
    else:
        # Make space for the ending as well
        max_len -= len(ending)

        return "{}".format(content[:max_len]) + ending


def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


specials = {
    "%20": " ",
}

def parse_special_chars(text: str):
    for t, rep in specials.items():
        text = text.replace(t, rep)

    return text

