# coding=utf-8

import logging
import asyncio
import os
import configparser
from discord import AutoShardedClient

os.chdir("..")

loop = asyncio.get_event_loop()
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

parser = configparser.ConfigParser()
parser.read("data/settings.ini")

client = AutoShardedClient(loop=loop)

IMAGE = input("What image would you like to upload?")

assert os.path.isfile(IMAGE)


@client.event
async def on_ready():
    print("Changing bot picture...")
    with open(IMAGE, "rb") as img:
        await client.user.edit(image=img.read())

    print("DONE!")


async def start():
    token = parser.get("Credentials", "token")

    await client.login(token)
    await client.connect()


def main():
    try:
        print("Connecting...")
        loop.run_until_complete(start())
    finally:
        print("Bye!")


if __name__ == '__main__':
    main()
