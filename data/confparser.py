# coding=utf-8
import os
import configparser

############
# CONFIG PARSER
############

PLUGINS_DIR = "plugins"
CACHE_DIR = "cache"
BACKUP_DIR = "backup"

SETTINGS_FILE = "settings.ini"
CONFIG_FILE = "config.ini"

PLUGIN_CONFIG_PATH = os.path.join(PLUGINS_DIR, CONFIG_FILE)


# Folder checks
if not os.path.isdir(PLUGINS_DIR):
    raise LookupError("missing plugins directory!")

if not os.path.isdir(CACHE_DIR):
    os.mkdir(CACHE_DIR)
    print("Directory '{}' was missing, created.".format(CACHE_DIR))

if not os.path.isdir(BACKUP_DIR):
    os.mkdir(BACKUP_DIR)
    print("Directory '{}' was missing, created.".format(BACKUP_DIR))

# Allows for extensibility
parsers = {}

# COPIES FILES IF NEEDED
must_shutdown = False
if not os.path.isfile(SETTINGS_FILE):
    must_shutdown = True
    print("No settings.ini present! Please fill out the empty one!")

    with open("settings.ini.example") as ex:
        with open(SETTINGS_FILE, "w") as sett:
            sett.write(ex.read())


if not os.path.isfile(PLUGIN_CONFIG_PATH):
    must_shutdown = True
    print("No plugins/config.ini present! Please fill out the empty one!")

    with open(os.path.join(PLUGINS_DIR, "config.ini.example")) as ex:
        with open(PLUGIN_CONFIG_PATH, "w") as sett:
            sett.write(ex.read())


if must_shutdown:
    exit(6)


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
