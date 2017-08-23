# coding=utf-8
import logging
import time
import re
from datetime import timedelta, datetime
from random import randint

from discord import Embed, Forbidden, utils

from data.stats import MESSAGE, PING
from data.utils import is_valid_command, add_dots

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

#####
# Commons plugin
# Mostly simple commands like !ping and !quote
#####

MAX_DICE_EXPR = 50
MAX_DICE = 1000

quotes = [
    "You miss 100% of the shots you don’t take. –Wayne Gretzky",
    "The most difficult thing is the decision to act, the rest is merely tenacity. –Amelia Earhart",
    "Twenty years from now you will be more disappointed by the things that you didn’t do than by the ones you did do, so throw off the bowlines, sail away from safe harbor, catch the trade winds in your sails.  Explore, Dream, Discover. –Mark Twain",
    "Life is 10% what happens to me and 90% of how I react to it. –Charles Swindoll",
    "Eighty percent of success is showing up. –Woody Allen",
    "The best time to plant a tree was 20 years ago. The second best time is now. –Chinese Proverb",
    "Winning isn’t everything, but wanting to win is. –Vince Lombardi",
    "I’ve learned that people will forget what you said, people will forget what you did, but people will never forget how you made them feel. –Maya Angelou",
    "The two most important days in your life are the day you are born and the day you find out why. –Mark Twain",
    "People often say that motivation doesn’t last. Well, neither does bathing.  That’stm why we recommend it daily. –Zig Ziglar",
    "Everything you’ve ever wanted is on the other side of fear. –George Addair",
    "We can easily forgive a child who is afraid of the dark; the real tragedy of life is when men are afraid of the light. –Plato",
    "When I was 5 years old, my mother always told me that happiness was the key to life.  When I went to school, they asked me what I wanted to be when I grew up.  I wrote down ‘happy’.  They told me I didn’t understand the assignment, and I told them they didn’t understand life. –John Lennon",
    "When one door of happiness closes, another opens, but often we look so long at the closed door that we do not see the one that has been opened for us. –Helen Keller",
    "Life is not measured by the number of breaths we take, but by the moments that take our breath away. –Maya Angelou",
    "Too many of us are not living our dreams because we are living our fears. –Les Brown",
    "I didn’t fail the test. I just found 100 ways to do it wrong. –Benjamin Franklin",
    "A person who never made a mistake never tried anything new. –Albert Einstein",
    "A truly rich man is one whose children run into his arms when his hands are empty. –Unknown",
    "If you want your children to turn out well, spend twice as much time with them, and half as much money. –Abigail Van Buren",
    "It does not matter how slowly you go as long as you do not stop. –Confucius",
    "You can’t use up creativity.  The more you use, the more you have. –Maya Angelou",
    "Do what you can, where you are, with what you have. –Teddy Roosevelt",
    "You may be disappointed if you fail, but you are doomed if you don’t try. –Beverly Sills",
    "The human race has one really effective weapon, and that is laughter. –Mark Twain",
    "A great artist can paint a great picture on a small canvas. –Charles Dudley Warner",
    "The present time has one advantage over every other - it is our own. –Charles Caleb Colton",
    "Age does not protect you from love. But love, to some extent, protects you from age. –Anais Nin",
    "A fool can throw a stone in a pond that 100 wise men can not get out. –Saul Bellow",
    "The secret of happiness is something to do. –John Burroughs"]

commands = {
    "_hello": {"desc": "Welcomes a **mentioned** person, or if no mentions are present, you.", "use": "[command] [mention]"},
    "_uptime": {"desc": "Tells you for how long I have been running."},
    "_github": {"desc": "Link to my project on GitHub."},
    "_ping": {"desc": "Just to check if I'm alive. fyi: I love ping-pong."},
    "_roll": {"desc": "Replies with a random number in range from 0 to your number.", "use": "[command] [number]", "alias": "_rng"},
    "_rng": {"desc": "Replies with a random number in range from 0 to your number.", "use": "[command] [number]", "alias": "_roll"},
    "_dice": {"desc": "Rolls the dice\nDice expression example: `5d6` - rolls five dices with six sides, `1d9` - rolls one dice with nine sides", "use": "[command] [dice expression]"},
    "_decide": {"desc": "Decides between different choices so you don't have to.", "use": "[command] word1|word2|word3|..."},
    "_8ball": {"desc": "Answers your questions. 8ball style.", "use": "[command] [question]"},
    "_quote": {"desc": "Brightens your day with a random quote."},
    "_invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "alias": "nano.invite"},
    "nano.invite": {"desc": "Gives you a link to invite Nano to another (your) server.", "alias": "_invite"},
    "_avatar": {"desc": "Gives you the avatar url of a mentioned person", "use": "[command] [mention or name]"},
    "_say": {"desc": "Says something (#channel is optional)", "use": "[command] (#channel) [message]"},
    "nano.info": {"desc": "A little info about me.", "alias": "_ayybot"},
    "_nano": {"desc": "A little info about me.", "alias": "nano.info"},
}

