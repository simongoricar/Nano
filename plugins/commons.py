# coding=utf-8
import logging
import time

from datetime import timedelta, datetime
from random import randint
from discord import Message, utils
from data.serverhandler import ServerHandler
from data.stats import MESSAGE, PING
from data.utils import is_valid_command

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Strings

nano_info = """**Hey! My name is Nano!**
I have a GitHub repo! `!github`
My current version is **<version>**.
I have been coded by *DefaltSimon*."""

nano_github = """Nano's code is being maintained and updated on **GitHub**: https://github.com/DefaltSimon/Nano"""

invite = """You wanna invite Nano to your server, eh? Sure.
**Just follow the link:** <link>"""

eight_ball = [
    "It is certain", "It is surely so", "Without a doubt", "You may rely on it", "Most likely", "Yes",
    "Ask again later", "Cannot predict now", "Concentrate and ask again", "I would say yes", "JUST DO IT",
    "My reply is no", "My sources say no", "Signs point to yes"]

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
    "You may be disappointed if you fail, but you are doomed if you don’t try. –Beverly Sills"]

valid_commands = [
    "_hello", "_uptime", "_github", "_roll", "_dice", "_ping", "_decide", "_8ball",
    "_quote", "_invite", "_avatar", "_say", "nano.info", "_nano", "_invite", "nano.invite"
]

# Common commands plugin


class Commons:
    def __init__(self, **kwargs):
        self.client = kwargs.get("client")
        self.loop = kwargs.get("loop")
        self.handler = kwargs.get("handler")
        self.nano = kwargs.get("nano")
        self.stats = kwargs.get("stats")

        assert isinstance(self.handler, ServerHandler)

    async def on_message(self, message, **kwargs):
        # Things
        assert isinstance(message, Message)
        client = self.client

        # Prefixes
        prefix = kwargs.get("prefix")

        # Custom commands registered for the server
        server_commands = self.handler.get_custom_commands(message.channel.server)

        # Checks for server specific commands
        for command in server_commands:
            if str(message.content).startswith(command):
                # Maybe same replacement logic in the future update?
                # /todo implement advanced replacement logic
                await client.send_message(message.channel, server_commands.get(command))
                self.stats.add(MESSAGE)

                return

        if not is_valid_command(message.content, valid_commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        # A shortcut
        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        # COMMANDS

        # !hello
        if startswith(prefix + "hello"):
            if len(message.mentions) >= 1:
                await client.send_message(message.channel, "Hi " + message.mentions[0].mention)
            elif len(message.mentions) == 0:
                await client.send_message(message.channel, "Hi " + message.author.mention)

        # !uptime
        elif startswith(prefix + "uptime"):
            d = datetime(1, 1, 1) + timedelta(seconds=time.time() - self.nano.boot_time)
            uptime = "I have been tirelessly answering people for\n" \
                     "**{} days, {} hours, {} minutes and {} seconds!**".format(d.day - 1, d.hour, d.minute, d.second)

            await client.send_message(message.channel, uptime)

        # !nano, nano.info
        elif startswith((prefix + "nano", "nano.info")):
            await client.send_message(message.channel, nano_info.replace("<version>", self.nano.version))

        # !github
        elif startswith(prefix + "github"):
            await client.send_message(message.channel, nano_github)

        # !roll
        elif startswith((prefix + "roll", prefix + "rng")):
            if startswith(prefix + "roll"):
                num = message.content[len(prefix + "roll "):]
            else:
                num = message.content[len(prefix + "rng "):]

            if not str(num).isnumeric():
                await client.send_message(message.channel, "Not a number.")
                return

            rn = randint(0, int(num))
            result = "**{}**. {}".format(rn, "**GG**" if rn == int(num) else "")

            await client.send_message(message.channel, "{}, you rolled {}".format(message.author.mention, result))

        # !dice
        elif startswith(prefix + "dice"):
            rn = randint(1, 6)
            await client.send_message(message.channel, "{}, the dice shows... **{}**".format(message.author.mention, rn))

        # !ping
        elif startswith(prefix + "ping"):
            await client.send_message(message.channel, "**Pong!**")

            self.stats.add(PING)

        # !decide
        elif startswith(prefix + "decide"):
            cut = str(message.content)[len(prefix + "decide "):]

            if len(cut.split("|")) == 1:
                await client.send_message(message.channel, "Guess what? It's " + str(cut) + ". **ba dum tss.**")

            else:
                split = cut.split("|")
                rn = randint(0, len(split) - 1)
                await client.send_message(message.channel, "**drum roll**... I have decided: {}".format(split[rn]))

        # !8ball
        elif startswith(prefix + "8ball"):
            answer = eight_ball[randint(0, len(eight_ball) - 1)]
            await client.send_message(message.channel, "The magic 8ball says: *{}*.".format(answer))

        # !quote
        elif startswith(prefix + "quote"):
            chosen = str(quotes[randint(0, len(quotes) - 1)])

            # Find the part where the author is mentioned
            place = chosen.rfind("–")
            await client.send_message(message.channel, "{}\n__{}__".format(chosen[:place], chosen[place:]))

        # !invite
        elif startswith(prefix + "invite", "nano.invite"):
            application = await client.application_info()

            # Most of the permissions that Nano uses
            perms = str("0x510917638")
            url = "https://discordapp.com/oauth2/" \
                  "authorize?client_id={}&scope=bot&permissions={}".format(application.id, perms)

            await client.send_message(message.channel, invite.replace("<link>", url))

        # !avatar
        elif startswith(prefix + "avatar"):
            # Selects the proper user
            if len(message.mentions) == 0:
                name = str(str(message.content)[len(prefix + "avatar "):])
                member = utils.find(lambda m: m.name == name, message.channel.server.members)
            else:
                member = message.mentions[0]

            if not member:
                member = message.author

            url = member.avatar_url

            if url:
                await client.send_message(message.channel, "**{}**'s avatar: {}".format(member.name, url))
            else:
                await client.send_message(message.channel,
                                          "**{}** does not have an avatar. :expressionless:".format(member.name))

        # !say
        elif startswith(prefix + "say"):
            content = message.content[len(prefix + "say "):]

            # See if the user is allowed to do @everyone
            ok = False
            for roles in message.author.roles:
                if roles.permissions.mention_everyone:
                    ok = True
                    break

            if message.channel.server.owner == message.author:
                ok = True

            # Filters if the author does not have permission to do @everyone
            await client.send_message(message.channel, content.replace("@", "") if not ok else content)


class NanoPlugin:
    _name = "Common Commands"
    _version = 0.1

    handler = Commons
    events = {
        "on_message": 10
        # type : importance
    }
