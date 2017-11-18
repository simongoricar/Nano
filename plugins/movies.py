# coding=utf-8
import configparser
import logging
import time

# External library available here: https://github.com/DefaltSimon/TMDbie
import tmdbie
from discord import errors
from typing import Union

from data.stats import MESSAGE
from data.utils import is_valid_command, IgnoredException
from data.confparser import get_config_parser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = get_config_parser()

commands = {
    "_imdb search": {"desc": "Searches for a film/series/person and displays general info", "use": "[command] [film/series title]", "alias": "_tmdb search"},
    "_imdb trailer": {"desc": "Gives you a link to the trailer of a film/series.", "use": "[command] [film/series title]", "alias": "_tmdb trailer"},
    "_imdb plot": {"desc": "Displays more plot info about a film/series.", "use": "[command] [film/series title]", "alias": "_tmdb plot"},
    "_imdb rating": {"desc": "Displays different ratings for the film/series.", "use": "[command] [film/series title]", "alias": "_tmdb rating"},
    "_imdb help": {"desc": "Displays available commands regarding IMDb.", "use": "[command]", "alias": "_tmdb help"},
    "_imdb": {"desc": "Displays all kinds of film/series info. (Powered by https://www.themoviedb.org)\nSubcommands: `search` `trailer` `plot` `rating` `help`", "use": "[command] [subcommand] OR [command] [film/series title (shortcut for search)]"},
    "_tmdb": {"desc": "Displays all kinds of film/series info. (Powered by https://www.themoviedb.org)\nSubcommands: `search` `trailer` `plot` `rating` `help`", "use": "[command] [subcommand] OR [command] [film/series title (shortcut for search)]"},
}

valid_commands = commands.keys()


class ObjectCompat:
    __slots__ = (
        "fields",
    )

    def __init__(self, **fields):
        self.fields = fields

        if "genres" in fields:
            self.fields["genres"] = fields["genres"].split("|")

    def __getattr__(self, item):
        return self.fields[item]


class RedisMovieCache:
    __slots__ = (
        "cache", "max_age"
    )

    def __init__(self, handler, max_age=21600):
        cache = handler.get_cache_handler()
        self.cache = cache.get_plugin_data_manager("movies")

        self.max_age = max_age

    def _is_valid(self, id_):
        """
        Checks timestamps to see if the definition is valid
        """
        if not self.cache.exists(id_):
            return False

        timestamp = float(self.cache.hget(id_, "timestamp"))
        return (time.time() - timestamp) < self.max_age

    def get_item_by_name(self, name):
        query = str(name).lower()

        if self.cache.hexists("by_name", query):
            return None

        raw = self.cache.hget("by_name", name)
        if not self._is_valid(raw):
            return None

        # Item exists, get it from redis cache
        item = self.cache.hgetall(raw)
        return ObjectCompat(**item)

    def get_item_by_id(self, id_):
        if not self._is_valid(id_):
            return None

        # Item exists, get it from redis cache
        item = self.cache.hgetall(id_)
        return ObjectCompat(**item)

    def get_from_cache(self, query):
        if not query:
            return None

        try:
            int(query)
        except ValueError:
            # Query is a name
            return self.get_item_by_name(query)
        else:
            # Query is a number
            return self.get_item_by_id(query)

    @staticmethod
    def _get_properties(obj):
        return {s: getattr(obj, s) for s in obj.__slots__ if hasattr(obj, s)}

    def item_set(self, item):
        """
        Puts the item into cache
        """
        payload = {**self._get_properties(item), **{"timestamp": time.time()}}

        if "genres" in payload.keys():
            payload.update({"genres": "|".join(payload["genres"])})

        self.cache.hmset(payload["id"], payload)

        # self.by_name[payload["title"].lower()] = payload["id"]
        self.cache.hset("by_name", payload["title"].lower(), payload["id"])

        log.info("Added new item to cache")



