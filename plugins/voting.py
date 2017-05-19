# coding=utf-8
import asyncio
import os
import logging
import importlib
from pickle import dumps, load
from discord import Message, Embed, Colour, errors
from data.serverhandler import ServerHandler
from data.stats import MESSAGE, VOTE, WRONG_PERMS, WRONG_ARG
from data.utils import is_valid_command, is_empty, StandardEmoji, log_to_file

__author__ = "DefaltSimon"
# Voting plugin

commands = {
    "_vote start": {"desc": "Starts a vote on the server.", "use": "[command] \"question\" choice1|choice2|...", "alias": None},
    "_vote end": {"desc": "Simply ends the current vote on the server.", "use": None, "alias": None},
    "_vote status": {"desc": "Shows info about the current voting.", "use": None, "alias": None},
    "_vote": {"desc": "Votes for an option if there is voting going on.", "use": "[command] [1,2,3,...]", "alias": None},
}

valid_commands = commands.keys()

NO_VOTE = StandardEmoji.WARNING + " There is no vote in progress."
IN_PROGRESS = StandardEmoji.WARNING + " A vote is already in progress."

VOTE_ITEM_LIMIT = 10
VOTE_ITEM_MAX_LENGTH = 800

OK_EMOJI = "\U0001F44D"

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LegacyVoteHandler:
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

    def get_votes(self, server_id):
        return self.votes.get(server_id)

    def get_vote_title(self, server_id):
        return self.vote_header.get(server_id)

    def get_choices(self, server_id):
        return self.vote_content.get(server_id)

    def end_voting(self, server):
        # Resets all server-related voting settings
        self.progress[server.id] = False

        self.votes.pop(server.id)
        self.voters.pop(server.id)

        self.vote_header.pop(server.id)
        self.vote_content.pop(server.id)

        self.author.pop(server.id)


class RedisVoteHandler:
    def __init__(self, handler):
        self.redis = handler.get_plugin_data_manager(namespace="voting")

        try:
            self.json = importlib.import_module("ujson")
        except ImportError:
            self.json = importlib.import_module("json")

    def need_save(self):
        # DEPRECATED
        return False

    def get_vote_amount(self):
        return len(self.redis.scan_iter("*"))

    def start_vote(self, author_name, server, title, choices):
        if self.redis.exists(server):
            return False

        payload = {
            "author": str(author_name),
            "votes": self.json.dumps({a: 0 for a in choices}),
            "voters": self.json.dumps([]),
            "title": str(title),
            "choices": self.json.dumps(choices),
            "inprogress": True,
        }

        self.redis.hmset(server, payload)
        return True

    def in_progress(self, server):
        return self.redis.exists(server.id)

    def plus_one(self, option, voter, server):
        if not self.in_progress(server):
            return False

        voters = self.json.loads(self.redis.hget(server.id, "voters"))
        vote_counts = self.json.loads(self.redis.hget(server.id, "votes"))

        try:
            choice_name = self.json.loads(self.redis.hget(server.id, "choices"))[option]
        except IndexError:
            return False

        if voter not in voters:
            voters.append(voter)
        else:
            return -1

        try:
            vote_counts[choice_name] += 1
            self.redis.hset(server.id, "votes", self.json.dumps(vote_counts))
            self.redis.hset(server.id, "voters", self.json.dumps(voters))
        except KeyError:
            return False

        return True

    def get_votes(self, server_id):
        return self.json.loads(self.redis.hget(server_id, "votes"))

    def get_vote_title(self, server_id):
        return self.redis.hget(server_id, "title")

    def get_choices(self, server_id):
        # get_content -> choices
        return self.json.loads(self.redis.hget(server_id, "choices"))

    def end_voting(self, server):
        return bool(self.redis.delete(server.id))


class Vote:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.legacy = kwargs.get("legacy")

        if kwargs.get("legacy"):
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
                self.vote = LegacyVoteHandler()

        else:
            self.vote = RedisVoteHandler(self.handler)

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
                await client.send_message(message.channel, StandardEmoji.WARNING + " Too many vote options "
                                                                                   "(max is **{}**, you put *{}*)".format(VOTE_ITEM_LIMIT, len(vote_items)))
                return

            if (len(title) + sum([len(a) for a in vote_items])) > VOTE_ITEM_MAX_LENGTH:
                await client.send_message(message.channel, StandardEmoji.WARNING + " The whole thing is too long! (max is {}, you have {}".format(VOTE_ITEM_MAX_LENGTH, sum([len(a) for a in vote_items])))

            self.vote.start_vote(message.author.name, message.server.id, title, vote_items)

            ch = "\n".join(["{}. {}".format(en + 1, ch) for en, ch in
                            enumerate(self.vote.get_choices(message.server.id))]).strip("\n")

            await client.send_message(message.channel, "Vote started:\n**{}**\n"
                                                       "```js\n{}```".format(self.vote.get_vote_title(message.server.id), ch))

        # !vote end
        elif startswith(prefix + "vote end"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                await client.send_message(message.channel, "You are not permitted to use this command.")

                self.stats.add(WRONG_PERMS)
                return

            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, NO_VOTE)
                return

            votes = self.vote.get_votes(message.server.id)
            title = self.vote.get_vote_title(message.server.id)

            embed = Embed(title=title, colour=Colour(0x303F9F),
                          description="(In total, {} people voted)".format(sum(votes.values())))
            embed.set_footer(text="Voting ended")

            for name, val in votes.items():
                embed.add_field(name=name, value="{} votes".format(val))

            try:
                await client.send_message(message.channel, "Vote ended:", embed=embed)
            except errors.HTTPException as e:
                await client.send_message(message.channel, "Something went wrong when trying to end voting. It has been logged and will be inspected.")
                log_to_file("VOTING ({}): {}".format(e, embed.to_dict()))
                return

            # Actually end the voting
            self.vote.end_voting(message.server)

        # !vote status
        elif startswith(prefix + "vote status"):
            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, NO_VOTE)
                return

            header = self.vote.get_vote_title(message.server.id)
            votes = sum(self.vote.get_votes(message.server.id).values())

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
                print("not in progress")
                return

            # Get the choice, but tell the author if he/she didn't supply a number
            try:
                choice = int(message.content[len(prefix + "vote "):]) - 1
            except ValueError:
                m = await client.send_message(message.channel, "Vote argument must be a number.")
                await asyncio.sleep(1.5)
                await client.delete_message(m)
                return

            if choice < 0:
                return

            res = self.vote.plus_one(choice, message.author.id, message.channel.server)

            if res == -1:
                msg = await client.send_message(message.channel, "Cheater " + StandardEmoji.NORMAL_SMILE)

                await asyncio.sleep(1)
                await client.delete_message(msg)

            elif res:
                await client.add_reaction(message, OK_EMOJI)

            else:
                msg = await client.send_message(message.channel, "Something went wrong... " + StandardEmoji.FROWN2)

                await asyncio.sleep(1)
                await client.delete_message(msg)

            self.stats.add(VOTE)

    async def on_shutdown(self):
        if not self.legacy:
            return

        # Saves the state of votes
        if not os.path.isdir("cache"):
            os.mkdir("cache")

        if self.vote.need_save():
            self.save_state()
        else:
            try:
                os.remove("cache/voting.temp")
            except OSError:
                pass


class NanoPlugin:
    name = "Voting"
    version = "0.2.5"

    handler = Vote
    events = {
        "on_message": 10,
        "on_shutdown": 5,
        # type : importance
    }
