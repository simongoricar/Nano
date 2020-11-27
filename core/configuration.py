import logging
import os
import json
import configparser

from .exceptions import MissingConfigurationException

log = logging.getLogger(__name__)

DIRECTORIES_JSON_FILE = os.path.abspath("./core/directories.json")

try:
    log.debug(f"Loading \"{DIRECTORIES_JSON_FILE}\" ...")
    with open(DIRECTORIES_JSON_FILE) as file:
        dir_locations = json.load(file)
except FileNotFoundError:
    raise MissingConfigurationException("Missing directories.json file! Are you sure your install is correct?")

# Directories
DIR_DATA = os.path.abspath(dir_locations.get("data", default="./data/"))
DIR_PLUGINS = os.path.abspath(dir_locations.get("plugins", default="./data/plugins/"))
DIR_CACHE = os.path.abspath(dir_locations.get("cache", default="./data/cache/"))
DIR_BACKUP = os.path.abspath(dir_locations.get("backup", default="./data/backup/"))

# Configuration files
# TODO merge settings.ini and config.ini, or make them per-plugin
SETTINGS_INI_NAME = "settings.ini"
SETTINGS_INI_EXAMPLE_NAME = "settings.ini.example"

CONFIG_INI_NAME = "config.ini"
CONFIG_INI_EXAMPLE_NAME = "config.ini.example"

SETTINGS_INI_PATH = os.path.abspath(os.path.join(DIR_DATA, SETTINGS_INI_NAME))
SETTINGS_INI_EXAMPLE_PATH = os.path.abspath(os.path.join(DIR_DATA, SETTINGS_INI_EXAMPLE_NAME))

CONFIG_INI_PATH = os.path.abspath(os.path.join(DIR_DATA, CONFIG_INI_NAME))
CONFIG_INI_EXAMPLE_PATH = os.path.abspath(os.path.join(DIR_DATA, CONFIG_INI_EXAMPLE_NAME))

PLUGIN_CONFIG_PATH = os.path.abspath(os.path.join(DIR_PLUGINS, CONFIG_INI_NAME))

# Bug and log file
BUGS_NAME = "bugs.txt"
LOG_NAME = "log.txt"

BUG_FILE_PATH = os.path.abspath(os.path.join(DIR_DATA, BUGS_NAME))
LOG_FILE_PATH = os.path.abspath(os.path.join(DIR_DATA, LOG_NAME))

log.info(
    f"""Configuration paths loaded:
\t-- Directories --
\t\tData directory: \"{DIR_DATA}\"
\t\tPlugins directory: \"{DIR_PLUGINS}\"
\t\tCache directory: \"{DIR_CACHE}\"
\t\tBackup directory: \"{DIR_BACKUP}\"
\t\tBackup directory: \"{DIR_BACKUP}\"
\t-- Files --
\t\t{SETTINGS_INI_NAME}: \"{SETTINGS_INI_PATH}\"
\t\t{CONFIG_INI_NAME}: \"{CONFIG_INI_PATH}\"
\t\t{BUGS_NAME}: \"{BUG_FILE_PATH}\"
\t\t{LOG_NAME}: \"{LOG_FILE_PATH}\"
"""
)


##
# Validate directories
##

# The plugins directory must exist
if not os.path.isdir(DIR_PLUGINS):
    raise MissingConfigurationException("Plugins directory is missing!")

# Directories like the cache and backup one will be created automatically
if not os.path.isdir(DIR_DATA):
    os.mkdir(DIR_DATA)
    log.info("Data directory '{}' was missing, created.".format(DIR_DATA))

if not os.path.isdir(DIR_CACHE):
    os.mkdir(DIR_CACHE)
    log.info("Cache directory '{}' was missing, created.".format(DIR_CACHE))

if not os.path.isdir(DIR_BACKUP):
    os.mkdir(DIR_BACKUP)
    log.info("Backup directory '{}' was missing, created.".format(DIR_BACKUP))

##
# Parsers
# config.ini and settings.ini
##
# If needed, copy the example files
if not os.path.isfile(SETTINGS_INI_PATH):
    raise MissingConfigurationException(
        "settings.ini not found. Please create the file, using settings.ini.example as a guide."
    )

if not os.path.isfile(CONFIG_INI_PATH):
    raise MissingConfigurationException(
        "config.ini not found. Please create the file, using config.ini.example as a guide."
    )


# settings.ini
PARSER_SETTINGS = configparser.ConfigParser()
PARSER_SETTINGS.read(SETTINGS_INI_PATH)

# config.ini
PARSER_CONFIG = configparser.ConfigParser()
PARSER_CONFIG.read(CONFIG_INI_PATH)

##
# Set up bug and log files
##

# If the files don't already exist, create empty ones
if not os.path.isfile(BUG_FILE_PATH):
    # Creates an empty file
    open(BUG_FILE_PATH, "w").close()

if not os.path.isfile(LOG_FILE_PATH):
    # Create an empty file
    open(LOG_FILE_PATH, "w").close()
