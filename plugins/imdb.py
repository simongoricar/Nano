# coding=utf-8
import logging
# External library available here: https://github.com/DefaltSimon/OMDbie
import omdbie
from discord import Message, errors
from data.utils import is_valid_command
from data.stats import MESSAGE

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS
IMDB_PROBLEMS = "Something went wrong while trying to get IMDb info."

commands = {
    "_imdb search": {"desc": "Searches for a film/series/person and displays general info", "use": "[command] [film/series/person name]", "alias": "_omdb search"},
    "_imdb trailer": {"desc": "Gives you a link to the trailer of a film/series.", "use": "[command] [film/series/person name]", "alias": "_omdb trailer"},
    "_imdb plot": {"desc": "Displays more plot info about a film/series.", "use": "[command] [film/series/person name]", "alias": "_omdb plot"},
    "_imdb rating": {"desc": "Displays different ratings for the film/series.", "use": "[command] [film/series/person name]", "alias": "_omdb rating"},
    "_imdb help": {"desc": "Displays available commands regarding IMDb.", "use": "[command]", "alias": "_omdb help"},
    "_imdb": {"desc": "The OMDb (http://omdbapi.com) module\nSubcommands: search trailer plot rating help", "use": None, "alias": None},
}

valid_commands = commands.keys()

# Objects


class IMDB:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.loop = kwargs.get("loop")

        self.omdb = omdbie.Client(loop=self.loop)

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)

        client = self.client
        prefix = kwargs.get("prefix")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "imdb"):
            # The process can take some time so we show that something is happening
            await client.send_typing(message.channel)

            if startswith((prefix + "imdb plot"), (prefix + "omdb plot")):
                search = str(message.content[len(prefix + "imdb plot "):])

                data = await self.omdb.by_title_or_id(search, plot=omdbie.PlotLength.full)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                await client.send_message(message.channel, "**{}**'s story\n```{}```".format(data.title, data.plot))

            elif startswith(prefix + "imdb search"):
                search = str(message.content[len(prefix + "imdb search "):])

                data = await self.omdb.by_title_or_id(search, plot=omdbie.PlotLength.full)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == omdbie.VideoType.series:
                    st = """**{}** series\n\nGenres: {}\nRating: **{}/10**\n\nDirector: *{}*\nSummary:
                    ```{}```""".format(data.title, str("`" + "`, `".join(data.genre) + "`"), data.imdb_rating,
                                       data.director, data.plot)

                else:
                    st = """**{}** ({})\n\nLength: `{}`\nGenres: {}\nRating: **{}/10**\n\nDirector: *{}*\nSummary:
                    ```{}```""".format(data.title, data.year, data.runtime, str("`" + "`, `".join(data.genre) + "`"),
                                       data.imdb_rating, data.director, data.plot)

                # Send the details
                try:
                    await client.send_message(message.channel, st)
                except errors.HTTPException:
                    await client.send_message(message.channel, "Something went wrong, please report it to the dev, preferably with a screenshot. Thanks!")

            elif startswith(prefix + "imdb trailer"):
                search = str(message.content[len(prefix + "imdb trailer "):])

                data = await self.omdb.by_title_or_id(search, plot=omdbie.PlotLength.full)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                await client.send_message(message.channel, "**{}**'s trailers on IMDB: {}".format(data.title, data.trailer))

            elif startswith(prefix + "imdb rating"):
                search = str(message.content[len(prefix + "imdb rating "):])

                data = await self.omdb.by_title_or_id(search, plot=omdbie.PlotLength.full)

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if not data.type == omdbie.VideoType.series:
                    await client.send_message(message.channel, "Only movies have Metascores.")
                    return

                await client.send_message(message.channel,
                                          "**{}**'s ratings on IMDB\nUser ratings: __{} out of 10__\n".format(data.title, data.imdb_rating))

            else:
                await client.send_message(message.channel,
                                          "**OMDb/IMDb help**\n\n`_imdb search [name or title]`, `_imdb plot [title]`, "
                                          "`_imdb trailer [title]`, `_imdb rating [title]`".replace("_", prefix))


class NanoPlugin:
    name = "Imdb Commands"
    version = "0.1.2"

    handler = IMDB
    events = {
        "on_message": 10
        # type : importance
    }
