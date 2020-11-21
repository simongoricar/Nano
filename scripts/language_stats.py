# coding=utf-8

# Change current directory to the root
import os
os.chdir("..")

import time
import logging
import asyncio
import configparser
from redis import StrictRedis

try:
    from rapidjson import dump
except ImportError:
    from json import dump

from core.serverhandler import ServerHandler
from core.utils import decode
from core.translations import TranslationManager

#########################################
# Language Statistics
# This script goes through all joined servers and extracts which languages are used for Nano
# Supports exporting data to json
#########################################

log = logging.getLogger(__name__)

parser = configparser.ConfigParser()
parser.read("settings.ini")

print("---------------------------")
print("Language Statistics utility")
print("---------------------------")

# Store time to display time taken at the end
init = time.monotonic()

# Parse languages
print("Parsing available languages...")
trans = TranslationManager()

languages = [l for l in trans.meta.keys()]
print(f"Current languages: {', '.join(languages)}")

# Connect to redis db
print("Connecting to redis...")
red: StrictRedis = ServerHandler.get_handler(asyncio.get_event_loop()).redis

print("Iterating though servers...")

server_count: int = 0
language_use: dict = {a: 0 for a in languages}

for s in red.scan_iter(match="server:*"):
    raw_key: str = decode(s)
    server_id: int = int(raw_key.split(":")[1])

    server_lang: str = decode(red.hget(raw_key, "lang"))
    print(f"Found server: {server_id} with language: '{server_lang}'")

    if server_lang is None:
        language_use["en"] += 1
    else:
        if "-" in server_lang:
            l, r = server_lang.split("-", maxsplit=1)
            server_lang = f"{l}_{r.upper()}"

        language_use[server_lang.replace("-", "_")] += 1

    server_count += 1

print(f"Done! Iterated though {server_count} servers.")

formatted = "\n".join([f'{l} - {v} servers' for l, v in language_use.items()])
print(f"Statistics:\n{formatted}")

# Ask to export results
inp = input("Do you want to export the results to a file? Y/n")
if inp.lower() == "y":
    payload = {"total": server_count,
               "per_language": language_use}


    tm = time.strftime("%d_%m_%y-%H_%M_%S", time.localtime())
    filename = f"utilities/statistics/languages{tm}.json"
    with open(filename, "w") as export:
        dump(payload, export)

    print(f"Exported to {filename}.")
