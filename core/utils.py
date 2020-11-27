# coding=utf-8
import re
import uuid
import os
from datetime import datetime
from typing import Iterable

from .configuration import DIR_DATA
from .translations import TranslationManager, DEFAULT_LANGUAGE


class CmdResponseTypes:
    REGISTER_ON_FAIL = "reg_on_fail"


class DynamicResponse:
    __slots__ = ("intention", "data")

    def __init__(self, intention, data):
        self.intention = intention
        self.data = data

    @classmethod
    def register_failure_response(cls, text):
        return cls(CmdResponseTypes.REGISTER_ON_FAIL, text)


# Singleton
class Singleton(type):
    """
    Only allows one instantiation. On subsequent __init__ calls, returns the first instance
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class StandardEmoji:
    """
    Standard (:emoji:) emojis.
    """
    # Symbols
    CHECKMARK_GREEN = ":white_check_mark:"
    CHECKMARK_BLUE = ":ballot_box_with_check:"
    CROSS_GREEN = ":negative_squared_cross_mark:"
    CROSS_RED = ":x:"
    WARNING = ":warning:"
    EXCLAMATION = ":exclamation:"
    EXCLAMATION_GREY = ":grey_exclamation:"
    NO_ENTRY = ":no_entry_sign:"
    ARROW_BACKWARD = ":arrow_backward:"
    ARROW_FORWARD = ":arrow_forward:"

    # Hands
    OK_HAND = ":ok_hand:"
    THUMBS_UP = ":+1:"
    MUSCLE = ":muscle:"

    # Face emojis
    SMILEY = ":smiley:"
    SMILE = ":smile:"
    TONGUE = ":stuck_out_tongue:"
    THINKING = ":thinking:"
    SCREAM = ":scream:"
    CRY = ":sob:"
    EXPRESSIONLESS = ":expressionless:"
    FROWNING = ":frowning:"
    FROWNING_2 = ":frowning2:"
    SLEEPING = ":sleeping:"
    ZIPPER_MOUTH = ":zipper_mouth:"
    ROFL = ":rofl:"
    WINK = ":wink:"

    # Other
    ROBOT = ":robot:"
    ALIEN = ":alien:"
    SPY = ":detective:"
    PING_PONG = ":ping_pong:"
    ALARM = ":alarm_clock:"
    TIMER = ":timer:"
    CLIPBOARD = ":clipboard:"
    PAPERCLIP = ":paperclip:"
    SCROLL = ":scroll:"
    COOKIE = ":cookie:"
    CHART_UP = ":chart_with_upwards_trend:"
    CHART_DOWN = ":chart_with_downwards_trend:"
    BAR_CHART = ":bar_chart:"
    ENVELOPE = ":envelope:"
    ENVELOPE_BLUE_ARROW = ":envelope_with_arrow:"
    ENVELOPE_INCOMING = ":incoming_envelope:"
    NOTEPAD_SPIRAL = ":notepad_spiral:"
    INFORMATION_SOURCE = ":information_source:"
    PENCIL = ":pencil:"
    PENCIL_2 = ":pencil2:"
    CALENDAR = ":calendar:"
    CALENDAR_SPIRAL = ":calendar_spiral:"


class UnicodeEmojis:
    """
    Unicode versions of StandardEmoji emojis.
    """
    # Symbols
    CHECKMARK_GREEN = "✅"
    CHECKMARK_BLUE = "☑"
    CROSS_GREEN = "❎"
    CROSS_RED = "❌"
    WARNING = "⚠"
    EXCLAMATION = "❗"
    EXCLAMATION_GREY = "❕"
    NO_ENTRY = "⛔"
    ARROW_BACKWARD = "◀"
    ARROW_FORWARD = "▶"

    # Hands
    OK_HAND = "👌"
    THUMBS_UP = "👍"
    MUSCLE = "💪"

    # Face emojis
    SMILEY = "😃"
    SMILE = "😄"
    TONGUE = "😛"
    THINKING = "🤔"
    SCREAM = "😱"
    CRY = "😭"
    EXPRESSIONLESS = "😑"
    FROWNING = "😦"
    FROWNING_2 = "☹"
    SLEEPING = "😴"
    ZIPPER_MOUTH = "🤐"
    ROFL = "🤣"
    WINK = "😉"

    # Other
    ROBOT = "🤖"
    ALIEN = "👽"
    SPY = "🕵️"
    PING_PONG = "🏓"
    ALARM = "⏰"
    TIMER = "⏲"
    CLIPBOARD = "📋"
    PAPERCLIP = "📎"
    SCROLL = "📜"
    COOKIE = "🍪"
    CHART_UP = "📈"
    CHART_DOWN = "📉"
    BAR_CHART = "📊"
    ENVELOPE = "✉"
    ENVELOPE_BLUE_ARROW = "📩"
    ENVELOPE_INCOMING = "📨"
    NOTEPAD_SPIRAL = "🗒️"
    INFORMATION_SOURCE = "ℹ"
    PENCIL = "📝"
    PENCIL_2 = "✏"
    CALENDAR = "📅"
    CALENDAR_SPIRAL = "🗓️"


# Singleton, which is why we instantiate is here
tr = TranslationManager()


def seconds_to_human_time(time_in_sec: int, language: str) -> str:
    """
    Converts time in seconds to a human-friendly representation.

    Args:
        time_in_sec: Time in seconds to convert.
        language: Language to use in the human-friendly representation.

    Returns:
        Human friendly-representation (string) of the time.

    """
    years = time_in_sec // (60 * 60 * 24 * 365)
    time_in_sec -= years * (60 * 60 * 24 * 365)

    days = time_in_sec // (60 * 60 * 24)
    time_in_sec -= days * (60 * 60 * 24)

    hours = time_in_sec // (60 * 60)
    time_in_sec -= hours * (60 * 60)

    minutes = time_in_sec // 60
    time_in_sec -= minutes * 60

    fields = []
    if years:
        fields.append(f"{years} {tr.get('TIME_YEARS', language)}")
    if days:
        fields.append(f"{days} {tr.get('TIME_DAYS', language)}")
    if hours:
        fields.append(f"{hours} {tr.get('TIME_HOURS', language)}")
    if minutes:
        fields.append(f"{minutes} {tr.get('TIME_MINUTES', language)}")

    # Remainder
    fields.append(f"{time_in_sec} {tr.get('TIME_SECONDS', language)}")

    return ", ".join(fields)


HUMAN_TIME_TO_UNIT = {
    "d": 60 * 60 * 24,
    "h": 60 * 60,
    "m": 60,
    "s": 1,
}


def human_time_to_seconds(string: str) -> int:
    """
    Converts a human time representation to seconds.
    Supported format: [<num>d] [<num>h] [<num>m] [<num>s]

    Args:
        string: Text to convert.

    Returns:
        Time representation converted to seconds.
    """
    # If already a number (assumed to be seconds), simply return the value as seconds
    if string.isnumeric():
        return int(string)

    # Process each unit
    group = string.split(" ")

    total_seconds = 0

    for element in group:
        try:
            value, unit = int(element[0:-1]), element[-1]
        except (IndexError, ValueError):
            # Conversion error
            continue
        else:
            # Use predefined conversion
            # (for example, minutes has the conversion 60)
            conversion = HUMAN_TIME_TO_UNIT.get(unit)
            if conversion:
                total_seconds += conversion * value

    return total_seconds


words = (
    "on",
    "enabled",
    "enable",
    "turn on",
    "true",
)


def matches_iterable(content: str, lst: Iterable = words) -> bool:
    return content.lower() in lst


def is_valid_command(msg: str, commands: Iterable, prefix: str):
    for cmd in commands:
        cmd = cmd.replace("_", prefix)

        if msg.startswith(cmd):
            return True

    return False


# BUG_FILE = os.path.join(DATA_DIR, "bugs.txt")
# LOG_FILE = os.path.join(DATA_DIR, "log.txt")
#
# # Verify the files exist so we can append to them
# if not os.path.isfile(BUG_FILE):
#     # Creates an empty file
#     with open(BUG_FILE, "w") as c:
#         pass
#
# if not os.path.isfile(LOG_FILE):
#     with open(LOG_FILE, "w") as c:
#        pass


def log_to_file(content, type_="log"):
    fn = BUG_FILE if type_ == "bug" else LOG_FILE

    with open(fn, "a") as file:
        cn = datetime.now().strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)

        try:
            file.write(cn + "\n")
        except UnicodeEncodeError:
            pass


def alternate_log(content: str, filename: str, append=True):
    with open(filename, "a" if append else "w") as file:
        cn = datetime.now().strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)

        try:
            file.write(cn + "\n")
        except UnicodeEncodeError:
            pass


none_ux = [
    "none", "false", "off", "disabled", "default", "disable"
]

ux_disables = {}

# Adds representations of None from other languages at import
for lng in tr.translations.keys():
    if lng not in ux_disables.keys():
        ux_disables[lng] = list(none_ux)

    th1 = tr.get("INFO_DISABLED", lng, fallback=False)
    th2 = tr.get("INFO_DISABLED_A", lng, fallback=False)

    if th1:
        ux_disables[lng].append(th1)
    if th2:
        ux_disables[lng].append(th2)


# Returns a bool indicating if 'ct' represents a disabling action
def is_disabled(ct, lang=DEFAULT_LANGUAGE):
    if ct is None or ct == "":
        return True

    ct = str(ct).lower()

    # Language-sensitive disabling
    for a in ux_disables[lang]:
        if ct.startswith(a):
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


def bin2bool(c) -> bool:
    """
    Converts a number (redis int response) to bool
    :param c: bytes/int
    """
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
    """
    Converts/decodes all kinds of types (mostly bytes) into their expected types
    """
    if isinstance(some, bytes):
        return decode_auto(some.decode())

    if isinstance(some, str):
        # Auto-convert numbers to int
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

    # If it's some other type, return it as is
    return some


def gen_id(length=38):
    """
    Not cryptographically safe, should only be used for IDs
    """
    return int(str(uuid.uuid4().int)[:length])


def chunks(item: list, n):
    """
    Generator, splits list into chunks
    """
    for i in range(0, len(item), n):
        yield item[i:i + n]


def add_dots(content, max_len=55, ending="[...]"):
    if not len(content) > max_len:
        return content
    else:
        # Make space for the ending as well
        max_len -= len(ending)

        return "{}".format(content[:max_len]) + ending


def is_number(string) -> bool:
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


def build_url(url, **fields) -> str:
    """
    Build an url with supplied dict of fields
    """
    if not url.endswith("?"):
        url += "?"

    field_list = ["{}={}".format(key, value) for key, value in fields.items()]
    return url + "&".join(field_list)


def apply_string_padding(strings: tuple, amount: int = 1):
    """
    Not available with standard .format

    :param amount: amount of padding left and right
    :param strings: iterable with strings to format
    :return: a tuple of inputted strings with applied formatting OR a string if length of strings is 1

    Example:

        strings: ["ayy", "some longer"]
        amount: 1
        >> [" ayy         ",
            " some longer "]
    """
    max_len = max([len(a) for a in strings])
    actual_padding = max_len + amount * 2

    empty_fill = amount * " "

    if len(strings) == 1:
        return empty_fill + strings[0] + empty_fill

    temp = []
    for s in strings:
        padd = actual_padding - (len(s) + 1)
        temp.append(empty_fill + s + padd * " ")

    return temp


def get_valid_commands(plugin):
    try:
        return list(plugin.commands.keys())
    except AttributeError:
        return None


USER_MENTION_REGEX = re.compile(r"<@[0-9]{18}>", re.MULTILINE)


def filter_text(text: str, mass_mentions: bool= True, user_mention: bool=True) -> str:
    """
    Removes all mentions in text
    """
    text = str(text)

    if mass_mentions:
        text = text.replace("@everyone", "@ everyone").replace("@here", "@ here")

    if user_mention:
        text = re.sub(
            USER_MENTION_REGEX,
            "==REDACTED MENTION==",
            text
        )

    return text
