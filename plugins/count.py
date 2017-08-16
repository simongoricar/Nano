# coding=utf-8
import configparser
import json
import logging

import aiohttp

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class POST:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")

        try:
            self.token = parser.get("bots.discord.pw", "token")
        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Missing api key for bots.discord.pw, disabling plugin...")
            raise RuntimeError

        self.session = None

    async def handle_session(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession(loop=self.loop)

        return self.session

    async def on_guild_join(self, guild, **_):
        srv_amount = len(self.client.guilds)

        resp = await self.upload(srv_amount)

        if resp is True:
            log.info("Updated guild count: {} (joined {})".format(srv_amount, guild.name))
        else:
            log.info("Something went wrong when updating guild count: {} (for {}) - status code {}".format(srv_amount, guild.name, resp))

    async def upload(self, num, token=None):
        if not token:
            token = self.token

        url = "https://bots.discord.pw/api/bots/{}/stats/".format(self.client.user.id)
        payload = {"server_count": num}
        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        session = await self.handle_session()

        async with session.post(url, data=json.dumps(payload), headers=head) as resp:
            status_code = resp.status

        return True if status_code == 200 else status_code


class NanoPlugin:
    name = "POST module for bots.discord.pw"
    version = "9"

    handler = POST
    events = {
        "on_guild_join": 9
    }
