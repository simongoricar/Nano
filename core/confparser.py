# coding=utf-8
import os
import json
import configparser

############
# CONFIG PARSER
############

with open("core/directories.json") as file:
    dir_locations = json.loads(file.read())
    if not dir_locations:
        dir_locations = {}

PLUGINS_DIR = dir_locations.get("plugins", "plugins/")
CACHE_DIR = dir_locations.get("cache", "cache/")
DATA_DIR = dir_locations.get("data", "data/")
BACKUP_DIR = dir_locations.get("backup", "backup/")

SETTINGS_FILE = "settings.ini"
CONFIG_FILE = "config.ini"

SETTINGS = os.path.join(DATA_DIR, SETTINGS_FILE)
SETTINGS_EXAMPLE = SETTINGS + ".example"
CONFIG = os.path.join(DATA_DIR, CONFIG_FILE)
CONFIG_EXAMPLE = CONFIG + ".example"

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
if not os.path.isfile(SETTINGS):
    must_shutdown = True
    print("No settings.ini present! Please fill out the empty one!")

    with open(SETTINGS_EXAMPLE) as ex:
        with open(SETTINGS_FILE, "w") as sett:
            sett.write(ex.read())


if not os.path.isfile(CONFIG):
    must_shutdown = True
    print("No plugins/config.ini present! Please fill out the empty one!")

    with open(CONFIG_EXAMPLE) as ex:
        with open(PLUGIN_CONFIG_PATH, "w") as sett:
            sett.write(ex.read())


if must_shutdown:
    exit(6)


# SETS UP BASIC PARSERS

# settings.ini
settings_parser = configparser.ConfigParser()

if not os.path.isfile(SETTINGS):
    raise FileNotFoundError("Missing {} in base directory!".format(SETTINGS))
settings_parser.read(SETTINGS)

parsers["settings"] = settings_parser


# plugins/config.ini
config_parser = configparser.ConfigParser()

if not os.path.isfile(CONFIG):
    raise FileNotFoundError("Missing {} in plugins directory!".format(CONFIG))
config_parser.read(CONFIG)

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