class TMDb:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.handler = kwargs.get("handler")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        try:
            redis_cache = RedisMovieCache(self.handler)
            self.tmdb = tmdbie.Client(api_key=parser.get("tmdb", "api-key"), cache_manager=redis_cache)
        except (configparser.NoSectionError, configparser.NoOptionError):
            log.critical("Missing api key for tmdb, disabling plugin...")
            raise RuntimeError

    async def _imdb_search(self, name, message, lang) -> Union[tmdbie.Movie, tmdbie.TVShow, tmdbie.Person]:
        if not name:
            await message.channel.send(self.trans.get("MSG_IMDB_NEED_TITLE", lang))
            raise IgnoredException

        try:
            data = await self.tmdb.search_multi(name)
        except tmdbie.TMDbException:
            await message.channel.send(self.trans.get("MSG_IMDB_ERROR2", lang))
            raise

        # Check validity
        if not data:
            await message.channel.send(self.trans.get("MSG_IMDB_NORESULTS", lang))
            raise IgnoredException

        return data

    # noinspection PyUnresolvedReferences
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

        # !imdb
        if startswith(prefix + "imdb", prefix + "tmdb"):
            # The process can take some time so we show that something is happening
            await message.channel.trigger_typing()

            cut = message.content[len(prefix + "imdb "):]

            try:
                subcommand, argument = cut.split(" ", maxsplit=1)
            # In case there are no parameters
            except ValueError:
                # Check if no subcommand - valid
                # If there's a subcommand, but no argument, fail
                if not cut.strip(" "):
                    await message.channel.send(trans.get("MSG_IMDB_INVALID_USAGE", lang).format(prefix))
                    return

                else:
                    subcommand, argument = cut, ""

            # !imdb plot
            if subcommand == "plot":
                data = await self._imdb_search(argument, message, lang)

                # Check type
                if data.media_type not in ["tv", "movie"]:
                    await message.channel.send(trans.get("MSG_IMDB_CANTPERSON", lang))
                    return

                # Try to send
                try:
                    info = trans.get("MSG_IMDB_PLOT", lang).format(data.title, data.overview)

                    await message.channel.send(info)
                except AttributeError:
                    await message.channel.send(trans.get("MSG_IMDB_PLOT_MISSING", lang))


            # !imdb trailer
            elif subcommand == "trailer":
                data = await self._imdb_search(argument, message, lang)

                try:
                    await message.channel.send(trans.get("MSG_IMDB_TRAILER", lang).format(data.title, data.trailer))
                except AttributeError:
                    await message.channel.send(trans.get("MSG_IMDB_TRAILER_MISSING", lang))

            # !imdb rating
            elif subcommand == "rating":
                data = await self._imdb_search(argument, message, lang)

                try:
                    content = trans.get("MSG_IMDB_RATINGS", lang).format(data.title, data.vote_average)
                    await message.channel.send(content)
                except AttributeError:
                    await message.channel.send(trans.get("MSG_IMDB_RATINGS_MISSING", lang))

            # !imdb help
            elif subcommand == "help":
                await message.channel.send(trans.get("MSG_IMDB_HELP", lang).replace("_", prefix))

            # !imdb search
            else:
                # Parse arguments
                if subcommand == "search":
                    # !imdb search the hunger games
                    query = argument
                else:
                    # !imdb the hunger games
                    query = " ".join((subcommand, argument))

                data = await self._imdb_search(query, message, lang)

                # Check type
                if data.media_type in ["tv", "movie"]:
                    info = []

                    # Step-by-step adding - some data might be missing
                    try:
                        media_type = trans.get("MSG_IMDB_SERIES", lang) if data.media_type == "tv" else ""

                        info.append("**{}** {}\n".format(data.title, media_type))
                    except AttributeError:
                        pass

                    try:
                        genres = "`{}`".format("`, `".join(data.genres))
                        info.append(trans.get("MSG_IMDB_GENRES", lang).format(genres))
                    except AttributeError:
                        pass

                    try:
                        info.append(trans.get("MSG_IMDB_AVGRATING", lang).format(data.vote_average))
                    except AttributeError:
                        pass

                    if data.media_type == "tv":
                        try:
                            info.append(trans.get("MSG_IMDB_SEASONS", lang).format(len(data.seasons)))
                        except AttributeError:
                            pass

                    try:
                        info.append(trans.get("MSG_IMDB_SUMMARY", lang).format(data.overview))
                    except AttributeError:
                        pass

                    try:
                        if data.poster:
                            info.append(trans.get("MSG_IMDB_POSTER", lang).format(data.poster))
                    except AttributeError:
                        pass

                    # Compile together info that is available
                    media_info = "\n".join(info)

                else:
                    await message.channel.send(trans.get("MSG_IMDB_PERSON_NOT_SUPPORTED", lang))
                    return

                # Send the details
                try:
                    await message.channel.send(media_info)
                except errors.HTTPException:
                    await message.channel.send(trans.get("MSG_IMDB_ERROR", lang))


class NanoPlugin:
    name = "TMDb Commands"
    version = "19"

    handler = TMDb
    events = {
        "on_message": 10
        # type : importance
    }
