# coding=utf-8
import asyncio
import importlib
import logging
import os
import sys
import time
import discord
import traceback

from core.serverhandler import ServerHandler
from core.stats import NanoStats
from core.translations import TranslationManager
from core.utils import log_to_file
from core.exceptions import PluginDisabledException
from core.configuration import PARSER_SETTINGS, DIR_PLUGINS

__title__ = "Nano"
__author__ = 'DefaltSimon'
__version__ = '3.9dev'


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


EVENTS = ["on_message", "on_guild_join", "on_channel_create", "on_channel_delete",
          "on_channel_update", "on_message_edit", "on_message_delete", "on_ready",
          "on_member_join", "on_member_remove", "on_member_update", "on_member_ban",
          "on_member_unban", "on_guild_remove", "on_error", "on_shutdown",
          "on_plugins_loaded", "on_reaction_add"]

# Ensure there are no duplicates
assert len(set(EVENTS)) == len(EVENTS)

# Other constants

IS_RESUME = False

# LOGGING

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Set logging levels for external modules
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("websockets.protocol").setLevel(logging.INFO)

# Disable redis debug messages
logging.getLogger("core.stats").setLevel(logging.INFO)
logging.getLogger("plugins.statistics").setLevel(logging.INFO)

# Loop, discord.py and Nano core modules initialization
loop = asyncio.get_event_loop()

# NOW USES AUTOSHARDING
custom_intents = discord.Intents.default()
custom_intents.members = True

client = discord.AutoShardedClient(
    loop=loop,
    intents=custom_intents,
)

log.info("Initializing ServerHandler and NanoStats...")

# Setup the server data and stats
handler = ServerHandler.get_handler(loop)
stats = NanoStats(loop, *ServerHandler.get_redis_data_credentials())
trans = TranslationManager()


