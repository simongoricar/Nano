# coding=utf-8
import time
import logging
import asyncio
import os
import sys
import configparser

os.chdir("..")

from core.serverhandler import ServerHandler, server_defaults
from core.utils import decode

#########################################
# Cleanup
# This script cleans up the database of unneeded entries
#########################################

log = logging.getLogger(__name__)

parser = configparser.ConfigParser()
parser.read("settings.ini")

print("-------------------------")
print("REDIS DB CLEANUP UTILITY")
print("-------------------------")

if input("This script will remove unwanted keys from the database "
         "(obsolete / deprecated ones).\nDo you want to proceed? (y/n) ").lower() == "n":
    sys.exit(4)

if input("Do you want to display every removed key? (y/n) ").lower() == "y":
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


init = time.monotonic()

print("Verifying server data...")
red = ServerHandler.get_handler(asyncio.get_event_loop())

config_keys = list(server_defaults.keys())

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
