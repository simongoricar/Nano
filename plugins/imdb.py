# coding=utf-8
import os
import time
import copy
import logging

from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import HTTPError
from discord import Message
from pickle import load, dump
from data.utils import threaded, is_valid_command
from data.stats import MESSAGE

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# CONSTANTS

IMDB_PROBLEMS = "Something went wrong while trying to get IMDb info."

base_url = "http://www.imdb.com"
search_url = "http://www.imdb.com/find?&q="

MOVIE = 1
SERIES = 2
PERSON = 3

types = {
    1: "Movie",
    2: "TV Series",
    3: "Person"}


def get_type(typ):
    return str(types.get(int(typ)))

things = [
    "  ",
    "\n",
    "\t",
    "\r"]


def clean(text):
    for ch in things:
        text = str(text).replace(ch, "")
    return text.strip(" ").strip("\n")

commands = {
    "_imdb search": {"desc": "Searches for a film/series/person and displays general info", "use": "[command] [film/series/person name]", "alias": None},
    "_imdb trailer": {"desc": "Gives you a link to the trailer of a film/series.", "use": "[command] [film/series/person name]", "alias": None},
    "_imdb plot": {"desc": "Displays more plot info about a film/series.", "use": "[command] [film/series/person name]", "alias": None},
    "_imdb rating": {"desc": "Displays different ratings for the film/series.", "use": "[command] [film/series/person name]", "alias": None},
    "_imdb help": {"desc": "Displays available commands regarding IMDb.", "use": "[command]", "alias": None},
    "_imdb": {"desc": "The IMDb module\nSubcommands: search trailer plot rating help", "use": None, "alias": None},
}

valid_commands = commands.keys()

# Objects


class Movie:
    def __init__(self, **kwargs):

        self.name = kwargs.get("name")
        self.length = kwargs.get("length")

        self.genres = kwargs.get("genres")

        self.rating = kwargs.get("rating")
        self.metascore = kwargs.get("metascore")

        self.video = kwargs.get("video")

        self.director = kwargs.get("director")
        self.writers = kwargs.get("writers")
        self.cast = kwargs.get("cast")

        self.summary = kwargs.get("summary")
        self.storyline = kwargs.get("storyline")

        self.type = kwargs.get("type")
        self.year = kwargs.get("year")

    @property
    def title(self):
        return self.name

    @property
    def trailer(self):
        return self.video


class TVSeries(Movie):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.series = kwargs.get("series")


class Person:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.short_bio = kwargs.get("short_bio")

        self.rank = kwargs.get("rank")

        self.known_for = kwargs.get("known_for")

        self.type = kwargs.get("type")


# Main class

class ImdbSearch:
    def __init__(self, max_age=86400, allow_local_cache=True):
        if os.path.isfile("cache/imdb.cache"):
            with open("cache/imdb.cache", "rb") as js:
                if js.read():
                    js.seek(0)

                    log.info("Using cache")
                    self.cache = load(js)
                else:
                    self.cache = {}
        else:
            log.info("Enabled, no cache")
            self.cache = {}

        self.max_age = max_age
        self.thread_lock = False

        self.allow_local_cache = allow_local_cache

    def lock(self):
        self.thread_lock = True

    def wait_until_release(self):
        while self.thread_lock:
            time.sleep(0.05)
        return

    def release(self):
        self.thread_lock = False

    @threaded
    def queue_write(self, data):
        if not self.allow_local_cache:
            return

        assert isinstance(data, dict)

        if self.cache != data:
            self.cache = copy.deepcopy(data)

        self.wait_until_release()

        self.lock()
        if not os.path.isdir("cache"): os.mkdir("cache")

        with open("cache/imdb.cache", "wb") as file:
            dump(data, file)
        self.release()

    def _clean_cache(self):
        log.warning("Cleaning cache")
        self.cache = {}

        if os.path.exists("cache/imdb.cache"):
            os.remove("cache/imdb.cache")

    def get_page_by_name(self, name):
        # Searching page

        html = urlopen(search_url + str(name).replace(" ", "+"))
        sp = BeautifulSoup(html, "html.parser")

        try:
            f = str(sp.find("tr", {"class": "findResult odd"}).find("a", href=True).get("href"))
        except AttributeError:
            # Returns None when no Film, Series or Person is found
            return None

        # Do not request page if it is in the cache and has a valid timestamp
        if self.cache.get(f):
            if self.cache[f].get("timestamp") - time.time() < self.max_age:
                log.debug("using cache for " + str(f))
                return self.cache[f].get("data")

        log.debug("requesting page for " + str(f))
        html = urlopen(base_url + f)
        sp = BeautifulSoup(html, "html.parser")

        # Figuring out the type
        typ = PERSON if f.startswith("/name") else None

        if not typ:
            try:
                typ = SERIES if "Episode Guide" == sp.find("div", {"class": "bp_heading"}).text else MOVIE
            except AttributeError:
                typ = MOVIE

        # Finding data and getting an instance
        if typ is MOVIE:
            data = self._get_data_tv_movie(sp, MOVIE)

        elif typ is SERIES:
            data = self._get_data_tv_movie(sp, SERIES)

        elif typ is PERSON:
            data = self._get_data_person(sp)

        else:
            # Impossible but k
            return None

        # Caching
        if not self.cache.get(f):
            self.cache[f] = {"data": data, "timestamp": time.time()}
            self.queue_write(self.cache)

        # Returning the instance
        return data

    @staticmethod
    def _get_data_tv_movie(sp, typ):
        name = str(sp.find("h1", {"itemprop": "name"}).text)
        name = name[:name.rfind("(")].strip(" ")

        length = clean(sp.find("time", {"itemprop": "duration"}).text)
        genres = [str(a.text).strip(" ") for a in sp.find("div", {"itemprop": "genre"}).find_all("a", href=True)]
        rating = sp.find("span", {"itemprop": "ratingValue"}).text

        video = base_url + str(sp.find("a", {"itemprop": "trailer"}, href=True).get("href")).strip("?ref_=tt_ov_vi")

        director = sp.find("div", {"class": "credit_summary_item"}).find("span", {"itemprop": "name"}).text
        cast = [a.text for a in sp.find("table", {"class": "cast_list"}).find_all("span", {"itemprop": "name"})]

        summary = clean(sp.find("div", {"class": "summary_text"}).text)
        storyline = clean(sp.find("div", {"class": "inline canwrap", "itemprop": "description"}).text)

        if typ is MOVIE:

            # Not fully flexible
            # metascore = clean(sp.find("div", {"class": "metacriticScore titleReviewBarSubItem"}).text)
            # Instead, this

            metascore = clean(sp.find("div", {"class": "titleReviewBarItem"}).find("a", href=True).text)

            writers = [a.text for a in
                       sp.find_all("div", {"class": "credit_summary_item"})[1].find_all("span", {"itemprop": "name"})]
            yr = sp.find("span", {"id": "titleYear"}).find("a", href=True).text

            return Movie(name=name, length=length, genres=genres, rating=rating, metascore=metascore, video=video,
                         director=director, writers=writers, cast=cast, summary=summary, storyline=storyline,
                         year=str(yr), type=MOVIE)

        else:
            series = len(sp.find("div", {"class": "seasons-and-year-nav"}).find_all("a", href=True))

            return TVSeries(name=name, length=length, genres=genres, rating=rating, video=video,
                            director=director, cast=cast, summary=summary, storyline=storyline, type=SERIES,
                            series=series)

    @staticmethod
    def _get_data_person(sp):
        name = sp.find("span", {"itemprop": "name"}).text
        rank = sp.find("a", {"id": "meterRank"}, href=True).text
        known_for = [a.text for a in sp.find("div", {"id": "knownfor"}).find_all("a", {"class": "knownfor-ellipsis"}, href=True)]

        summary = clean(str(sp.find("div", {"itemprop": "description"}).text).strip("\n")).strip(" See full bio »")

        return Person(name=name, short_bio=summary, rank=rank, known_for=known_for, type=PERSON)


