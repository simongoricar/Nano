# coding=utf-8
import time
import logging
import sys
import configparser
from data.serverhandler import ServerHandler, server_defaults
from data.utils import decode

#########################################
# Cleanup
# This script cleans up the database of unneeded entries
#########################################

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

parser = configparser.ConfigParser()
parser.read("settings.ini")

print("-------------------------")
print("REDIS DB CLEANUP UTILITY")
print("-------------------------")

if input("This script will remove unwanted keys from the database (obsolete / deprecated ones).\nDo you want to proceed? (y/n) ").lower() == "n":
    sys.exit(4)

if not parser.get("Storage", "type") == "redis":
    print("Storage type is not set to redis, please change to continue (settings.ini)")
    sys.exit(2)


init = time.monotonic()

print("Verifying server data...")
red = ServerHandler.get_handler()

config_keys = server_defaults.keys()

c = 0

for server in red.redis.scan_iter(match="server:*"):
    server = decode(server)

    fields = decode(red.redis.hgetall(server))
    for key, value in fields.items():
        if key not in config_keys:
            log.debug("Clearing key: {}".format(key))
            red.redis.hdel(server, key)

            c += 1

if c != 0:
    print("Done, {} entries fixed.".format(c))
else:
    print("Done, no obsolete keys.")
