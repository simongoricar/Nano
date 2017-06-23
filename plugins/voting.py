# coding=utf-8
import asyncio
import importlib
import logging
from pickle import dumps

from discord import Message, Embed, Colour, errors

from data.stats import MESSAGE, VOTE, WRONG_PERMS, WRONG_ARG
from data.utils import is_valid_command, log_to_file

__author__ = "DefaltSimon"
# Voting plugin

commands = {
    "_vote start": {"desc": "Starts a vote on the server.", "use": "[command] \"question\" choice1|choice2|...", "alias": None},
    "_vote end": {"desc": "Simply ends the current vote on the server.", "use": None, "alias": None},
    "_vote status": {"desc": "Shows info about the current voting.", "use": None, "alias": None},
    "_vote": {"desc": "Votes for an option if there is voting going on.", "use": "[command] [1,2,3,...]", "alias": None},
}

valid_commands = commands.keys()

VOTE_ITEM_LIMIT = 10
VOTE_ITEM_MAX_LENGTH = 800

OK_EMOJI = "\U0001F44D"

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class RedisVoteHandler:
    def __init__(self, handler):
        self.redis = handler.get_plugin_data_manager(namespace="voting")

        try:
            self.json = importlib.import_module("ujson")
        except ImportError:
            self.json = importlib.import_module("json")

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
        self.trans = kwargs.get("trans")

        self.vote = RedisVoteHandler(self.handler)

    def save_state(self):
        with open("cache/voting.temp", "wb") as cache:
            cache.write(dumps(self.vote))  # Save instance of Vote to be used on the next boot

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

        def startswith(*args):
            for a in args:
                if message.content.startswith(a):
                    return True

            return False

        # !vote start
        if startswith(prefix + "vote start"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_ADMIN", lang))

                self.stats.add(WRONG_PERMS)
                return

            if self.vote.in_progress(message.server):
                await client.send_message(message.channel, trans.get("MSG_VOTING_IN_PROGRESS", lang))
                return

            vote_content = message.content[len(prefix + "vote start "):]
            base = str(vote_content).split("\"")

            if len(base) != 3:
                await client.send_message(message.channel, trans.get("MSG_VOTING_I_USAGE", lang).format(prefix))
                self.stats.add(WRONG_ARG)
                return

            title = str(base[1])
            vote_items = str(base[2]).split("|")
            vote_items = [a.strip(" ") for a in list(vote_items)]

            if len(vote_items) > VOTE_ITEM_LIMIT:
                await client.send_message(message.channel, trans.get("MSG_VOTING_OPTIONS_TM", lang).format(VOTE_ITEM_LIMIT, len(vote_items)))
                return

            if (len(title) + sum([len(a) for a in vote_items])) > VOTE_ITEM_MAX_LENGTH:
                await client.send_message(message.channel, trans.get("MSG_VOTING_OPTIONS_TL ", lang).format(VOTE_ITEM_MAX_LENGTH, sum([len(a) for a in vote_items])))

            self.vote.start_vote(message.author.name, message.server.id, title, vote_items)

            ch = "\n".join(["{}. {}".format(en + 1, ch) for en, ch in
                            enumerate(self.vote.get_choices(message.server.id))]).strip("\n")

            await client.send_message(message.channel, trans.get("MSG_VOTING_STARTED", lang).format(self.vote.get_vote_title(message.server.id), ch))

        # !vote end
        elif startswith(prefix + "vote end"):
            if not self.handler.can_use_restricted_commands(message.author, message.server):
                await client.send_message(message.channel, trans.get("PERM_ADMIN", lang))

                self.stats.add(WRONG_PERMS)
                return

            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            votes = self.vote.get_votes(message.server.id)
            title = self.vote.get_vote_title(message.server.id)

            embed = Embed(title=title, colour=Colour(0x303F9F), description=trans.get("MSG_VOTING_AMOUNT", lang).format(sum(votes.values())))

            for name, val in votes.items():
                embed.add_field(name=name, value=trans.get("MSG_VOTING_AMOUNT2", lang).format(val))

            try:
                await client.send_message(message.channel, trans.get("MSG_VOTING_ENDED", lang), embed=embed)
            except errors.HTTPException as e:
                await client.send_message(message.channel, trans.get("MSG_VOTING_ERROR", lang))
                log_to_file("VOTING ({}): {}".format(e, embed.to_dict()))
                return

            # Actually end the voting
            self.vote.end_voting(message.server)

        # !vote status
        elif startswith(prefix + "vote status"):
            if not self.vote.in_progress(message.server):
                await client.send_message(message.channel, trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            header = self.vote.get_vote_title(message.server.id)
            votes = sum(self.vote.get_votes(message.server.id).values())

            if votes == 0:
                vote_disp = trans.get("MSG_VOTING_S_NONE", lang)
            elif votes == 1:
                vote_disp = trans.get("MSG_VOTING_S_ONE", lang)
            else:
                vote_disp = trans.get("MSG_VOTING_S_MULTI", lang).format(votes)

            await client.send_message(message.channel, trans.get("MSG_VOTING_STATUS", lang).format(header, vote_disp))

        # !vote
        elif startswith(prefix + "vote"):
            # Ignore if there is no vote going on instead of getting an exception
            if not self.vote.in_progress(message.server):
                return

            # Get the choice, but tell the author if he/she didn't supply a number
            try:
                choice = int(message.content[len(prefix + "vote "):]) - 1
            except ValueError:
                m = await client.send_message(message.channel, trans.get("MSG_VOTING_NOT_NUMBER", lang))
                await asyncio.sleep(1.5)
                await client.delete_message(m)
                return

            if choice < 0:
                return

            res = self.vote.plus_one(choice, message.author.id, message.server)

            if res == -1:
                msg = await client.send_message(message.channel, trans.get("MSG_VOTING_CHEATER", lang))

                await asyncio.sleep(1)
                await client.delete_message(msg)

            elif res:
                await client.add_reaction(message, OK_EMOJI)

            else:
                msg = await client.send_message(message.channel, trans.get("MSG_VOTING_SOMETHING_WRONG", lang))

                await asyncio.sleep(1)
                await client.delete_message(msg)

            self.stats.add(VOTE)


class NanoPlugin:
    name = "Voting"
    version = "0.2.5"

    handler = Vote
    events = {
        "on_message": 10,
        # type : importance
    }
