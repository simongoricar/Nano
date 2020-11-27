# coding=utf-8
import configparser
import json
import logging
import aiohttp

from core.configuration import PARSER_CONFIG

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class GuildCounter:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")

        try:
            self.botspw_token = PARSER_CONFIG.get("discord.bots.gg", "token")
            self.botsorg_token = PARSER_CONFIG.get("discordbots.org", "token")
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
        b = await self.upload_discordbots_gg(amount)

        return a and b

    async def _send(self, url, payload, headers):
        session = await self.handle_session()

        async with session.post(url, data=json.dumps(payload), headers=headers) as resp:
            status_code = resp.status

        log.info("Sent server count to {} with status code {}".format(url, status_code))

        return True if status_code == 200 else status_code

    async def upload_discordbots_gg(self, num, token=None):
        if not token:
            token = self.botspw_token

        url = "https://discord.bots.gg/api/v1/bots/{}/stats/".format(self.client.user.id)
        payload = {"guildCount": num}
        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        return await self._send(url, payload, head)

    async def upload_discordbots_org(self, num, token=None):
        if not token:
            token = self.botsorg_token

        url = "https://discordbots.org/api/bots/{}/stats".format(self.client.user.id)

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
    version = "11"

    handler = GuildCounter
    events = {
        "on_guild_join": 9
    }
