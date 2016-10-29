# coding=utf-8
import asyncio
import os
import logging
from pickle import dumps, load
from discord import Message
from data.serverhandler import ServerHandler
from data.stats import MESSAGE, VOTE
from data.utils import is_valid_command, is_empty

__author__ = "DefaltSimon"
# Voting plugin

valid_commands = [
    "_vote start",
    "_vote end", "_vote "
]

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class VoteHandler:
    def __init__(self, **_):

        # Plugin-related
        self.vote_header = {}
        self.vote_content = {}

        self.voters = {}
        self.votes = {}
        self.progress = {}

        self.author = {}

    def need_save(self):
        return bool(self.vote_header or self.vote_content or self.progress)

    def start_vote(self, author, server, vote):

        # Reference - !vote start "Vote for this mate" one|two|three
        self.vote_header[server.id] = str(vote).split("\"")[1]
        vote_names = str(vote).split("\"")[2]

        vote_split = vote_names.split("|")

        self.votes[server.id] = {}
        self.voters[server.id] = []
        count = 0
        for this in vote_split:
            vote_split[count] = this.strip(" ")

            try:
                self.votes[server.id][str(this).strip(" ")] = 0
            except KeyError:
                self.votes[server.id] = []

            count += 1

        self.vote_content[server.id] = vote_split

        self.author[server.id] = str(author)

        self.progress[server.id] = True

    def in_progress(self, server):
        try:
            if self.progress[server.id] is True:
                return True
            else:
                return False
        except KeyError:
            return False

    def plus_one(self, option, voter, server):
        try:
            option = int(option)
        except ValueError:
            return False

        if voter in self.voters[server.id]:
            return -1

        self.voters[server.id].append(voter)

        if option > len(self.votes):
            return False

        else:
            item = self.vote_content[server.id][option - 1]
            try:
                self.votes[server.id][item] += 1
            except KeyError:
                self.votes[server.id][item] = 1

    def get_votes(self, server):
        return self.votes.get(server.id)

    def get_vote_header(self, server):
        return self.vote_header.get(server.id)

    def get_content(self, server):
        return self.vote_content.get(server.id)

    def end_voting(self, server):
        # Resets all server-related voting settings
        self.progress[server.id] = False

        self.votes.pop(server.id)
        self.voters.pop(server.id)

        self.vote_header.pop(server.id)
        self.vote_content.pop(server.id)

        self.author.pop(server.id)


class Vote:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        # Removes the file if it is empty
        if is_empty("cache/voting.temp"):
            os.remove("cache/voting.temp")

        # Uses the cache if it exists
        if os.path.isfile("cache/voting.temp"):
            log.info("Using voting.cache")

            with open("cache/voting.temp", "rb") as vote_cache:
                self.vote = load(vote_cache)

            os.remove("cache/voting.temp")

        else:
            self.vote = VoteHandler()

    async def on_message(self, message, **kwargs):
        assert isinstance(message, Message)
        assert isinstance(self.handler, ServerHandler)
        client = self.client
        prefix = kwargs.get("prefix")

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*args):
            for a in args:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "vote start"):
            if not self.handler.can_use_restricted_commands(message.author, message.channel.server):
                await client.send_message(message.content, "You are not permitted to use this command.")
                # /todo add stats integration
                return

            if self.vote.in_progress(message.channel.server):
                await client.send_message(message.channel, "A vote is already in progress.")
                return

            vote_content = message.content[len(prefix + "vote start "):]

            self.vote.start_vote(message.author.name, message.channel.server, vote_content)

            ch = []
            n = 1
            for this in self.vote.get_content(message.channel.server):
                ch.append("{}. {}".format(n, this))
                n += 1

            ch = "\n".join(ch).strip("\n")

            await client.send_message(message.channel, "**{}**\n"
                                                       "```{}```".format(self.vote.get_vote_header(message.channel.server), ch))

        elif startswith(prefix + "vote end"):
            if not self.handler.can_use_restricted_commands(message.author, message.channel.server):
                await client.send_message(message.content, "You are not permitted to use this command.")
                # /todo add stats integration
                return

            if not self.vote.in_progress(message.channel.server):
                await client.send_message(message.channel, "There is no vote in progress.")
                return

            votes = self.vote.get_votes(message.channel.server)
            header = self.vote.get_vote_header(message.channel.server)
            content = self.vote.get_content(message.channel.server)

            # Actually end the voting
            self.vote.end_voting(message.channel.server)

            # Compile results
            cn = ["{} - `{} votes`".format(a, votes[a]) for a in content]

            combined = "Vote ended:\n__{}__\n\n{}".format(header, "\n".join(cn))

            await client.send_message(message.channel, combined)

        elif startswith(prefix + "vote"):
            choice = message.content[len(prefix + "vote "):]

            if not choice:
                return

            if not self.vote.in_progress(message.channel.server):
                return

            res = self.vote.plus_one(int(choice), message.author.id, message.channel.server)

            if res == -1:
                msg = await client.send_message(message.channel, "Cheater :smile:")

                await asyncio.sleep(1)

                await client.delete_message(msg)

            self.stats.add(VOTE)

    async def on_shutdown(self):
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        if self.vote.need_save():
            with open("cache/voting.temp", "wb") as cache:
                cache.write(dumps(self.vote))  # Save instance of Vote to be used on the next boot


class NanoPlugin:
    _name = "Voting"
    _version = 0.2

    handler = Vote
    events = {
        "on_message": 10,
        "on_shutdown": 5,
        # type : importance
    }
