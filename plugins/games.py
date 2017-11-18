# coding=utf-8
import configparser
import aiohttp
import logging

try:
    from ujson import loads, dumps
except ImportError:
    from json import loads, dumps
from discord import Embed

from data.utils import is_valid_command, build_url
from data.confparser import get_config_parser
from data.stats import MESSAGE

commands = {
    "_gamedb": {"desc": "Looks up information on all kinds of video games.\nUses https://www.igdb.com"},
}

valid_commands = commands.keys()

parser = get_config_parser()
log = logging.getLogger(__name__)


class Game:
    __slots__ = ("id", "name", "summary", "genres", "publishers", "rating", "cover_image", "video")

    def __init__(self, **fields):
        self.id = fields.get("id")
        self.name = fields.get("name")

        self.summary = fields.get("summary")
        self.genres = [a["name"] for a in fields.get("genres")]
        self.publishers = [a["name"] for a in fields.get("publishers")]
        self.rating = fields.get("total_rating")

        cover = fields.get("cover")
        if cover:
            self.cover_image = Igdb.IMAGES.format(size="cover_big", id=cover.get("cloudinary_id"))
        else:
            self.cover_image = None

        videos = fields.get("videos")
        if videos:
            self.video = Igdb.VIDEO.format(videos[0]["video_id"])
        else:
            self.video = None


class Igdb:
    GAMES = "https://api-2445582011268.apicast.io/games/"
    IMAGES = "https://images.igdb.com/igdb/image/upload/t_{size}/{id}.jpg"
    VIDEO = "https://www.youtube.com/watch?v={}"

    def __init__(self, api_key: str):
        # TODO caching
        self.key = api_key

        self.session = aiohttp.ClientSession()

    async def _request(self, url: str, fields: dict):
        url = build_url(url, **fields)
        headers = {
            "user-key": self.key,
            "Accept": "application/json"
        }

        async with self.session.get(url, headers=headers) as resp:
            return await resp.json(loads=loads, content_type=None)

    async def get_game_by_name(self, name: str):
        payload = {
            "search": name,
            "fields": "name,publishers,summary,total_rating,genres,cover,videos",
            "expand": "genres,publishers",
            "limit": 1
        }

        resp = await self._request(Igdb.GAMES, payload)
        if len(resp) < 1:
            raise ValueError("unexpected: resp has length {}".format(len(resp)))

        game_obj = Game(**resp[0])

        return game_obj


class GameDB:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        try:
            gamedb_key = parser.get("igdb", "api-key")
        except (configparser.NoSectionError, configparser.NoOptionError):
            log.critical("Missing api key for Igdb, disabling plugin...")
            raise RuntimeError

        self.gamedb = Igdb(gamedb_key)

    async def on_message(self, message, **kwargs):
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # !gamedb [name]
        if startswith(prefix + "gamedb"):
            game_name = message.content[len(prefix + "gamedb "):]

            if not game_name:
                await message.channel.send(trans.get("MSG_IGDB_NONAME", lang))
                return


            game = await self.gamedb.get_game_by_name(game_name)

            embed = Embed(title=":video_game: **{}**".format(game.name), description=game.summary)
            embed.set_image(url=game.cover_image)

            genres = " ".join(["`{}`".format(a) for a in game.genres])
            embed.add_field(name=trans.get("MSG_IGDB_GENRES", lang), value=genres)
            publishers = " ".join(["`{}`".format(a) for a in game.publishers])
            embed.add_field(name=trans.get("MSG_IGDB_PUBLISHERS", lang), value=publishers)

            if game.rating:
                rating = "{} / 100".format(int(game.rating))
                embed.add_field(name=trans.get("MSG_IGDB_RATING", lang), value=rating)

            if game.video:
                embed.add_field(name=trans.get("MSG_IGDB_VIDEO", lang), value=game.video)

            embed.set_footer(text="Powered by idgb.com")

            await message.channel.send(embed=embed)


class NanoPlugin:
    name = "Game Database"
    version = "1"

    handler = GameDB
    events = {
        "on_message": 10,
        # type : importance
    }
