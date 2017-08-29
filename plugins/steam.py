# coding=utf-8
import logging

import steamapi
from discord import HTTPException

from data.stats import MESSAGE, WRONG_ARG
from data.utils import is_valid_command
from data.confparser import get_config_parser

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = get_config_parser()


commands = {
    "_steam": {"desc": "Searches for the specified steam id.\nSubcommands: 'steam user', 'steam games', 'steam friends'", "use": "[command] [end of user url/id]"},
    "_steam user": {"desc": "Searches for general info about the user.", "use": "[command] [end of user url/id]"},
    "_steam games": {"desc": "Searches for all owned games in user's account.", "use": "[command] [end of user url/id]"},
    "_steam friends": {"desc": "Searches for all friends that the user has.", "use": "[command] [end of user url/id]"},
    "_steam help": {"desc": "Displays help for all steam commands.", "use": "[command]"},
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

    @staticmethod
    async def get_friends(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [friend.name for friend in user.friends]
        except steamapi.errors.UserNotFoundError:
            return None, None

    @staticmethod
    async def get_games(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [game.name for game in user.games]
        except steamapi.errors.UserNotFoundError:
            return None, None

    @staticmethod
    async def get_owned_games(uid):
        try:
            user = steamapi.user.SteamUser(userurl=str(uid))
            return user.name, [game.name for game in user.owned_games]
        except steamapi.errors.UserNotFoundError:
            return None, None


class Steam:
    def __init__(self, **kwargs):
        self.nano = kwargs.get("nano")
        self.client = kwargs.get("client")
        self.stats = kwargs.get("stats")
        self.trans = kwargs.get("trans")

        key = parser.get("steam", "key")
        self.steam = SteamSearch(key)

    async def on_message(self, message, **kwargs):
        prefix = kwargs.get("prefix")

        trans = self.trans
        lang = kwargs.get("lang")

        if not is_valid_command(message.content, commands, prefix=prefix):
            return
        else:
            self.stats.add(MESSAGE)

        def startswith(*msg):
            for a in msg:
                if message.content.startswith(a):
                    return True

            return False

        if startswith(prefix + "steam"):
            await message.channel.trigger_typing()

            cut = message.content[len(prefix + "steam "):].strip(" ")

            try:
                subcommand, argument = cut.split(" ", maxsplit=1)
            # In case there are no parameters
            except ValueError:
                # Check if no subcommand - valid
                # If there's a subcommand, but no argument, fail
                if not cut.strip(" "):
                    await message.channel.send(trans.get("MSG_STEAM_INVALID_PARAMS", lang).format(prefix))
                    return

                subcommand, argument = cut, ""

            # !steam games
            if subcommand == "games":
                if not argument:
                    await message.channel.send(trans.get("MSG_STEAM_NEED_URL", lang))
                    return

                # Game search
                try:
                    username, games = await self.steam.get_owned_games(argument)
                except ValueError:
                    await message.channel.send(trans.get("MSG_STEAM_INVALID_URL", lang))
                    return
                except (steamapi.errors.APIFailure, steamapi.errors.APIException):
                    await message.channel.send(trans.get("MSG_STEAM_PRIVATE", lang))
                    raise

                if not username:
                    await message.channel.send(trans.get("ERROR_NO_USER2", lang))
                    self.stats.add(WRONG_ARG)
                    return

                if not games:
                    await message.channel.send(trans.get("MSG_STEAM_PRIVATE_GAMES", lang))
                    self.stats.add(WRONG_ARG)
                    return

                games = ["`{}`".format(game) for game in games]

                try:
                    await message.channel.send(trans.get("MSG_STEAM_GAMES", lang).format(username, ", ".join(games)))
                except HTTPException:
                    await message.channel.send(trans.get("MSG_STEAM_GAMES_TOO_MANY", lang))

            elif subcommand == "user":
                if not argument:
                    await message.channel.send(trans.get("MSG_STEAM_NEED_URL", lang))
                    return

                # Basic search
                try:
                    steam_user = await self.steam.get_user(argument)
                except ValueError:
                    await message.channel.send(trans.get("MSG_STEAM_INVALID_URL", lang))
                    return
                except (steamapi.errors.APIFailure, steamapi.errors.APIException):
                    await message.channel.send(trans.get("MSG_STEAM_PRIVATE", lang))
                    raise

                if not steam_user:
                    await message.channel.send(trans.get("ERROR_NO_USER2", lang))
                    self.stats.add(WRONG_ARG)
                    return

                state = trans.get("MSG_STEAM_ONLINE", lang) if steam_user.state else trans.get("MSG_STEAM_OFFLINE", lang)

                try:
                    info = trans.get("MSG_STEAM_USER_INFO", lang).format(steam_user.name, state, steam_user.level, len(steam_user.games), len(steam_user.friends), argument)
                except AttributeError:
                    await message.channel.send(trans.get("MSG_STEAM_PRIVATE", lang))
                    return

                if len(info) > 2000:
                    await message.channel.send(trans.get("MSG_STEAM_FRIENDS_TOO_MANY", lang))

                else:
                    await message.channel.send(info)

            elif subcommand == "help":
                await message.channel.send(trans.get("MSG_STEAM_HELP", lang).replace("_", prefix))


class NanoPlugin:
    name = "Steam Commands"
    version = "18"

    handler = Steam
    events = {
        "on_message": 10
        # type : importance
    }
