# coding=utf-8
import asyncio
import os
import logging
from pickle import dumps, load
from discord import Message
from data.serverhandler import ServerHandler
from data.stats import MESSAGE, VOTE, WRONG_PERMS, WRONG_ARG
from data.utils import is_valid_command, is_empty, StandardEmoji

__author__ = "DefaltSimon"
# Voting plugin

valid_commands = [
    "_vote start", "_vote status"
    "_vote end", "_vote "
]

NO_VOTE = StandardEmoji.WARNING + " There is no vote in progress."
IN_PROGRESS = StandardEmoji.WARNING + " A vote is already in progress."

VOTE_ITEM_LIMIT = 10

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

    def start_vote(self, author, server, title, choices):
        # Reference - !vote start "Vote for this mate" one|two|three
        self.vote_header[server.id] = title

        # Assumes there is no ongoing vote
        self.votes[server.id] = {}
        self.voters[server.id] = []
        self.vote_content[server.id] = []
        self.author[server.id] = None

        for this in choices:
            try:
                self.votes[server.id][this] = 0
            except KeyError:
                self.votes[server.id] = []

        self.vote_content[server.id] = choices
        self.author[server.id] = str(author)
        self.progress[server.id] = True

    def in_progress(self, server):
        try:
            return self.progress[server.id] is True
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

            return True

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

            # 3.1.5 : disabled
            # os.remove("cache/voting.temp")

        else:
            self.vote = VoteHandler()

    def save_state(self):
        with open("cache/voting.temp", "wb") as cache:
            cache.write(dumps(self.vote))  # Save instance of Vote to be used on the next boot

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

        # !vote start
        if startswith(prefix + "vote start"):
            if not self.handler.can_use_restricted_commands(message.author, message.channel.server):
                await client.send_message(message.channel, "You are not permitted to use this command.")

                self.stats.add(WRONG_PERMS)
                return

            if self.vote.in_progress(message.channel.server):
                await client.send_message(message.channel, IN_PROGRESS)
                return

            vote_content = message.content[len(prefix + "vote start "):]
            base = str(vote_content).split("\"")

            if len(base) != 3:
                await client.send_message(message.channel, "Incorrect usage. Check {}help vote start for info.".format(prefix))
                self.stats.add(WRONG_ARG)
                return

            title = str(base[1])
            vote_items = str(base[2]).split("|")
            vote_items = [a.strip(" ") for a in list(vote_items)]

            if len(vote_items) > VOTE_ITEM_LIMIT:
                await client.send_message(message.channel, StandardEmoji.WARNING + " The vote options are bigger than allowed "
                                                           "(max is **{}**, you put *{}*)".format(VOTE_ITEM_LIMIT, len(vote_items)))
                return

            self.vote.start_vote(message.author.name, message.channel.server, title, vote_items)

            ch = []
            n = 1
            for this in self.vote.get_content(message.channel.server):
                ch.append("{}. {}".format(n, this))
                n += 1

            ch = "\n".join(ch).strip("\n")

            await client.send_message(message.channel, "**{}**\n"
                                                       "```{}```".format(self.vote.get_vote_header(message.server), ch))

        # !vote end
        elif startswith(prefix + "vote end"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                await client.send_message(message.channel, "You are not permitted to use this command.")

                self.stats.add(WRONG_PERMS)
                return

            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, NO_VOTE)
                return

            votes = self.vote.get_votes(message.server)
            header = self.vote.get_vote_header(message.server)
            content = self.vote.get_content(message.server)

            # Actually end the voting
            self.vote.end_voting(message.server)

            # Put results together
            cn = ["{} - `{} votes`".format(a, votes[a]) for a in content]

            combined = "Vote ended:\n__{}__\n\n{}".format(header, "\n".join(cn))

            await client.send_message(message.channel, combined)

        # !vote status
        elif startswith(prefix + "vote status"):
            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, NO_VOTE)
                return

            header = self.vote.get_vote_header(message.server)
            votes = sum(self.vote.get_votes(message.server).values())

            if votes == 0:
                vote_disp = "no-one has voted yet"
            elif votes == 1:
                vote_disp = "only one person has voted"
            else:
                vote_disp = "{} people have voted".format(votes)

            await client.send_message(message.channel, "**Vote:** \"{}\"\n```So far, {}.```".format(header, vote_disp))

        # !vote
        elif startswith(prefix + "vote"):
            # Ignore if there is no vote going on instead of getting an exception
            if not self.vote.in_progress(message.server):
                return

            # Get the choice, but tell the author if he/she didn't supply a number
            try:
                choice = int(message.content[len(prefix + "vote "):])
            except ValueError:
                m = await client.send_message(message.channel, "Vote argument must be a number.")
                await asyncio.sleep(1.5)
                await client.delete_message(m)
                return

            if (not choice) or (not self.vote.in_progress(message.channel.server)):
                return

            res = self.vote.plus_one(choice, message.author.id, message.channel.server)

            if res == -1:
                msg = await client.send_message(message.channel, "Cheater " + StandardEmoji.NORMAL_SMILE)

                await asyncio.sleep(1)
                await client.delete_message(msg)

            elif res:
                msg = await client.send_message(message.channel, StandardEmoji.PERFECT)

                await asyncio.sleep(1.5)
                await client.delete_message(msg)

            self.stats.add(VOTE)

    async def on_shutdown(self):
        # Saves the state of votes
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        if self.vote.need_save():
            print("saving")
            print(self.vote.__dict__)
            self.save_state()
        else:
            try:
                os.remove("cache/voting.temp")
            except OSError:
                pass


class NanoPlugin:
    _name = "Voting"
    _version = "0.2.4"

    handler = Vote
    events = {
        "on_message": 10,
        "on_shutdown": 5,
        # type : importance
    }
