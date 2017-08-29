# coding=utf-8
import os
import configparser

############
# CONFIG PARSER
############

PLUGINS_DIR = "plugins"

SETTINGS_FILE = "settings.ini"
CONFIG_FILE = "config.ini"

PLUGIN_CONFIG_PATH = os.path.join(PLUGINS_DIR, CONFIG_FILE)

# Allows for extensibility
parsers = {}


# SETS UP BASIC PARSERS

# settings.ini
settings_parser = configparser.ConfigParser()

if not os.path.isfile(SETTINGS_FILE):
    raise FileNotFoundError("Missing {} in base directory!".format(SETTINGS_FILE))
settings_parser.read(SETTINGS_FILE)

parsers["settings"] = settings_parser


# plugins/config.ini
config_parser = configparser.ConfigParser()

if not os.path.isfile(PLUGIN_CONFIG_PATH):
    raise FileNotFoundError("Missing {} in plugins directory!".format(CONFIG_FILE))
config_parser.read(PLUGIN_CONFIG_PATH)

parsers["config"] = config_parser


def get_parser(name: str) -> configparser.ConfigParser:
    if name.endswith(".ini"):
        name = name.rstrip(".ini")

    return parsers[name]


def new_parser(path: str, name: str) -> configparser.ConfigParser:
    if name in parsers.keys():
        return get_parser(name)

    parser = configparser.ConfigParser()

    if not os.path.isfile(path):
        raise FileNotFoundError("Configuration file missing: {}".format(path))

    parser.read(path)

    parsers[name] = parser


# Syntactic sugar for get_parser
def get_settings_parser() -> configparser.ConfigParser:
    return settings_parser


def get_config_parser() -> configparser.ConfigParser:
    return config_parser