class PluginObject:
    def __init__(self, lib, instance):
        self.plugin = lib
        self.handler = getattr(lib, "NanoPlugin")

        self.instance = instance
        self.events = self.handler.events


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

        self.owner_id = PARSER_SETTINGS.getint("Settings", "ownerid")
        self.dev_server = PARSER_SETTINGS.getint("Dev", "server")

        # Plugin-related
        self.plugin_names = []
        self.plugins = {}
        self.plugin_events = {a: [] for a in EVENTS}
        self.event_types = set(self.plugin_events.keys())

        # Updates the plugin list
        self.update_plugins()

    def update_plugins(self):
        started = time.monotonic()
        plugin_names = [pl[:-3] for pl in os.listdir(DIR_PLUGINS)
                        if os.path.isfile(os.path.join(DIR_PLUGINS, pl))
                        and pl.endswith(".py")]

        self._update_plugins(plugin_names)

        log.info("Plugins loaded in {}s".format(round(time.monotonic() - started, 3)))

    def _update_plugins(self, names: list):
        log.info("Loading plugins...")

        loaded = []
        failed = []
        disabled = []

        PLUGINS_NAMESPACE = DIR_PLUGINS.replace("/", "").replace("\\", "")

        # Try to import every plugin
        for plug_name in list(names):
            # Use importlib
            try:
                plugin = importlib.import_module("{}.{}".format(PLUGINS_NAMESPACE, plug_name))
            except ImportError:
                log.warning("Failed to import plugin: {}".format(plug_name))
                log.critical(traceback.format_exc())

                failed.append(plug_name)
                continue

            # Plugin loaded, check validity
            # Plugin must have a class NanoPlugin, see examples in plugins/
            if not hasattr(plugin, "NanoPlugin"):
                log.error("Plugin {} does not have the required NanoPlugin class".format(plug_name))
                failed.append(plug_name)

                del plugin
                continue

            info = getattr(plugin, "NanoPlugin")
            handler_cls = info.handler

            # Make an instance
            try:
                inst = handler_cls(
                    client=client,
                    loop=loop,
                    handler=handler,
                    nano=self,
                    stats=stats,
                    trans=trans
                )
            # A plugin can raise PluginDisabledException to indicate it shouldn't be loaded
            except PluginDisabledException as e:
                log.warning("Plugin disabled: {} (reason: \"{}\")".format(plug_name, e))
                disabled.append(plug_name)

                del plugin
                continue
            # Any other exception is logged
            except Exception:
                log.warning("Exception while creating plugin instance: {}".format(plug_name))
                log.critical(traceback.format_exc())

                del plugin
                continue

            self.plugins[plug_name] = PluginObject(plugin, inst)
            loaded.append(plug_name)

        self.plugin_names = loaded

        log.info("=== Plugin load complete ===")
        log.info("{} loaded plugins: {}".format(len(self.plugin_names), ", ".join(self.plugin_names)))

        # Log if any plugins failed to load
        if disabled:
            log.warning("{} disabled plugins: {}".format(len(disabled), ", ".join(disabled)))

        if failed:
            log.warning("{} failed plugins: {}".format(len(failed), ", ".join(failed)))

        self._parse_priorities()

        asyncio.ensure_future(self.dispatch_event(ON_PLUGINS_LOADED))

    async def reload_plugin(self, name: str):
        log.info("Reloading plugin: {}".format(name))

        if name.endswith(".py"):
            name = name[:-3]

        # Verify that the plugin is actually already loaded
        if name not in self.plugins.keys():
            raise NotImplementedError

        plug = self.get_plugin(name)
        assert isinstance(plug, PluginObject)

        # Gracefully reload if the plugin has ON_SHUTDOWN event
        if ON_SHUTDOWN in plug.events.keys():
            await getattr(plug.instance, ON_SHUTDOWN)()

        # Reload the plugin
        try:
            plugin = importlib.reload(plug.plugin)
        except ImportError:
            log.warning("Couldn't reload {}".format(name))
            log.critical(traceback.format_exc())
            raise RuntimeError

        # Plugin loaded, check validity
        # Plugin must have a class NanoPlugin, see examples in plugins/
        if not hasattr(plugin, "NanoPlugin"):
            log.warning("Plugin {} does not have the required NanoPlugin class".format(name))

            del plugin
            raise RuntimeError

        info = getattr(plugin, "NanoPlugin")
        events = info.events
        handler_cls = info.handler

        # Make an instance
        try:
            inst = handler_cls(client=client,
                               loop=loop,
                               handler=handler,
                               nano=self,
                               stats=stats,
                               trans=trans)
        # A plugin can raise RuntimeError to indicate it doesn't want to be loaded
        except RuntimeError:
            del plugin
            raise RuntimeError
        # Other exceptions make it fail
        except Exception:
            log.warning("Failed to reload and instantiate {}".format(name))
            log.critical(traceback.format_exc())

            del plugin
            raise RuntimeError

        self.plugins[name] = PluginObject(plugin, inst)

        self._parse_priorities()

        # Call ON_PLUGINS_LOADED if the plugin requires it
        if ON_PLUGINS_LOADED in events.keys():
            await getattr(inst, ON_PLUGINS_LOADED)()

        log.info("Plugin reloaded: {}".format(name))
        return True

    def _parse_priorities(self):
        log.info("Parsing priorities...")

        temp = {}

        for p in self.plugins.values():
            assert isinstance(p, PluginObject)

            for ev_name, priority in p.events.items():
                if not temp.get(ev_name):
                    temp[ev_name] = []

                temp[ev_name].append({"callback": getattr(p.instance, ev_name), "importance": priority})

        # Order callbacks
        for event, unordered in temp.items():
            ordered = sorted(unordered, key=lambda a: a["importance"])
            ordered = [i["callback"] for i in ordered]

            self.plugin_events[event] = ordered

    def get_plugin(self, name: str) -> dict:
        if name.endswith(".py"):
            name = name[:-3]

        return self.plugins[name]

    async def dispatch_event(self, event_type, *args, **kwargs):
        """
        Dispatches any discord event (for example: on_message)
        """
        if event_type not in self.event_types:
            log.warning("No such event: {}".format(event_type))
            return

        # If there is no registered event, quit
        if not self.plugin_events[event_type]:
            return

        # Plugins have already been ordered from most important to least important
        for cb in self.plugin_events[event_type]:
            # log.debug("Executing plugin {}:{}".format(cb.strip(".py"), event_type))

            # Execute the corresponding method in the plugin
            resp = await cb(*args, **kwargs)

            # COMMUNICATION
            # If data is passed, assign proper variables
            if not resp:
                continue

            if type(resp) is not list:
                resp = (resp, )

            # Multiple commands can be passed in a form of a tuple
            for cmd in resp:
                # Parse additional variables
                if type(cmd) in (tuple, list, set):
                    # Unpacks parameters
                    cmd, arguments, *safe = cmd

                # No additional arguments
                else:
                    arguments = ()

                # Makes communication between the core and plugins possible

                # RETURN
                # Exits the current event immediately and doesn't call any more plugins
                if cmd == "return":
                    return

                # ADD_VAR
                # Adds a variable to the current kwargs
                elif cmd == "add_var":
                    if type(arguments) is tuple:
                        # Arguments must be a dict
                        for k, v in arguments[0].items():
                            kwargs[k] = v
                    else:
                        for k, v in arguments.items():
                            kwargs[k] = v

                # SHUTDOWN
                # Calls the ON_SHUTDOWN event, then exists
                elif cmd == "shutdown":
                    try:
                        await self.dispatch_event(ON_SHUTDOWN)

                    finally:
                        # Sys.exit is usually handled by developer.py in the ON_SHUTDOWN event
                        # but it is here as backup as well
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
async def on_member_ban(guild, user):
    await nano.dispatch_event(ON_MEMBER_BAN, guild, user)


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
        log_to_file("Resumed connection as {}".format(client.user.name))
        return
    IS_RESUME = True

    print("connected!")
    print("BOT name: {} ({})".format(client.user.name, client.user.id))

    log_to_file("Connected as {} ({})".format(client.user.name, client.user.id))

    await nano.dispatch_event(ON_READY)


async def start():
    if not PARSER_SETTINGS.has_option("Credentials", "token"):
        log.critical("Token not found. Check your settings.ini")
        log_to_file("Could not start: Token not specified")
        return

    token = PARSER_SETTINGS.get("Credentials", "token")

    await client.login(token)
    await client.connect()


def main():
    try:
        print("Connecting to Discord...", end="")
        loop.run_until_complete(start())

    except Exception as e:
        loop.run_until_complete(client.logout())
        log.critical("Something went wrong, quitting (see log bugs.txt)")
        log_to_file("CRITICAL, shutting down: {}".format(e), "bug")

        # Attempts to save plugin state
        log.critical("Dispatching ON_SHUTDOW...")
        loop.run_until_complete(nano.dispatch_event(ON_SHUTDOWN))
        log.critical("Shutting down...")

    finally:
        loop.close()


if __name__ == '__main__':
    main()