valid_commands = commands.keys()


# Utility for non-failable get operator
def l_get(lst, index, fallback=None):
    return lst[index] if len(lst) > index else fallback


class Parser:
    def __init__(self):
        # Used to capture parsing groups
        self.pt = re.compile(r"({(?:[0-9a-z]+[|]?)+})")

    def _split_groups(self, text):
        text_list = []

        # Splits the text on every group in the match
        c_ind = 0
        gr = self.pt.finditer(text)
        for m in gr:
            st = m.start()
            en = m.end()

            text_list.append(text[c_ind:st])
            text_list.append(text[st:en])
            c_ind = en

        return text_list

    def _verify_groups(self, groups):
        # TODO implement
        raise NotImplementedError

    @staticmethod
    def _parse_group(group, ctx):
        name, *tokens = group.split("|")
        first = tokens[0]

        # Actually gets the result
        # whole system in this function because of performance
        # Assumes groups have been verified with _verify_groups

        # 1. Author stuff
        if name == "author":
            if first == "name":
                return ctx.author.display_name
            if first == "id":
                return ctx.author.id
            if first == "mention":
                return ctx.author.mention
            if first == "discrim":
                return ctx.author.discriminator
            if first == "avatar":
                return ctx.author.avatar_url or ctx.author.default_avatar_url
            else:
                return ctx.author.name

        # 2. Mention stuff
        elif name == "mention":
            # first == index
            typ = tokens[2]

            if typ == "name":
                return ctx.mentions[first].display_name
            if typ == "id":
                return ctx.mentions[first].id
            if typ == "mention":
                return ctx.mentions[first].mention
            if typ == "discrim":
                return ctx.mentions[first].discriminator
            if typ == "avatar":
                return ctx.mentions[first].avatar_url or ctx.mentions[first].default_avatar_url
            else:
                return ctx.mentions[first].name

        # 3. Random numbers
        elif name == "rnd":
            # from is first
            # to is the second item (index 1)
            to = l_get(tokens, 1)

            # Two arguments
            if to:
                # Assumes both arguments can be ints
                return randint(int(first), int(to))
            # Only one
            else:
                # Assumes argument is int
                return randint(0, int(first))


    def parse(self, text, ctx):
        ls = self._split_groups(text)

        for ind, t in enumerate(ls):
            if t:
                if (t[0] == "{") and (t[-1] == "}"):
                    # valid group, parse
                    # Cut out { and }
                    ls[ind] = str(self._parse_group(t[1:-1], ctx))

        return "".join(ls)


