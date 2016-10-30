# coding=utf-8
import requests
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

    async def on_server_join(self, server):
        amount = len(self.client.servers)
        token = parser.get("bots.discord.pw", "token")

        self.upload(amount, token)
        log.info("Updated guild count: {} (joined {})".format(amount, server.name))

    @staticmethod
    def upload(num, token):
        url = "https://bots.discord.pw/api/bots/:user_id/stats/".replace(":user_id", "171633949532094464")
        payload = {"server_count": num}
        head = {
            "Content-Type": "application/json",
            "Authorization": str(token)
        }

        requests.post(url, data=json.dumps(payload), headers=head)
        return True


class NanoPlugin:
    _name = "POST module for bots.discord.pw"
    _version = 0.1

    handler = POST
    events = {
        "on_server_join": 9
    }
