# coding=utf-8
import asyncio
import logging

try:
    from rapidjson import loads, dumps
except ImportError:
    from json import loads, dumps

from discord import Embed, Colour, errors

from core.stats import MESSAGE, VOTE, WRONG_PERMS
from core.utils import is_valid_command, log_to_file, decode, add_dots, filter_text

__author__ = "DefaltSimon"
# Voting plugin

commands = {
    "_poll": {"desc": "A group of commands designed to handle poll creation and managment.\nSubcommands: `start`, `end`, `status`", "use": "[command] [subcommand]"},
    "_poll start": {"desc": "Starts a poll on the server.", "use": "[command] \"question\" choice1|choice2|..."},
    "_poll end": {"desc": "Simply ends the current poll on the server."},
    "_poll status": {"desc": "Shows info about the current poll."},
    "_vote": {"desc": "Votes for an option if there is voting going on.", "use": "[command] [1,2,3,...]"},
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

        # !poll start
        # Arguments: "[title]" [option1]|(option2)|...
        # OR       : "[title]" [option1],(option2),...
        if startswith(prefix + "poll start"):
            if not await self.handler.is_admin(message.author, message.guild):
                await message.channel.send(trans.get("PERM_ADMIN", lang))
                self.stats.add(WRONG_PERMS)
                return

            if self.vote.in_progress(message.guild.id):
                await message.channel.send(trans.get("MSG_VOTING_IN_PROGRESS", lang))
                return

            arguments = message.content[len(prefix + "poll start "):].strip(" ")
            if not arguments:
                await message.channel.send(trans.get("MSG_VOTING_I_USAGE", lang).format(prefix))
                return

            # TITLE
            # Handle short_title, "longer title", 'also like this'
            if arguments[0] == "\"":
                _, title, arguments = arguments.split("\"", maxsplit=3)
            elif arguments[0] == "'":
                _, title, arguments = arguments.split("'", maxsplit=3)
            else:
                title, arguments = arguments.split(" ", maxsplit=1)

            arguments = arguments.lstrip(" ")


            # CHOICES
            # | as separator
            if "|" in arguments:
                items = [a.strip(" ") for a in arguments.split("|") if a]
            # , used as separator
            else:
                items = [a.strip(" ") for a in arguments.split(",") if a]

            # Send an error if there's only a title
            if len(items) < 2:
                await message.channel.send(trans.get("MSG_VOTING_NEED_OPTIONS", lang).format(prefix))
                return
            # END OF ARGUMENT PARSING


            # Check item amount
            if len(items) > VOTE_ITEM_LIMIT:
                await message.channel.send(trans.get("MSG_VOTING_OPTIONS_TM", lang).format(VOTE_ITEM_LIMIT, len(items)))
                return

            # Check total length
            if (len(title) + sum([len(a) for a in items])) > VOTE_ITEM_MAX_LENGTH:
                await message.channel.send(trans.get("MSG_VOTING_OPTIONS_TL ", lang).format(VOTE_ITEM_MAX_LENGTH, sum([len(a) for a in items])))
                return

            # Check if any option is empty
            if any(e == "" for e in items):
                await message.channel.send(trans.get("MSG_VOTING_EMPTY_ITEM", lang))
                return

            # Filter text (remove @ everyone, etc)
            title, items = filter_text(title), [filter_text(i) for i in items]

            self.vote.start_vote(message.author.id, message.guild.id, title, items)

            # Generates a list of options to show
            choices = "\n\n".join(["[{}]\n{}".format(en + 1, ch) for en, ch in
                                   enumerate(self.vote.get_choices(message.guild.id))])

            await message.channel.send(trans.get("MSG_VOTING_STARTED", lang).format(title, choices))

        # !poll end
        elif startswith(prefix + "poll end"):
            if not await self.handler.is_admin(message.author, message.guild):
                await message.channel.send(trans.get("PERM_ADMIN", lang))
                self.stats.add(WRONG_PERMS)
                return

            if not self.vote.in_progress(message.guild.id):
                await message.channel.send(trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            # Wait for confirmation
            msg = await message.channel.send(trans.get("MSG_VOTING_END_CONFIRMATION", lang).format(OK_EMOJI))
            await msg.add_reaction(OK_EMOJI)

            def check(reaction, user):
                return user == message.author and str(reaction.emoji) == OK_EMOJI

            try:
                await self.client.wait_for('reaction_add', timeout=45, check=check)
            except asyncio.TimeoutError:
                await message.channel.send(trans.get("MSG_VOTING_END_ABORT", lang))
                return

            await msg.delete()

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
                await message.channel.send(trans.get("MSG_VOTING_ENDED", lang) + "\n", embed=embed)
            except errors.HTTPException as e:
                await message.channel.send(trans.get("MSG_VOTING_ERROR", lang))
                log_to_file("VOTING ({}): {}".format(e, embed.to_dict()), "bug")

        # !poll status
        elif startswith(prefix + "poll status"):
            if not self.vote.in_progress(message.guild.id):
                await message.channel.send(trans.get("MSG_VOTING_NO_PROGRESS", lang))
                return

            header = filter_text(self.vote.get_title(message.guild.id))
            votes = sum(self.vote.get_votes(message.guild.id).values())

            if votes == 0:
                vote_disp = trans.get("MSG_VOTING_S_NONE", lang)
            elif votes == 1:
                vote_disp = trans.get("MSG_VOTING_S_ONE", lang)
            else:
                vote_disp = trans.get("MSG_VOTING_S_MULTI", lang).format(votes)

            await message.channel.send(trans.get("MSG_VOTING_STATUS", lang).format(header, vote_disp))

        # !vote
        elif startswith(prefix + "vote"):
            # Ignore if there is no vote going on instead of getting an exception
            if not self.vote.in_progress(message.guild.id):
                await message.add_reaction(X_EMOJI)

                msg = await message.channel.send(trans.get("MSG_VOTING_NO_PROGRESS", lang))
                await asyncio.sleep(2)
                await msg.delete()

                return

            # Get the choice, but tell the author if he/she didn't supply a number
            try:
                choice = int(message.content[len(prefix + "vote "):]) - 1
            # Cannot convert to int
            except ValueError:
                await message.add_reaction(BLOCK_EMOJI)

                m = await message.channel.send(trans.get("MSG_VOTING_NOT_NUMBER", lang))
                await asyncio.sleep(2)
                await m.delete()
                return

            res = self.vote.plus_one(choice, message.author.id, message.guild.id)

            # User already voted
            if res == -1:
                await message.add_reaction(BLOCK_EMOJI)

                msg = await message.channel.send(trans.get("MSG_VOTING_CHEATER", lang))
                await asyncio.sleep(2)
                await msg.delete()

            # No such option
            elif not res:
                await message.add_reaction(X_EMOJI)

                msg = await message.channel.send(trans.get("MSG_VOTING_INVALID_NUMBER", lang))
                await asyncio.sleep(2)
                await msg.delete()

            # Everything ok, was added
            else:
                await message.add_reaction(OK_EMOJI)

            self.stats.add(VOTE)


class NanoPlugin:
    name = "Voting"
    version = "28"

    handler = Vote
    events = {
        "on_message": 10,
        # type : importance
    }
