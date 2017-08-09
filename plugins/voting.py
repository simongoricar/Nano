# coding=utf-8
import asyncio
import logging

try:
    from ujson import loads, dumps
except ImportError:
    from json import loads, dumps

from discord import Embed, Colour, errors

from data.stats import MESSAGE, VOTE, WRONG_PERMS
from data.utils import is_valid_command, log_to_file, decode, add_dots

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

# OK_EMOJI = "\U0001F44D"
OK_EMOJI = "👍"
# X_EMOJI = "\U00002715"
X_EMOJI = "❌"
# BLOCK_EMOJI = "\U0001F4DB"
BLOCK_EMOJI = "📛"
# QUESTION_EMOJI = "\U0000003F"
QUESTION_EMOJI = "❔"

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class RedisVoteHandler:
    """
    Type: hash
    Namespace: voting:*

    Layout:

        voters: list(voter_ids)
        inprogress: bool
        title: string
        votes: json-encoded dict(index: amount)
        choices: json-encoded list(choices)
        author: int (author id)
    """
    def __init__(self, handler):
        self.redis = handler.get_plugin_data_manager(namespace="voting")

    def get_vote_amount(self) -> int:
        return len(self.redis.scan_iter("*"))

    def start_vote(self, author_id: int, server_id: int, title: str, choices: list):
        # Do not automatically overwrite
        if self.redis.exists(server_id):
            return False

        payload = {
            "author": author_id,
            "votes": dumps([0 for _ in range(len(choices))]),
            # Can safely be [] without using dumps()
            "voters": "[]",
            "title": str(title),
            "choices": dumps(choices),
            # no more inprogress, is pointless
        }

        return self.redis.hmset(server_id, payload)

    def in_progress(self, server_id):
        return self.redis.exists(server_id)

    def plus_one(self, o_index: int, user_id: int, server_id: int):
        """
        Adds a vote
        :return:
            -1 -> person already voted
            False -> no such option
            True -> everything is ok
        """
        if not self.in_progress(server_id):
            return False

        data = decode(self.redis.hgetall(server_id))
        voters, vote_counts, options = loads(data.get("voters")), loads(data.get("votes")), loads(data.get("choices"))

        # Missing option
        if o_index > len(options) -1:
            return False
        # Negative number
        if o_index < 0:
            return False

        # Add the voter to the list
        if user_id in voters:
            # Error: That person has already voted
            return -1
        else:
            voters.append(user_id)

        # Add +1 to option at index
        vote_counts[o_index] += 1

        # Choice list doesn't change
        payload = {
            "votes": dumps(vote_counts),
            "voters": dumps(voters),
        }

        return self.redis.hmset(server_id, payload)

    def get_votes(self, server_id) -> dict:
        """
        :return dict(vote_text: amount)
        """
        by_index = loads(self.redis.hget(server_id, "votes"))
        names = loads(self.redis.hget(server_id, "choices"))

        return {names[c]: amount for c, amount in enumerate(by_index)}

    def get_title(self, server_id):
        return self.redis.hget(server_id, "title")

    def get_choices(self, server_id: int) -> list:
        return loads(self.redis.hget(server_id, "choices"))

    def end_voting(self, server_id: int):
        return bool(self.redis.delete(server_id))


