# coding=utf-8
import logging
from typing import Union
from json import loads
from xml.etree import ElementTree

log = logging.getLogger(__name__)


# To avoid circular import from utils.py
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


DEFAULT_LANGUAGE = "en"

# Handle some string in a different way

strings_to_list = [
    # Used in conversation.py
    "CONV_Q_SLEEP",
    "CONV_MOOD_LIST",
    "CONV_Q_HOW",
    "CONV_Q_HELLO",
    "CONV_Q_AYY",
    "CONV_Q_RIP",
    "CONV_Q_MASTER",
    "CONV_Q_MAKER",

]

# required by .startswith
strings_to_tuple = [
    # Used in admin.py for nano.settings
    "MSG_SETTINGS_WF_OPTIONS",
    "MSG_SETTINGS_SF_OPTIONS",
    "MSG_SETTINGS_IF_OPTIONS"

]



# Lower the strings (no performance impact, is done once at runtime)
strings_to_list = [a.lower() for a in strings_to_list]
strings_to_tuple = [a.lower() for a in strings_to_tuple]


def split_into_list(something: str) -> list:
    return [a.strip(" ") for a in something.split("|")]


def split_into_tuple(something: str) -> tuple:
    return tuple(a.strip(" ") for a in something.split("|"))


def get_meta() -> dict:
    with open("translations/meta.json") as meta:
        d = meta.read()
        if not d:
            raise RuntimeError("meta.json is empty")

        return loads(d)


class TranslationManager(metaclass=Singleton):
    __slots__ = (
        "meta", "translations", "default_lang"
    )

    def __init__(self):
        self.meta = {}
        self.translations = {}

        self.default_lang = DEFAULT_LANGUAGE

        self.reload_translations()

    def load_languages(self):
        for lang in self.meta.keys():
            log.info("Loading {}.xml".format(lang))
            etree = ElementTree.parse("translations/{}.xml".format(lang))

            xml_dict = self.parse_xml_to_dict(etree)

            if type(xml_dict) is not dict:
                raise TypeError("expected dict, got {}".format(type(xml_dict)))

            self.translations[lang] = xml_dict

        log.info("Parsed {} languages: {}".format(len(self.meta.keys()), ",".join(self.meta.keys())))
        self.parse_special_strings()

    def parse_special_strings(self):
        if not self.translations:
            raise RuntimeError("Translations are not yet loaded!")

        c = 0

        for lang, words in self.translations.items():
            specials = {}

            for name, string in words.items():

                if name in strings_to_list:
                    # Parse: split the string into a list
                    specials[name] = split_into_list(string)
                    c += 1
                elif name in strings_to_tuple:
                    # Parse: split the string into a tuple
                    specials[name] = split_into_tuple(string)
                    c += 1

            # Overwrite existing dictionary with parsed strings
            if specials:
                self.translations[lang].update(specials)

        log.info("Parsed {} special strings".format(c))

    @staticmethod
    def parse_xml_to_dict(tree: ElementTree) -> dict:
        tree = tree.getroot()

        buffer = {}
        for child in tree:
            # Ignore other tags
            if child.tag != "string":
                continue

            name = child.attrib.get("name")

            # Ignore entries without name
            if not name:
                continue

            if name.lower() in buffer.keys():
                log.warning("{} already exists!".format(name))

            buffer[name.lower()] = child.text

        return buffer

    def get(self, name: str, lang=DEFAULT_LANGUAGE, fallback=True) -> str:
        if not lang:
            lang = DEFAULT_LANGUAGE

        name = name.lower()
        item = self.translations.get(lang)

        # Fall back to english
        if not item:
            item = self.translations.get("en")

        trans = item.get(name)
        if not trans and fallback:
            # Fall back to english, again
            trans = self.translations.get("en").get(name)
            # Emergency
            if not trans:
                return "Please notify the dev, something went wrong (translation missing): {}".format(name)

        return trans

    def is_language_code(self, language_code) -> bool:
        return language_code in self.meta.keys()

    def find_language_code(self, language_name) -> Union[str, None]:
        for c, details in self.meta.items():
            if details.get("name") == language_name:
                return c

        return None

    def reload_translations(self):
        self.meta = get_meta()
        self.load_languages()
