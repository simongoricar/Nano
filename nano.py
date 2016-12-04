# coding=utf-8
import asyncio
import configparser
import copy
import importlib
import logging
import os
import sys
import threading
import time
import discord

# ServerHandler and NanoStats import
from data import serverhandler
from data import stats as bot_stats
from data.utils import log_to_file

__title__ = "Nano"
__author__ = 'DefaltSimon'
__version__ = '3.2'


# CONSTANTS and EVENTS

ON_MESSAGE = "on_message"
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


ON_SERVER_JOIN = "on_server_join"
ON_SERVER_REMOVE = "on_server_remove"

ON_ERROR = "on_error"
ON_SHUTDOWN = "on_shutdown"

# Other

is_resume = False

# LOGGING

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Set logging levels
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("websockets.protocol").setLevel(logging.INFO)

# Loop initialization and other things

loop = asyncio.get_event_loop()
client = discord.Client(loop=loop)
handler = serverhandler.ServerHandler()
stats = bot_stats.NanoStats()

# Config parser

parser = configparser.ConfigParser()
parser.read("settings.ini")

# Constants
first = True

# Decorator


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


@threaded
def save_submission(content):
    with open("data/submissions.txt", "a") as sf:
        sf.write(str(content))

# Singleton class


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
        self.owner_id = parser.get("Settings", "ownerid")

        self.dev_server = parser.get("Dev", "server")

        # Plugin-related
        self.plugin_names = []
        self.plugins = {}
        self.plugin_events = dict(on_message=[], on_server_join=[], on_channel_create=[], on_channel_delete=[],
                                  on_channel_update=[], on_message_delete=[], on_message_edit=[], on_ready=[],
                                  on_member_join=[], on_member_remove=[], on_member_update=[], on_member_ban=[],
                                  on_member_unban=[], on_server_remove=[], on_error=[], on_shutdown=[])
        self.plugin_events_ = dict(self.plugin_events)

        # Updates the plugin list
        self.update_plugins()

    def update_plugins(self):
        self.plugin_names = [pl for pl in os.listdir("plugins")
                             if os.path.isfile(os.path.join("plugins", pl)) and str(pl).endswith(".py")]

        self._update_plugins(self.plugin_names)

    def _update_plugins(self, plugin_names):
        """
        Updates all plugins (imports them).
        """
        log.info("Updating plugins...")

        failed = []

        for plugin in list(plugin_names):
            # Use the importlib to dynamically import all plugins
            try:
                plug = importlib.import_module("plugins.{}".format(plugin[:-3]))
            except ImportError:
                self.plugin_names.pop(self.plugin_names.index(plugin))
                failed.append(plugin)
                continue

            # If this file is not a plugin, ignore it
            try:
                plug.NanoPlugin
            except AttributeError:
                # remove it from the plugin list and delete it
                self.plugin_names.pop(self.plugin_names.index(plugin))
                failed.append(plugin)
                del plug
                continue

            cls = plug.NanoPlugin.handler
            events = plug.NanoPlugin.events
            # Instantiate the plugin
            instance = cls(client=client,
                           loop=loop,
                           handler=handler,
                           nano=self,
                           stats=stats)

            self.plugins[plugin] = {
                "plugin": plug,
                "handler": cls,
                "instance": instance,
                "events": events,
            }

            for event, importance in events.items():
                self.plugin_events_[event].append({"plugin": plugin, "importance": importance})

        log.debug("Registered plugins: {}".format([str(p).rstrip(".py") for p in self.plugin_names]))

        if failed:
            log.warning("Failed plugins: {}".format(failed))

        self._parse_priorities()

    async def reload_plugin(self, plugin):
        if not str(plugin).endswith(".py"):
            plugin = str(plugin) + ".py"
        else:
            plugin = str(plugin)

        p = self.get_plugin(plugin)
        if not p:
            return False

        # Gracefully reload if the plugin has ON_SHUTDOWN event
        if ON_SHUTDOWN in p.get("events").keys():
            await getattr(p.get("instance"), ON_SHUTDOWN)()

        for event, imp in p.get("events").items():
            self.plugin_events_[event].remove({"plugin": plugin, "importance": imp})

        try:
            plug = importlib.reload(p.get("plugin"))
        except ImportError:
            return False

        # If this file is not a plugin, ignore it
        try:
            plug.NanoPlugin
        except AttributeError:
            return False

        cls = plug.NanoPlugin.handler
        events = plug.NanoPlugin.events

        # Instantiate the plugin
        instance = cls(client=client,
                       loop=loop,
                       handler=handler,
                       nano=self,
                       stats=stats)

        self.plugins[plugin] = {
            "plugin": plug,
            "handler": cls,
            "instance": instance,
            "events": events,
        }

        for event, importance in events.items():
            self.plugin_events_[event].append({"plugin": plugin, "importance": importance})

        self._parse_priorities()

        return True

    def _parse_priorities(self):
        log.info("Parsing priorities...")

        pe = copy.deepcopy(self.plugin_events_)
        for el, thing in pe.items():
            # Skip if empty
            if not el or not thing:
                continue

            sorted_list = sorted(thing, key=lambda a: a.get("importance"))
            sorted_list = [it.get("plugin") for it in list(sorted_list)]

            self.plugin_events[el] = sorted_list

    def get_plugin(self, name):
        if not str(name).endswith(".py"):
            return self.plugins.get(str(name) + ".py")
        else:
            return self.plugins.get(str(name))

    async def dispatch_event(self, event_type, *args, **kwargs):
        """
        Dispatches any discord event (for example: on_message)
        """
        if not self.plugin_events.get(event_type):
            return

        # Plugins have already been ordered from most important to least important
        for plugin in self.plugin_events.get(event_type):
            log.debug("Executing {}".format(getattr(self.plugins[plugin].get("instance"), event_type)))

            # Execute the corresponding method in the plugin
            resp = await getattr(self.plugins[plugin].get("instance"), event_type)(*args, **kwargs)

            # COMMUNICATION
            # If data is passed, assign proper variables
            if isinstance(resp, tuple):
                ag = resp[1:]
                resp = str(resp[0])

            else:
                ag = list()

            # Makes communication between the core and plugins possible
            if resp == "return":
                log.debug("Exiting")
                return

            elif resp == "add_var":
                # Add/Set new kwargs
                try:
                    if isinstance(ag, tuple):
                        for k, v in ag[0].items():
                            kwargs[k] = v

                    else:
                        for k, v in ag.items():
                            kwargs[k] = v
                except AttributeError as e:
                    print("Exception: " + str(e))
                    # debugme remove this after it has been fixed
                    print("DEBUG!! {} at plugin {}".format(ag, plugin))

            elif resp == "shutdown":
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
    log.debug("Dispatching on_message")
    await nano.dispatch_event(ON_MESSAGE, message)


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
async def on_member_unban(server, member):
    await nano.dispatch_event(ON_MEMBER_UNBAN, server, member)


@client.event
async def on_server_join(server):
    await nano.dispatch_event(ON_SERVER_JOIN, server)


@client.event
async def on_server_remove(server):
    await nano.dispatch_event(ON_SERVER_REMOVE, server)


@client.event
async def on_error(event, *args, **kwargs):
    await nano.dispatch_event(ON_ERROR, event, *args, **kwargs)

# Do I really need all of this? No, I don't.


@client.event
async def on_ready():
    # Just prints "Resumed connection" if that's the way it is
    global is_resume
    if is_resume:
        print("Resumed connection...")
        return
    is_resume = True

    print("connected!")
    print("Username: " + str(client.user.name))
    print("ID: " + str(client.user.id))

    log_to_file("Connected as {} ({})".format(client.user.name, client.user.id))

    await nano.dispatch_event(ON_READY)


async def start():
    if not parser.has_option("Credentials", "token"):
        log.fatal("Token not found. Check your settings.ini")
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
        log.fatal("Something went wrong, quitting (see log for exception info).")
        log_to_file("Something went wrong: {}".format(e))

    finally:
        loop.close()


if __name__ == '__main__':
    main()
