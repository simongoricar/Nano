# coding=utf-8
import asyncio
import configparser
import copy
import importlib
import logging
import os
import sys
import time
import discord

# ServerHandler and NanoStats import
from data import serverhandler
from data import stats as bot_stats
from data.translations import TranslationManager
from data.utils import log_to_file

__title__ = "Nano"
__author__ = 'DefaltSimon'
__version__ = '3.7beta.0'


# EVENTS

ON_MESSAGE = "on_message"
ON_REACTION_ADD = "on_reaction_add"
ON_READY = "on_ready"

ON_MESSAGE_DELETE = "on_message_delete"
ON_MESSAGE_EDIT = "on_message_edit"

ON_CHANNEL_DELETE = "on_channel_delete"
ON_CHANNEL_CREATE = "on_channel_create"
ON_CHANNEL_UPDATE = "on_channel_update"

ON_MEMBER_JOIN = "on_member_join"
ON_MEMBER_REMOVE = "on_member_remove"
ON_MEMBER_UPDATE = "on_member_update"
ON_MEMBER_BAN = "on_member_ban"
ON_MEMBER_UNBAN = "on_member_unban"

ON_GUILD_JOIN = "on_guild_join"
ON_GUILD_REMOVE = "on_guild_remove"

ON_ERROR = "on_error"
ON_SHUTDOWN = "on_shutdown"
ON_PLUGINS_LOADED = "on_plugins_loaded"

# Other constants

IS_RESUME = False
IS_FIRST = True

# LOGGING

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Set logging levels for external modules
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("websockets.protocol").setLevel(logging.INFO)

# Config parser setup
parser = configparser.ConfigParser()
parser.read("settings.ini")


# Loop, discord.py and Nano core modules initialization
loop = asyncio.get_event_loop()
# NOW USES AUTOSHARDING
# client = discord.Client(loop=loop)
client = discord.AutoShardedClient(loop=loop)

log.info("Initializing ServerHandler and NanoStats...")

# Setup the server data and stats
use_legacy = not parser.get("Storage", "type") == "redis"
handler = serverhandler.ServerHandler.get_handler(legacy=use_legacy)
stats = bot_stats.get_NanoStats(legacy=use_legacy)
trans = TranslationManager()

