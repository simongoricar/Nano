# coding=utf-8
import configparser
import aiohttp
import logging
from fuzzywuzzy import process, fuzz

try:
    from rapidjson import loads, dumps
except ImportError:
    from json import loads, dumps
from discord import Embed

from core.utils import is_valid_command, build_url
from core.configuration import PARSER_CONFIG
from core.stats import MESSAGE

commands = {
    "_gamedb": {"desc": "Looks up information on all kinds of video games.\nUses https://www.igdb.com"},
}
valid_commands = commands.keys()

log = logging.getLogger(__name__)


class Game:
    def __init__(self, **fields):
        self.id = fields.get("id")
        self.name = fields.get("name")
        self.url = fields.get("url")

        self.summary = fields.get("summary")
        # Optimized for parsing
        self.genres = "|".join([a["name"] for a in fields.get("genres", [])]) or None
        self.publishers = "|".join([a["name"] for a in fields.get("publishers", [])]) or None

        self.rating = int(fields.get("total_rating")) if fields.get("total_rating") else None

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


class GameCompat:
    __slots__ = ("id", "name", "summary", "genres", "publishers", "rating", "cover_image", "video", "url", "_fields")

    def __init__(self, fields):
        self._fields = fields

        # Parse strings split by |
        if fields.get("genres"):
            self._fields["genres"] = fields.get("genres").split("|")

        if fields.get("publishers"):
            self._fields["publishers"] = fields.get("publishers").split("|")

    def __getattr__(self, item):
        return self._fields[item]


class IgdbCacheManager:
    """
    Layout:
        namespace: games
        type: hash

            games:ID
                hash fields with all
    """
    def __init__(self, handler):
        self._cache = handler.get_cache_handler().get_plugin_data_manager("games")

        self._tmp_names = {}
        self._fill_name_cache()

    def _fill_name_cache(self):
        """
        Fills the local name cache with entries already present in the database
        """
        games = self._cache.scan_iter("*")

        for id_ in games:
            name = self._cache.hget(id_, "name", use_namespace=False)

            self._tmp_names[name] = id_.split(":")[1]

        log.info("Local name cache updated with {} entries".format(len(games)))

    def exists_in_cache(self, id_):
        return self._cache.exists(id_)

    def _get(self, id_):
        obj = self._cache.hgetall(id_)
        if not obj:
            for name, g_id in list(self._tmp_names.items()):
                if g_id == id_:
                    del self._tmp_names[name]
                    log.debug("Game object was invalid, removed")

            return None

        return obj

    def get_by_id(self, id_):
        return self._get(id_)

    def get_by_name(self, name):
        compares = self._tmp_names.keys()
        if not compares:
            return None

        highest, score = process.extractOne(name, compares, scorer=fuzz.partial_token_sort_ratio)

        if score > 85:
            return self._get(self._tmp_names[highest])
        else:
            return None

    def add_to_cache(self, item: Game):
        id_ = item.id
        # 1 Day of cache
        ttl = 60 * 60 * 24

        # Add to local "cache"
        self._tmp_names[item.name] = item.id

        # item = {**item, **{"timestamp": ttl}}

        pipe = self._cache.pipeline()

        pipe.hmset("games:{}".format(id_), item.__dict__)
        pipe.expire("games:{}".format(id_), ttl)

        pipe.execute()
        log.info("Added new game to cache")


class Igdb:
    GAMES = "https://api-2445582011268.apicast.io/games/"
    IMAGES = "https://images.igdb.com/igdb/image/upload/t_{size}/{id}.jpg"
    VIDEO = "https://youtu.be/{}"

    def __init__(self, api_key: str, handler, loop):
        self.key = api_key
        self.cache = IgdbCacheManager(handler)

        self.session = aiohttp.ClientSession(loop=loop)

    async def _request(self, url: str, fields: dict):
        url = build_url(url, **fields)
        headers = {
            "user-key": self.key,
            "Accept": "application/json"
        }

        async with self.session.get(url, headers=headers) as resp:
            return await resp.json(loads=loads, content_type=None)

    async def get_game_by_name(self, name: str):
        a = self.cache.get_by_name(name)
        if a is not None:
            return GameCompat(a)


        payload = {
            "search": name,
            "fields": "name,publishers,summary,total_rating,genres,cover,videos,url",
            "expand": "genres,publishers",
            "limit": 1
        }

        resp = await self._request(Igdb.GAMES, payload)
        # No result
        if len(resp) < 1:
            return None

        game_obj = Game(**resp[0])
        self.cache.add_to_cache(game_obj)

        return GameCompat(game_obj.__dict__)


class GameDB:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")
        self.loop = kwargs.get("loop")

        try:
            gamedb_key = PARSER_CONFIG.get("igdb", "api-key")
        except (configparser.NoSectionError, configparser.NoOptionError):
            log.critical("Missing api key for Igdb, disabling plugin...")
            raise RuntimeError

        self.gamedb = Igdb(gamedb_key, self.handler, self.loop)

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
            if not game:
                await message.channel.send(trans.get("MSG_IGDB_NO_RESULT", lang))
                return

            if game.summary:
                embed = Embed(description=game.summary)
            else:
                embed = Embed(description=trans.get("MSG_IGDB_NO_SUMMARY", lang))

            if game.cover_image:
                embed.set_image(url=game.cover_image)
            embed.set_author(name=game.name, url=game.url)

            if game.genres:
                genres = " ".join(["`{}`".format(a) for a in game.genres])
                embed.add_field(name=trans.get("MSG_IGDB_GENRES", lang), value=genres)
            if game.publishers:
                publishers = " ".join(["`{}`".format(a) for a in game.publishers])
                embed.add_field(name=trans.get("MSG_IGDB_PUBLISHERS", lang), value=publishers, inline=False)

            if game.rating:
                rating = "{} / 100".format(int(game.rating))
                embed.add_field(name=trans.get("MSG_IGDB_RATING", lang), value=rating, inline=False)

            if game.video:
                embed.add_field(name=trans.get("MSG_IGDB_VIDEO", lang), value=game.video, inline=False)

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