class IMDB:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        self.imdb = ImdbSearch()

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

            if startswith(prefix + "imdb plot") or startswith(prefix + "imdb story"):
                if startswith(prefix + "imdb plot"):
                    search = str(message.content[len(prefix + "imdb plot "):])
                else:
                    search = str(message.content[len(prefix + "imdb story "):])

                try:
                    data = self.imdb.get_page_by_name(search)
                except:
                    await client.send_message(message.channel, IMDB_PROBLEMS)
                    return

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == PERSON:
                    return
                else:
                    await client.send_message(message.channel,
                                              "**{}**'s story\n```{}```".format(data.name, data.storyline))

            elif startswith(prefix + "imdb search"):
                search = str(message.content[len(prefix + "imdb search "):])

                try:
                    data = self.imdb.get_page_by_name(search)
                except:
                    await client.send_message(message.channel, IMDB_PROBLEMS)
                    return

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == MOVIE:
                    st = """**{}** ({})\n\nLength: `{}`\nGenres: {}\nRating: **{}/10**\n\nDirector: *{}*\nSummary:
                    ```{}```""".format(data.name, data.year, data.length, str("`" + "`, `".join(data.genres) + "`"),
                                       data.rating, data.director, data.summary)

                elif data.type == SERIES:
                    st = """**{}** series\n\nGenres: {}\nRating: **{}/10**\n\nDirector: *{}*\nSummary:
                    ```{}```""".format(data.name, str("`" + "`, `".join(data.genres) + "`"), data.rating,
                                       data.director, data.summary)

                elif data.type == PERSON:
                    st = """**{}**\n\nKnown for: {}\nIMDB Rank: **{}**\n\nShort bio:
                    ```{}```""".format(data.name, str("`" + "`, `".join(data.known_for) + "`"), data.rank, data.short_bio)

                else:
                    return

                # Send the details
                await client.send_message(message.channel, st)

            elif startswith(prefix + "imdb trailer"):
                search = str(message.content[len(prefix + "imdb trailer "):])

                try:
                    data = self.imdb.get_page_by_name(search)
                except:
                    await client.send_message(message.channel, IMDB_PROBLEMS)
                    return

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if data.type == PERSON:
                    return

                await client.send_message(message.channel,
                                          "**{}**'s trailer on IMDB: {}".format(data.name, data.trailer))

            elif startswith(prefix + "imdb rating"):
                search = str(message.content[len(prefix + "imdb rating "):])

                try:
                    data = self.imdb.get_page_by_name(search)
                except:
                    await client.send_message(message.channel, IMDB_PROBLEMS)
                    return

                if not data:
                    await client.send_message(message.channel, "No results.")
                    return

                if not data.type == MOVIE:
                    await client.send_message(message.channel, "Only movies have Metascores.")
                    return

                await client.send_message(message.channel,
                                          "**{}**'s ratings on IMDB\nUser ratings: __{} out of 10__\n"
                                          "Metascore: __{}__".format(data.name, data.rating, data.metascore))

            else:
                await client.send_message(message.channel,
                                          "**IMDB help**\n\n`_imdb search [name or title]`, `_imdb plot [title]`, "
                                          "`_imdb trailer [title]`, `_imdb rating [title]`".replace("_", prefix))


class NanoPlugin:
    name = "Imdb Commands"
    version = "0.1.1"

    handler = IMDB
    events = {
        "on_message": 10
        # type : importance
    }