class Commons:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        self.pings = {}
        self.getter = None
        self.resolve_user = None

        self.parser = Parser()

    async def on_plugins_loaded(self):
        self.getter = self.nano.get_plugin("server").get("instance")
        self.resolve_user = self.nano.get_plugin("admin").get("instance").resolve_user

    async def log_say_command(self, message, content, prefix, lang):
        log_channel = await self.getter.handle_log_channel(message.guild)

        if not log_channel:
            return

        embed = Embed(title=self.trans.get("MSG_LOGPOST_SAY", lang).format(prefix), description=add_dots(content, 350))
        embed.set_author(name="{} ({})".format(message.author.name, message.author.id), icon_url=message.author.avatar_url)
        embed.add_field(name=self.trans.get("INFO_CHANNEL", lang), value=message.channel.mention)

        await log_channel.send(embed=embed)

    @staticmethod
    def at_everyone_filter(content, author, force_remove=False):
        # See if the user is allowed to do @everyone
        # Removes mentions if user doesn't have the permission to mention
        if not author.guild_permissions.mention_everyone or force_remove is True:
            content = str(content).replace("@everyone", "").replace("@here", "")

        return content

    async def on_message(self, message, **kwargs):
        client = self.client
        trans = self.trans

        prefix = kwargs.get("prefix")
        lang = kwargs.get("lang")

        # Custom commands registered for the server
        server_commands = self.handler.get_custom_commands(message.guild.id)

        if server_commands:
            # Checks for server specific commands
            for command in server_commands.keys():
                # UPDATE 2.1.4: not .startswith anymore!
                if message.content == command:
                    await message.channel.send(server_commands.get(command))
                    self.stats.add(MESSAGE)

                    return

        # TODO test this thoroughly
        # if server_commands:
        #     # According to tests, .startswith is faster than slicing, wtf
        #     pass
        #
        #     for k in server_commands.keys():
        #         if message.content.startswith(k):
        #             raw_resp = server_commands[k]
        #             response = self.parser.parse(raw_resp, message)
        #
        #             print("response")
        #             print(response)
        #
        #             await message.channel.send(response)
        #
        #             return


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

        # COMMANDS

        # !hello
        if startswith(prefix + "hello"):
            argument = message.content[len(prefix + "hello "):]

            # Parse mentions or name
            if argument:
                if len(message.mentions) > 0:
                    mention = message.mentions[0].mention
                else:
                    # Find user
                    usr = utils.find(lambda a: a.name == argument, message.guild.members)
                    if not usr:
                        mention = message.author.mention
                    else:
                        mention = usr.mention
            else:
                mention = message.author.mention

            if len(message.mentions) >= 1:
                await message.channel.send(trans.get("INFO_HI", lang).format(mention))
            elif len(message.mentions) == 0:
                await message.channel.send(trans.get("INFO_HI", lang).format(mention))

        # !uptime
        elif startswith(prefix + "uptime"):
            d = datetime(1, 1, 1) + timedelta(seconds=time.time() - self.nano.boot_time)
            uptime = trans.get("MSG_UPTIME", lang).format(d.day - 1, d.hour, d.minute, d.second)

            await message.channel.send(uptime)

        # !nano, nano.info
        elif startswith((prefix + "nano", "nano.info")):
            await message.channel.send(trans.get("INFO_GENERAL", lang).format(p=prefix, ver=self.nano.version))

        # !github
        elif startswith(prefix + "github"):
            await message.channel.send(trans.get("INFO_GITHUB", lang))

        # !roll [number]
        elif startswith(prefix + "roll", prefix + "rng "):
            if startswith(prefix + "roll"):
                num = message.content[len(prefix + "roll "):]
            else:
                num = message.content[len(prefix + "rng "):]

            if not num.isnumeric():
                await message.channel.send(trans.get("ERROR_NOT_NUMBER", lang))
                return

            rn = randint(0, int(num))
            result = "**{}**. {}".format(rn, "**GG**" if rn == int(num) else "")

            await message.channel.send(trans.get("MSG_ROLL", lang).format(message.author.mention, result))

        # !dice [dice expression: 5d6 + 1d8]
        elif startswith(prefix + "dice"):
            cut = message.content[len(prefix + "dice "):]

            # Defaults to a normal dice
            if not cut:
                dice_types = ["1d6"]
            else:
                dice_types = [a.strip(" ") for a in cut.split("+")]

            # To prevent lag
            if len(dice_types) > MAX_DICE_EXPR:
                await message.channel.send(trans.get("MSG_DICE_TOO_MANY", lang).format(MAX_DICE_EXPR))
                return

            results = []
            tt = 0
            for dice in dice_types:
                try:
                    times, sides = dice.split("d")
                    times, sides = int(times), int(sides)
                except ValueError:
                    await message.channel.send(trans.get("MSG_DICE_INVALID", lang))
                    return

                if times > MAX_DICE or sides > MAX_DICE:
                    await message.channel.send(trans.get("MSG_DICE_TOO_BIG", lang).format(MAX_DICE))
                    return

                total = 0
                for _ in range(times):
                    total += randint(1, sides)

                tt += total

                results.append(trans.get("MSG_DICE_ENTRY", lang).format(dice, total))

            await message.channel.send(trans.get("MSG_DICE_RESULTS", lang).format(message.author.mention, "\n".join(results), tt))

        # !ping
        elif startswith(prefix + "ping"):
            base_time = datetime.now() - message.created_at
            base_taken = int(divmod(base_time.total_seconds(), 60)[1] * 1000)

            a = await message.channel.send(trans.get("MSG_PING_MEASURING", lang))
            self.pings[a.id] = [time.monotonic(), a, base_taken]

            # Thumbs up
            await a.add_reaction("\U0001F44D")
            self.stats.add(PING)

        # !decide [item1]|[item2]|etc...
        elif startswith(prefix + "decide"):
            cut = str(message.content)[len(prefix + "decide "):].strip(" ")

            if not cut:
                await message.channel.send(trans.get("MSG_DECIDE_NO_ARGS", lang))
                return

            # If | is not used, try spaces
            options = cut.split("|")
            if len(options) == 1:
                options = cut.split(" ")

            if len(options) == 1:
                await message.channel.send(trans.get("MSG_DECIDE_SPECIAL", lang).format(cut))

            else:
                rn = randint(0, len(options) - 1)
                await message.channel.send(trans.get("MSG_DECIDE_NORMAL", lang).format(options[rn]))

        # !8ball
        elif startswith(prefix + "8ball"):
            eight_ball = [a.strip(" ") for a in trans.get("MSG_8BALL_STRINGS", lang).split("|")]
            answer = eight_ball[randint(0, len(eight_ball) - 1)]

            await message.channel.send(trans.get("MSG_8BALL", lang).format(answer))

        # !quote
        elif startswith(prefix + "quote"):
            chosen = str(quotes[randint(0, len(quotes) - 1)])

            # Find the part where the author is mentioned
            place = chosen.rfind("–")
            await message.channel.send("{}\n- __{}__".format(chosen[:place], chosen[place+1:]))

        # !invite
        elif startswith(prefix + "invite", "nano.invite"):
            # ONLY FOR TESTING - if nano beta is active
            if startswith("nano.invite.make_real"):
                application = await client.application_info()

                # Most of the permissions that Nano uses
                perms = "1543765079"
                url = "<https://discordapp.com/oauth2/" \
                      "authorize?client_id={}&scope=bot&permissions={}>".format(application.id, perms)

                await message.channel.send(trans.get("INFO_INVITE", lang).replace("<link>", url))
                return

            await message.channel.send(trans.get("INFO_INVITE", lang).replace("<link>", "<http://invite.nanobot.pw>"))

        # !avatar
        elif startswith(prefix + "avatar"):
            name = message.content[len(prefix + "avatar "):]

            if not name:
                member = message.author
            else:
                member = await self.resolve_user(name, message, lang)

            url = member.avatar_url

            if url:
                await message.channel.send(trans.get("MSG_AVATAR_OWNERSHIP", lang).format(member.name, url))
            else:
                await message.channel.send(trans.get("MSG_AVATAR_NONE", lang).format(member.name))

        # !say (#channel) [message]
        elif startswith(prefix + "say"):
            if not self.handler.is_mod(message.author, message.guild):
                await message.channel.send(trans.get("PERM_MOD", lang))
                return "return"

            content = str(message.content[len(prefix + "say "):]).strip(" ")

            if not content:
                await message.channel.send(trans.get("ERROR_INVALID_CMD_ARGUMENTS", lang))
                return

            if len(message.channel_mentions) != 0:
                channel = message.channel_mentions[0]
                content = content.replace(channel.mention, "").strip(" ")
            else:
                channel = message.channel

            content = self.at_everyone_filter(content, message.author)

            try:
                await channel.send(content)
                await self.log_say_command(message, content, prefix, lang)
            except Forbidden:
                await message.channel.send(trans.get("MSG_SAY_NOPERM", lang).format(channel.id))

    async def on_reaction_add(self, reaction, _, **kwargs):
        if reaction.message.id in self.pings.keys():
            # Message data: list(initial_time, message, taken_time)
            msg_data = self.pings.pop(reaction.message.id)
            lang = kwargs.get("lang")

            delta = round((time.monotonic() - int(msg_data[0])) * 100, 2)
            # Message object
            msg = msg_data[1]

            await msg.edit(content=self.trans.get("MSG_PING_RESULT", lang).format(msg_data[2], delta))
            await msg.clear_reactions()


class NanoPlugin:
    name = "Common Commands"
    version = "26"

    handler = Commons
    events = {
        "on_message": 10,
        "on_reaction_add": 10,
        "on_plugins_loaded": 5,
        # type : importance
    }