# Singleton metaclass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Nano(metaclass=Singleton):
    def __init__(self):
        # Variables
        self.boot_time = time.time()
        self.version = __version__

        self.owner_id = parser.getint("Settings", "ownerid")
        self.dev_server = parser.getint("Dev", "server")

        # Plugin-related
        self.plugin_names = []
        self.plugins = {}
        self.plugin_events = dict(on_message=[], on_server_join=[], on_channel_create=[], on_channel_delete=[],
                                  on_channel_update=[], on_message_delete=[], on_message_edit=[], on_ready=[],
                                  on_member_join=[], on_member_remove=[], on_member_update=[], on_member_ban=[],
                                  on_member_unban=[], on_server_remove=[], on_error=[], on_shutdown=[],
                                  on_plugins_loaded=[], on_reaction_add=[])
        self.plugin_events_ = dict(self.plugin_events)

        # Updates the plugin list
        self.update_plugins()

    def update_plugins(self):
        started = time.monotonic()
        self.plugin_names = [pl for pl in os.listdir("plugins")
                             if os.path.isfile(os.path.join("plugins", pl)) and str(pl).endswith(".py")]

        self._update_plugins(self.plugin_names)

        log.info("Plugins loaded in {}s".format(round(time.monotonic() - started, 3)))

    def _update_plugins(self, plugin_names):
        """
        Updates all plugins (imports them).
        """
        log.info("Loading plugins...")

        failed = []
        ignored = []

        for plugin in list(plugin_names):
            # Use the importlib to dynamically import all plugins
            try:
                plug = importlib.import_module("plugins.{}".format(plugin[:-3]))
            except ImportError as e:
                log.warning("Failed import: {}".format(e))
                self.plugin_names.pop(self.plugin_names.index(plugin))
                failed.append(plugin)
                continue

            # If this file is not a plugin (does not have a class NanoPlugin), ignore it
            try:
                assert plug.NanoPlugin
                # If plugin has attribute 'disabled' and it is True, disable the plugin
                if hasattr(plug.NanoPlugin, "disabled"):
                    assert plug.NanoPlugin.disabled is False

            except (AttributeError, AssertionError):
                # remove it from the plugin list and delete it
                self.plugin_names.pop(self.plugin_names.index(plugin))
                ignored.append(plugin)
                del plug
                continue

            cls = plug.NanoPlugin.handler
            events = plug.NanoPlugin.events
            # Instantiate the plugin
            try:
                instance = cls(client=client,
                               loop=loop,
                               handler=handler,
                               nano=self,
                               stats=stats,
                               legacy=use_legacy,
                               trans=trans)

            except RuntimeError:
                self.plugin_names.pop(self.plugin_names.index(plugin))
                ignored.append(plugin)
                del plug
                continue
            except Exception as e:
                log.warning("Unexpected error in {}: {}".format(plugin, e))
                self.plugin_names.pop(self.plugin_names.index(plugin))
                failed.append(plugin)
                del plug
                continue

            self.plugins[plugin] = {
                "plugin": plug,
                "handler": cls,
                "instance": instance,
                "events": events,
            }

            for event, importance in events.items():
                self.plugin_events_[event].append({"plugin": plugin, "importance": importance})

        log.debug("Registered plugins: {}".format([str(p).rstrip(".py") for p in self.plugin_names]))

        # Display ignored / failed plugins
        if ignored:
            log.warning("Ignored/Disabled plugins: {}".format(", ".join(ignored)))

        if failed:
            log.warning("Failed plugins: {}".format(", ".join(failed)))

        self._parse_priorities()

        asyncio.ensure_future(self.dispatch_event(ON_PLUGINS_LOADED))

    async def reload_plugin(self, plugin):
        if not str(plugin).endswith(".py"):
            plugin = str(plugin) + ".py"
        else:
            plugin = str(plugin)

        c_plug = self.get_plugin(plugin)
        if not c_plug:
            return False

        # Gracefully reload if the plugin has ON_SHUTDOWN event
        if ON_SHUTDOWN in c_plug.get("events").keys():
            await getattr(c_plug.get("instance"), ON_SHUTDOWN)()

        for event, imp in c_plug.get("events").items():
            self.plugin_events_[event].remove({"plugin": plugin, "importance": imp})

        try:
            c_plug = importlib.reload(c_plug.get("plugin"))
        except ImportError:
            return False

        try:
            assert c_plug.NanoPlugin
            # If plugin has attribute 'disabled' and it is True, disable the plugin
            if hasattr(c_plug.NanoPlugin, "disabled"):
                assert c_plug.NanoPlugin.disabled is False

        except (AttributeError, AssertionError):
            # remove it from the plugin list and delete it
            self.plugin_names.pop(self.plugin_names.index(plugin))
            del c_plug

        cls = c_plug.NanoPlugin.handler
        events = c_plug.NanoPlugin.events

        # Instantiate the plugin
        try:
            instance = cls(client=client,
                           loop=loop,
                           handler=handler,
                           nano=self,
                           stats=stats,
                           trans=trans)

        except RuntimeError:
            self.plugin_names.pop(self.plugin_names.index(plugin))
            del c_plug
            return False
        except Exception as e:
            log.warning("Unexpected error in {}: {}".format(plugin, e))
            self.plugin_names.pop(self.plugin_names.index(plugin))
            del c_plug
            return False

        self.plugins[plugin] = {
            "plugin": c_plug,
            "handler": cls,
            "instance": instance,
            "events": events,
        }

        for event, importance in events.items():
            self.plugin_events_[event].append({"plugin": plugin, "importance": importance})

        self._parse_priorities()
        # Call ON_PLUGINS_LOADED if the plugin requires it
        if ON_PLUGINS_LOADED in events.keys():
            await getattr(instance, ON_PLUGINS_LOADED)()

        return True

    def _parse_priorities(self):
        log.info("Parsing priorities...")

        pe_copy = copy.deepcopy(self.plugin_events_)
        for element, thing in pe_copy.items():
            # Skip if empty
            if not element or not thing:
                continue

            sorted_list = sorted(thing, key=lambda a: a.get("importance"))
            sorted_list = [it.get("plugin") for it in list(sorted_list)]

            self.plugin_events[element] = sorted_list

    def get_plugin(self, name):
        if not str(name).endswith(".py"):
            return self.plugins.get(str(name) + ".py")
        else:
            return self.plugins.get(str(name))

    async def dispatch_event(self, event_type, *args, **kwargs):
        """
        Dispatches any discord event (for example: on_message)
        """
        if event_type not in self.plugin_events.keys():
            log.warning("No such event: {}".format(event_type))
            return

        # Plugins have already been ordered from most important to least important
        for plugin in self.plugin_events[event_type]:
            log.debug("Executing {}".format(getattr(self.plugins[plugin].get("instance"), event_type)))

            # Execute the corresponding method in the plugin
            resp = await getattr(self.plugins[plugin].get("instance"), event_type)(*args, **kwargs)

            # COMMUNICATION
            # If data is passed, assign proper variables
            if not resp:
                continue

            if type(resp) is not list:
                resp = [resp]

            for cmd in resp:
                if isinstance(cmd, tuple):
                    var_addons = cmd[1:]
                    cmd = str(cmd[0])

                else:
                    var_addons = list()

                # Makes communication between the core and plugins possible
                if cmd == "return":
                    log.debug("Exiting")
                    return

                elif cmd == "add_var":
                    # Add/Set new kwargs
                    if isinstance(var_addons, tuple):
                        for k, v in var_addons[0].items():
                            kwargs[k] = v

                    else:
                        for k, v in var_addons.items():
                            kwargs[k] = v

                elif cmd == "set_arg":
                    if isinstance(var_addons, tuple):
                        for k, v in var_addons[0].items():
                            temp = [a for a in args]
                            temp[k] = v
                            args = tuple(b for b in temp)

                    else:
                        for k, v in var_addons.items():
                            temp = [a for a in args]
                            temp[k] = v
                            args = tuple(b for b in temp)

                elif cmd == "shutdown":
                    try:
                        await self.dispatch_event(ON_SHUTDOWN)

                    finally:
                        # Sys.exit is usually handled by developer.py in the ON_SHUTDOWN event,
                        # but it does not hurt to have it here as well.
                        sys.exit(0)


