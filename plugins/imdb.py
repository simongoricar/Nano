# coding=utf-8
import configparser
import logging

from discord import Message, errors

# External library available here: https://github.com/DefaltSimon/TMDbie
import tmdbie
from data.stats import MESSAGE
from data.utils import is_valid_command

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

commands = {
    "_imdb search": {"desc": "Searches for a film/series/person and displays general info", "use": "[command] [film/series/person name]", "alias": "_tmdb search"},
    "_imdb trailer": {"desc": "Gives you a link to the trailer of a film/series.", "use": "[command] [film/series/person name]", "alias": "_tmdb trailer"},
    "_imdb plot": {"desc": "Displays more plot info about a film/series.", "use": "[command] [film/series/person name]", "alias": "_tmdb plot"},
    "_imdb rating": {"desc": "Displays different ratings for the film/series.", "use": "[command] [film/series/person name]", "alias": "_tmdb rating"},
    "_imdb help": {"desc": "Displays available commands regarding IMDb.", "use": "[command]", "alias": "_tmdb help"},
    "_imdb": {"desc": "The TMDb (https://www.themoviedb.org/) module\nSubcommands: search trailer plot rating help", "use": None, "alias": None},
    "_tmdb": {"desc": "General alias for the imdb command (see the help message)", "use": None, "alias": None}
}

valid_commands = commands.keys()

# Objects


class TMDb:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")
        self.trans = kwargs.get("trans")

        try:
            self.tmdb = tmdbie.Client(api_key=parser.get("tmdb", "api-key"))
        except (configparser.NoSectionError, configparser.NoOptionError):
            log.critical("Missing api key for osu!, disabling plugin...")
            raise RuntimeError

    # noinspection PyUnresolvedReferences
    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        client = self.client
        prefix = kwargs.get("prefix")

        trans = self.trans
        lang = kwargs.get("lang")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if startswith((prefix + "imdb"), (prefix + "tmdb")):
            # The process can take some time so we show that something is happening
            await client.send_typing(message.channel)

            if startswith((prefix + "imdb plot"), (prefix + "tmdb plot")):
                search = str(message.content[len(prefix + "imdb plot "):])

                try:
                    data = await self.tmdb.search_multi(search)
                except tmdbie.TMDbException:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_ERROR2", lang))
                    raise

                if not data:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_NORESULTS", lang))
                    return

                if data.media_type not in ["tv", "movie"]:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_CANTPERSON", lang))
                    return

                try:
                    info = trans.get("MSG_IMDB_PLOT", lang).format(data.title, data.overview)

                    await client.send_message(message.channel, info)
                except AttributeError:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_PLOT_MISSING", lang))


            elif startswith((prefix + "imdb search"), (prefix + "tmdb search")):
                search = str(message.content[len(prefix + "imdb search "):])

                try:
                    data = await self.tmdb.search_multi(search)
                except tmdbie.TMDbException:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_ERROR2", lang))
                    raise

                if not data:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_NORESULTS", lang))
                    return

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
                    await client.send_message(message.channel, trans.get("MSG_IMDB_PERSON_NOT_SUPPORTED", lang))
                    return

                # Send the details
                try:
                    await client.send_message(message.channel, media_info)
                except errors.HTTPException:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_ERROR", lang))

            elif startswith((prefix + "imdb trailer"), (prefix + "tmdb trailer")):
                search = str(message.content[len(prefix + "imdb trailer "):])

                try:
                    data = await self.tmdb.search_multi(search)
                except tmdbie.TMDbException:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_ERROR2", lang))
                    raise

                if not data:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_NORESULTS", lang))
                    return

                try:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_TRAILER", lang).format(data.title, data.trailer))
                except AttributeError:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_TRAILER_MISSING", lang))

            elif startswith((prefix + "imdb rating"), (prefix + "tmdb rating")):
                search = str(message.content[len(prefix + "imdb rating "):])

                try:
                    data = await self.tmdb.search_multi(search)
                except tmdbie.TMDbException:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_ERROR2", lang))
                    raise

                if not data:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_NORESULTS", lang))
                    return

                try:
                    content = trans.get("MSG_IMDB_RATINGS", lang).format(data.title, data.vote_average)
                    await client.send_message(message.channel, content)
                except AttributeError:
                    await client.send_message(message.channel, trans.get("MSG_IMDB_RATINGS_MISSING", lang))

            else:
                await client.send_message(message.channel, trans.get("MSG_IMDB_HELP", lang).replace("_", prefix))


class NanoPlugin:
    name = "TMDb Commands"
    version = "15"

    handler = TMDb
    events = {
        "on_message": 10
        # type : importance
    }