class Vote:
    def __init__(self, **kwargs):
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.vote = RedisVoteHandler(self.handler)

    async def on_message(self, message, **kwargs):
        client = self.client
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        # Check if this is a valid command
        if not is_valid_command(message.content, commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*matches):
            for match in matches:
                if message.content.startswith(match):
                    return True

            return False

        # !vote start [title]|[option1]|(option2)|...
        if startswith(prefix + "vote start"):
            if not self.handler.can_use_admin_commands(message.author, message.guild):
                await client.send_message(message.channel, trans.get("PERM_ADMIN", lang))
                self.stats.add(WRONG_PERMS)
                return

            if self.vote.in_progress(message.guild.id):
                await client.send_message(message.channel, trans.get("MSG_VOTING_IN_PROGRESS", lang))
                return

            arguments = message.content[len(prefix + "vote start "):].strip(" ")
            if not arguments:
                await client.send_message(message.channel, trans.get("MSG_VOTING_I_USAGE", lang).format(prefix))
                return

            s = arguments.split("|")

            # Minimal is the title and one choice
            if len(s) < 2:
                await client.send_message(message.channel, trans.get("MSG_VOTING_I_USAGE", lang).format(prefix))
                return

            title, *items = [a.strip(" ") for a in s]

            # Check item amount
            if len(items) > VOTE_ITEM_LIMIT:
                await client.send_message(message.channel, trans.get("MSG_VOTING_OPTIONS_TM", lang).format(VOTE_ITEM_LIMIT, len(items)))
                return

            # Check total length
            if (len(title) + sum([len(a) for a in items])) > VOTE_ITEM_MAX_LENGTH:
                await client.send_message(message.channel, trans.get("MSG_VOTING_OPTIONS_TL ", lang).format(VOTE_ITEM_MAX_LENGTH, sum([len(a) for a in items])))
                return

            # Check if any option is empty
            if any(e == "" for e in items):
                await client.send_message(message.channel, trans.get("MSG_VOTING_EMPTY_ITEM", lang))
                return

            self.vote.start_vote(message.author.id, message.guild.id, title, items)

            # Generates a list of options to show
            choices = "\n\n".join(["[{}]\n{}".format(en + 1, ch) for en, ch in
                            enumerate(self.vote.get_choices(message.guild.id))])

            await client.send_message(message.channel, trans.get("MSG_VOTING_STARTED", lang).format(title, choices))

        # !vote end
        elif startswith(prefix + "vote end"):
            if not self.handler.can_use_admin_commands(message.author, message.guild):
                await client.send_message(message.channel, trans.get("PERM_ADMIN", lang))
                self.stats.add(WRONG_PERMS)
                return

            if not self.vote.in_progress(message.guild.id):
                await client.send_message(message.channel, trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            votes = self.vote.get_votes(message.guild.id)
            title = self.vote.get_title(message.guild.id)

            total_votes = sum(votes.values())

            embed = Embed(title="**{}**".format(title), colour=Colour(0x303F9F), description=trans.get("MSG_VOTING_AMOUNT", lang).format(total_votes))

            for name, val in votes.items():
                # Zero-width space
                dotted = add_dots(name, max_len=240) or "\u200B"
                embed.add_field(name=dotted, value=trans.get("MSG_VOTING_AMOUNT2", lang).format(val))

            # Actually end the voting
            self.vote.end_voting(message.guild.id)

            try:
                await client.send_message(message.channel, trans.get("MSG_VOTING_ENDED", lang) + "\n", embed=embed)
            except errors.HTTPException as e:
                await client.send_message(message.channel, trans.get("MSG_VOTING_ERROR", lang))
                log_to_file("VOTING ({}): {}".format(e, embed.to_dict()), "bug")

        # !vote status
        elif startswith(prefix + "vote status"):
            if not self.vote.in_progress(message.guild.id):
                await client.send_message(message.channel, trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            header = self.vote.get_title(message.guild.id)
            votes = sum(self.vote.get_votes(message.guild.id).values())

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
            if not self.vote.in_progress(message.guild.id):
                return

            # Get the choice, but tell the author if he/she didn't supply a number
            try:
                choice = int(message.content[len(prefix + "vote "):]) - 1
            # Cannot convert to int
            except ValueError:
                # REWRITE test
                await message.add_reaction(BLOCK_EMOJI)

                m = await client.send_message(message.channel, trans.get("MSG_VOTING_NOT_NUMBER", lang))
                await asyncio.sleep(2)
                # REWRITE test
                await m.delete()
                return

            res = self.vote.plus_one(choice, message.author.id, message.guild.id)

            # User already voted
            if res == -1:
                # REWRITE test
                await message.add_reaction(BLOCK_EMOJI)

                msg = await client.send_message(message.channel, trans.get("MSG_VOTING_CHEATER", lang))
                await asyncio.sleep(2)
                # REWRITE test
                await msg.delete()

            # No such option
            elif not res:
                # REWRITE test
                await message.add_reaction(X_EMOJI)

                msg = await client.send_message(message.channel, trans.get("MSG_VOTING_INVALID_NUMBER", lang))
                await asyncio.sleep(2)
                # REWRITE test
                await msg.delete()

            # Everything ok, was added
            else:
                # REWRITE test
                await message.add_reaction(OK_EMOJI)

            self.stats.add(VOTE)


class NanoPlugin:
    name = "Voting"
    version = "25"

    handler = Vote
    events = {
        "on_message": 10,
        # type : importance
    }
