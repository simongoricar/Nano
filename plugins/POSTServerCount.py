# coding=utf-8
import aiohttp
import json
import configparser
import logging

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class POST:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")

        try:
            self.token = parser.get("bots.discord.pw", "token")
        except (configparser.NoOptionError, configparser.NoSectionError):
            log.critical("Missing api key for bots.discord.pw, disabling plugin...")
            raise RuntimeError

    async def on_server_join(self, server):
        amount = len(self.client.servers)

        resp = await self.upload(amount, token=self.token)

        if resp is True:
            log.info("Updated guild count: {} (joined {})".format(amount, server.name))
        else:
            log.info("Something went wrong when updating guild count: {} (for {}) - status code {}".format(amount, server.name, resp))

    async def upload(self, num, token=None):
        if not token:
            return False

        url = "https://bots.discord.pw/api/bots/:user_id/stats/".replace(":user_id", self.client.user.id)
        payload = {"server_count": num}
        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(payload), headers=head) as resp:
                status_code = resp.status

        return True if status_code == 200 else status_code


class NanoPlugin:
    name = "POST module for bots.discord.pw"
    version = "0.2"

    handler = POST
    events = {
        "on_server_join": 9
    }
