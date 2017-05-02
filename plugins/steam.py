# coding=utf-8
import steamapi
import configparser
import logging
from discord import Message, HTTPException
from data.utils import is_valid_command, StandardEmoji, reraise
from data.stats import MESSAGE, WRONG_ARG

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")

NOT_WHOLE_URL = "Please put in the **ending** of a (\"vanity\") URL, not the *entire* URL!"

commands = {
    "_steam": {"desc": "Searches for the specified steam id.\nSubcommands: 'steam user', 'steam games', 'steam friends'", "use": "[command] [end of user url/id]", "alias": None},
    "_steam user": {"desc": "Searches for general info about the user.", "use": "[command] [end of user url/id]", "alias": None},
    "_steam games": {"desc": "Searches for all owned games in user's account.", "use": "[command] [end of user url/id]", "alias": None},
    "_steam friends": {"desc": "Searches for all friends that the user has.", "use": "[command] [end of user url/id]", "alias": None},
    "_steam help": {"desc": "Displays help for all steam commands.", "use": "[command]", "alias": None},
}

valid_commands = commands.keys()


class SteamSearch:
    def __init__(self, api_key):
        steamapi.core.APIConnection(api_key=api_key)

    @staticmethod
    def get_user(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user
        except steamapi.errors.UserNotFoundError:
            return None
        except ValueError:
            raise ValueError

    @staticmethod
    def get_friends(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [friend.name for friend in user.friends]
        except steamapi.errors.UserNotFoundError:
            return None, None
        except ValueError:
            raise ValueError

    @staticmethod
    def get_games(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [game.name for game in user.games]
        except steamapi.errors.UserNotFoundError:
            return None, None
        except ValueError:
            raise ValueError

    @staticmethod
    def get_owned_games(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [game.name for game in user.owned_games]
        except steamapi.errors.UserNotFoundError:
            return None, None
        except ValueError:
            raise ValueError


class Steam:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")

        key = parser.get("steam", "key")
        self.steam = SteamSearch(key)

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

        if startswith(prefix + "steam"):
            if startswith(prefix + "steam friends "):
                uid = str(message.content)[len(prefix + "steam friends "):]

                # Friend search
                await client.send_typing(message.channel)
                try:
                    username, friends = self.steam.get_friends(uid)
                except ValueError:
                    await client.send_message(message.channel, NOT_WHOLE_URL)
                    return
                except steamapi.errors.APIFailure:
                    await client.send_message(message.channel, "Something went wrong. " + StandardEmoji.CRY)
                    reraise()
                    return

                if not username:
                    await client.send_message(message.channel, "User **does not exist**.")
                    self.stats.add(WRONG_ARG)
                    return

                if not friends:
                    await client.send_message(message.channel, "Could not fetch friends (probably because the user has a private profile.")
                    self.stats.add(WRONG_ARG)
                    return

                friends = ["`" + friend + "`" for friend in friends]

                await client.send_message(message.channel,
                                          "*User:* **{}**\n\n*Friends:* {}".format(username, ", ".join(friends)))

            elif startswith(prefix + "steam games"):
                uid = str(message.content)[len(prefix + "steam games "):]

                # Game search
                await client.send_typing(message.channel)

                try:
                    username, games = self.steam.get_owned_games(uid)
                except ValueError:
                    await client.send_message(message.channel, NOT_WHOLE_URL)
                    return
                except steamapi.errors.APIFailure:
                    await client.send_message(message.channel, "Something went wrong. " + StandardEmoji.CRY)
                    reraise()

                if not username:
                    await client.send_message(message.channel, "User **does not exist**.")
                    self.stats.add(WRONG_ARG)
                    return

                if not games:
                    await client.send_message(message.channel, "Could not fetch games (probably because the user has a private profile.")
                    self.stats.add(WRONG_ARG)
                    return

                games = ["`{}`".format(game) for game in games]

                try:
                    await client.send_message(message.channel,
                                              "*User:* **{}**:\n\n*Owned games:* {}".format(username, ", ".join(games)))
                except HTTPException:
                    await client.send_message(message.channel,
                                              "This message can not fit onto Discord: **user has too many games to display (lol)**")

            elif startswith(prefix + "steam user "):
                uid = str(message.content)[len(prefix + "steam user "):]

                # Basic search
                await client.send_typing(message.channel)

                try:
                    steam_user = self.steam.get_user(uid)
                except ValueError:
                    await client.send_message(message.channel, NOT_WHOLE_URL)
                    return

                if not steam_user:
                    await client.send_message(message.channel, "User **does not exist**.")
                    self.stats.add(WRONG_ARG)
                    return

                try:
                    info = "User: **{}**\n```css\nStatus: {}\nLevel: {}\nGames: {} owned (including free games)\nFriends: {}```\n" \
                           "Direct link: http://steamcommunity.com/id/{}/".format(steam_user.name, "Online" if steam_user.state else "Offline",
                                                                                  steam_user.level, len(steam_user.games), len(steam_user.friends), uid)
                except AttributeError:
                    await client.send_message(message.channel, "Could not display user info. This can happen when the user has a private profile. " + StandardEmoji.FROWN)
                    return

                if len(info) > 2000:
                    await client.send_message(message.channel,
                                              "This message can not fit onto Discord: **user has too many friends to display (lol)**")

                else:
                    await client.send_message(message.channel, info)

            elif startswith(prefix + "steam") or startswith(prefix + "steam help"):
                await client.send_message(message.channel,
                                          "**Steam commands:**\n`_steam user community_url`, `_steam friends community_url`, `_steam games community_url`".replace("_", prefix))


class NanoPlugin:
    name = "Steam Commands"
    version = "0.1.1"

    handler = Steam
    events = {
        "on_message": 10
        # type : importance
    }
