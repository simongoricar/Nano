# coding=utf-8
import logging
from typing import Union
from json import loads
from xml.etree import ElementTree

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# To avoid circular import from utils.py
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


DEFAULT_LANGUAGE = "en"

def get_meta() -> dict:
    with open("translations/meta.json", "r") as meta:
        d = meta.read()
        if not d:
            raise RuntimeError("meta.json is empty")

        return loads(d)


class TranslationManager(metaclass=Singleton):
    __slots__ = (
        "meta", "translations", "default_lang"
    )

    def __init__(self):
        self.meta = get_meta()

        self.translations = {}
        self.default_lang = DEFAULT_LANGUAGE

        self.parse_languages_from_meta()

    def parse_languages_from_meta(self):
        for lang in self.meta.keys():
            etree = ElementTree.parse("translations/{}.xml".format(lang))

            xml_dict = self.parse_xml_to_dict(etree)

            if type(xml_dict) is not dict:
                raise TypeError("expected dict, got {}".format(type(xml_dict)))

            self.translations[lang] = xml_dict

        log.info("Parsed {} languages: {}".format(len(self.meta.keys()), ",".join(self.meta.keys())))

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

    def get(self, name: str, lang=DEFAULT_LANGUAGE) -> str:
        if not lang:
            lang = DEFAULT_LANGUAGE

        name = name.lower()
        item = self.translations.get(lang)

        # Fall back to english
        if not item:
            item = self.translations.get("en")

        trans = item.get(name)
        if not trans:
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
        self.parse_languages_from_meta()
