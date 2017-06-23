# coding=utf-8
import configparser
import logging

import steamapi
from discord import Message, HTTPException

from data.stats import MESSAGE, WRONG_ARG
from data.utils import is_valid_command, reraise

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = configparser.ConfigParser()
parser.read("plugins/config.ini")


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
    async def get_user(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user
        except steamapi.errors.UserNotFoundError:
            return None
        except ValueError:
            raise ValueError

    @staticmethod
    async def get_friends(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [friend.name for friend in user.friends]
        except steamapi.errors.UserNotFoundError:
            return None, None
        except ValueError:
            raise ValueError

    @staticmethod
    async def get_games(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [game.name for game in user.games]
        except steamapi.errors.UserNotFoundError:
            return None, None
        except ValueError:
            raise ValueError

    @staticmethod
    async def get_owned_games(uid):
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
        self.trans = kwargs.get("trans")

        key = parser.get("steam", "key")
        self.steam = SteamSearch(key)

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
                    await client.send_message(message.channel, trans.get("MSG_STEAM_INVALID_URL", lang))
                    return
                except (steamapi.errors.APIFailure, steamapi.errors.APIException):
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE", lang))
                    reraise()
                    return

                if not username:
                    await client.send_message(message.channel, trans.get("ERROR_NO_USER2", lang))
                    self.stats.add(WRONG_ARG)
                    return

                if not friends:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE_FRIENDS", lang))
                    self.stats.add(WRONG_ARG)
                    return

                friends = ["`" + friend + "`" for friend in friends]

                await client.send_message(message.channel, trans.get("MSG_STEAM_FRIENDS", lang).format(username, ", ".join(friends)))

            elif startswith(prefix + "steam games"):
                uid = str(message.content)[len(prefix + "steam games "):]

                # Game search
                await client.send_typing(message.channel)

                try:
                    username, games = self.steam.get_owned_games(uid)
                except ValueError:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_INVALID_URL", lang))
                    return
                except (steamapi.errors.APIFailure, steamapi.errors.APIException):
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE", lang))
                    reraise()
                    return

                if not username:
                    await client.send_message(message.channel, trans.get("ERROR_NO_USER2", lang))
                    self.stats.add(WRONG_ARG)
                    return

                if not games:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE_GAMES", lang))
                    self.stats.add(WRONG_ARG)
                    return

                games = ["`{}`".format(game) for game in games]

                try:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_GAMES", lang).format(username, ", ".join(games)))
                except HTTPException:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_GAMES_TOO_MANY", lang))

            elif startswith(prefix + "steam user "):
                uid = str(message.content)[len(prefix + "steam user "):]

                # Basic search
                await client.send_typing(message.channel)

                try:
                    steam_user = self.steam.get_user(uid)
                except ValueError:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_INVALID_URL", lang))
                    return
                except (steamapi.errors.APIFailure, steamapi.errors.APIException):
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE", lang))
                    reraise()
                    return

                if not steam_user:
                    await client.send_message(message.channel, trans.get("ERROR_NO_USER2", lang))
                    self.stats.add(WRONG_ARG)
                    return

                state = trans.get("MSG_STEAM_ONLINE", lang) if steam_user.state else trans.get("MSG_STEAM_OFFLINE", lang)

                try:
                    info = trans.get("MSG_STEAM_USER_INFO", lang).format(steam_user.name, state, steam_user.level, len(steam_user.games), len(steam_user.friends), uid)
                except AttributeError:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_PRIVATE", lang))
                    return

                if len(info) > 2000:
                    await client.send_message(message.channel, trans.get("MSG_STEAM_FRIENDS_TOO_MANY", lang))

                else:
                    await client.send_message(message.channel, info)

            elif startswith(prefix + "steam") or startswith(prefix + "steam help"):
                await client.send_message(message.channel, trans.get("MSG_STEAM_HELP", lang).replace("_", prefix))


class NanoPlugin:
    name = "Steam Commands"
    version = "0.2.1"

    handler = Steam
    events = {
        "on_message": 10
        # type : importance
    }