nano = Nano()

# DISCORD EVENTS -> NANO EVENTS


@client.event
async def on_message(message):
    await nano.dispatch_event(ON_MESSAGE, message)


@client.event
async def on_reaction_add(reaction, user):
    await nano.dispatch_event(ON_REACTION_ADD, reaction, user)


@client.event
async def on_message_delete(message):
    await nano.dispatch_event(ON_MESSAGE_DELETE, message)


@client.event
async def on_message_edit(before, after):
    await nano.dispatch_event(ON_MESSAGE_EDIT, before, after)


@client.event
async def on_channel_delete(channel):
    await nano.dispatch_event(ON_CHANNEL_DELETE, channel)


@client.event
async def on_channel_create(channel):
    await nano.dispatch_event(ON_CHANNEL_DELETE, channel)


@client.event
async def on_channel_update(before, after):
    await nano.dispatch_event(ON_CHANNEL_UPDATE, before, after)


@client.event
async def on_member_join(member):
    await nano.dispatch_event(ON_MEMBER_JOIN, member)


@client.event
async def on_member_remove(member):
    await nano.dispatch_event(ON_MEMBER_REMOVE, member)


@client.event
async def on_member_update(before, after):
    await nano.dispatch_event(ON_MEMBER_UPDATE, before, after)


@client.event
async def on_member_ban(member):
    await nano.dispatch_event(ON_MEMBER_BAN, member)


@client.event
async def on_member_unban(guild, member):
    await nano.dispatch_event(ON_MEMBER_UNBAN, guild, member)


@client.event
async def on_guild_join(guild):
    await nano.dispatch_event(ON_GUILD_JOIN, guild)


@client.event
async def on_guild_remove(guild):
    await nano.dispatch_event(ON_GUILD_REMOVE, guild)


@client.event
async def on_error(event, *args, **kwargs):
    await nano.dispatch_event(ON_ERROR, event, *args, **kwargs)

# Do I really need all of this? No, I don't.


@client.event
async def on_ready():
    # Just prints "Resumed connection" if that's the way it is
    global IS_RESUME
    if IS_RESUME:
        print("Resumed connection...")
        return
    IS_RESUME = True

    print("connected!")
    print("BOT name: {} ({})".format(client.user.name, client.user.id))

    log_to_file("Connected as {} ({})".format(client.user.name, client.user.id))

    await nano.dispatch_event(ON_READY)


async def start():
    if not parser.has_option("Credentials", "token"):
        log.critical("Token not found. Check your settings.ini")
        log_to_file("Could not start: Token not specified")

    token = parser.get("Credentials", "token")

    await client.login(token)
    await client.connect()


def main():
    try:
        print("Connecting to Discord...", end="")
        loop.run_until_complete(start())

    except Exception as e:
        loop.run_until_complete(client.logout())
        log.critical("Something went wrong, quitting (see log for exception info).")
        log_to_file("CRITICAL, shutting down: {}".format(e))

        # Attempts to save plugin state
        log.critical("Dispatching ON_SHUTDOW...")
        loop.run_until_complete(nano.dispatch_event(ON_SHUTDOWN))
        log.critical("done, shutting down...")

    finally:
        loop.close()


if __name__ == '__main__':
    main()
