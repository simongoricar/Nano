# coding=utf-8


__author__ = "DefaltSimon"

import logging
import copy
import time
import threading
import os
from pickle import load, dump

from urllib.request import urlopen
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

baseurl = "http://www.imdb.com"
findurl = "http://www.imdb.com/find?&q="

MOVIE = 1
SERIES = 2
PERSON = 3

types = {
    1: "Movie",
    2: "TV Series",
    3: "Person"
}

def get_type(typ):
    return str(types.get(int(typ)))

things = [
    "  ",
    "\n",
    "\t",
    "\r"
]

def clean(text):
    for ch in things:
        text = str(text).replace(ch, "")
    return text.strip(" ").strip("\n")

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

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

class Imdb:
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
        self.threadlock = False

        self.allow_local_cache = allow_local_cache

    def lock(self):
        self.threadlock = True

    def wait_until_release(self):
        while self.threadlock:
            time.sleep(0.05)
        return

    def release(self):
        self.threadlock = False

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
        html = urlopen(findurl + str(name).replace(" ", "+"))
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
        html = urlopen(baseurl + f)
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

        video = baseurl + str(sp.find("a", {"itemprop": "trailer"}, href=True).get("href")).strip("?ref_=tt_ov_vi")

        director = sp.find("div", {"class": "credit_summary_item"}).find("span", {"itemprop": "name"}).text
        cast = [a.text for a in sp.find("table", {"class": "cast_list"}).find_all("span", {"itemprop": "name"})]

        #sh = sp.find("table", {"class": "cast_list"})
        #odd = sh.find_all("tr", {"class": "odd"})
        #even = sh.find_all("tr", {"class": "even"})

        #cast = []
        #for rn in range(len(odd + even)):
        #    try:
        #        onee = odd.pop(0)
        #        twoo = even.pop(0)
        #
        #        if not onee and not twoo:
        #            break
        #
        #        if onee:
        #            one = dict(name=onee.find("span", {"itemprop": "name"}).text,
        #                        character=onee.find("td", {"class": "character"})) # .find("a", href=True).text)
        #
        #            cast.append(one)
        #
        #        if twoo:
        #            two = dict(name=onee.find("span", {"itemprop": "name"}).text,
        #                        character=onee.find("td", {"class": "character"})) # .find("a", href=True).text)
        #            cast.append(two)
        #
        #        del onee
        #        del twoo
        #    except IndexError:
        #        break

        summary = clean(sp.find("div", {"class": "summary_text"}).text)
        storyline = clean(sp.find("div", {"class": "inline canwrap", "itemprop": "description"}).text)

        if typ is MOVIE:

            metascore = clean(sp.find("div", {"class": "metacriticScore score_mixed titleReviewBarSubItem"}).text)
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
        knownfor = [a.text for a in sp.find("div", {"id": "knownfor"}).find_all("a", {"class": "knownfor-ellipsis"}, href=True)]

        summary = clean(str(sp.find("div", {"itemprop": "description"}).text).strip("\n")).strip(" See full bio »")


        return Person(name=name, short_bio=summary, rank=rank, known_for=knownfor, type=PERSON)

# Tests
#logging.basicConfig(level=logging.INFO)
#
#im = Imdb()
#
#while True:
#    movie = im.get_page_by_name(input(">"))
#
#    if isinstance(movie, Movie) or isinstance(movie, TVSeries):
#        print(get_type(movie.type))
#        print(movie.cast, sep="\n")
#
#    elif isinstance(movie, Person):
#        print(movie.name, movie.rank, movie.short_bio, movie.known_for, sep="\n")
#
#    else:
#        print("NOTHING FOUND")