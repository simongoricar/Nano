# coding=utf-8
import configparser
import json
import logging
import aiohttp

from data.confparser import get_config_parser

parser = get_config_parser()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class GuildCounter:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")

        try:
            self.botspw_token = parser.get("bots.discord.pw", "token")
            self.botsorg_token = parser.get("discordbots.org", "token")
        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Missing api key(s), disabling plugin...")
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

    async def upload(self, amount):
        a = await self.upload_discordbots_org(amount)
        b = await self.upload_discordbots_pw(amount)

        return a and b

    async def _send(self, url, payload, headers):
        session = await self.handle_session()

        async with session.post(url, data=json.dumps(payload), headers=headers) as resp:
            status_code = resp.status

        return True if status_code == 200 else status_code

    async def upload_discordbots_pw(self, num, token=None):
        if not token:
            token = self.botspw_token

        url = "https://bots.discord.pw/api/bots/{}/stats/".format(self.client.user.id)
        payload = {"server_count": num}
        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        return await self._send(url, payload, head)

    async def upload_discordbots_org(self, num, token=None):
        info = await self.client.application_info()

        if not token:
            token = self.botsorg_token

        url = "https://discordbots.org/api/bots/{}/stats".format(info.id)

        payload = {
            "server_count": num
        }

        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        return await self._send(url, payload, head)


class NanoPlugin:
    name = "Server count updater"
    version = "10"

    handler = GuildCounter
    events = {
        "on_guild_join": 9
    }
