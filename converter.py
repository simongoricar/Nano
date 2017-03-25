# coding=utf-8
import time
import configparser
from data import stats
from data.serverhandler import ServerHandler, server_defaults

#########################################
# Converter utility
# This script inserts existing servers.yml into a running Redis db
# It also transfers stats
#########################################


parser = configparser.ConfigParser()
parser.read("settings.ini")

if not parser.get("Storage", "type") == "redis":
    print("Storage type is not set to redis, please change to continue (settings.ini)")


init = time.monotonic()

red_stats = stats.get_NanoStats(legacy=False)
leg_stats = stats.get_NanoStats(legacy=True)
print("Copying stats...", end="")

for stat_typ, val in leg_stats.cached_data.items():
    if stat_typ not in stats.stat_types:
        print("{} is not a stat_type?".format(stat_typ))
        continue

    red_stats._set_amount(stat_typ, int(val))

print("done")
print("Copying server data...")
red = ServerHandler.get_handler(legacy=False)
legacy = ServerHandler.get_handler(legacy=True)

server_data = legacy.get_data()

commands = []
blacklists = []
mutes = []
bases = []


def auto_int(a):
    try:
        return int(a)
    except ValueError:
        return a


def make_int(a):
    try:
        return int(a)
    except ValueError:
        return None


def auto_bool(cn):
    if str(cn).lower() == "true":
        return True
    elif str(cn).lower() == "false":
        return False
    elif str(cn).lower() == "none":
        return None
    else:
        return False


for s_id, data in server_data.items():
    if data.get("customcmds"):
        # Filter out too long commands
        cmds = {k: v for k, v in data.get("customcmds").items() if (len(k or mklen(81)) <= 80) and (len(v or mklen(801)) <= 800)}

        commands.append({
            "commands:{}".format(s_id): cmds
        })

    if data.get("blacklisted"):
        blacklists.append({
            "blacklist:{}".format(s_id): [make_int(a) for a in data.get("blacklisted") if a is not None]
        })

    if data.get("muted"):
        mutes.append({
            "mutes:{}".format(s_id): [make_int(a) for a in data.get("muted") if a is not None]
        })

    if data.get("banmsg") is None:
        banmsg = server_defaults.get("banmsg")
    else:
        banmsg = data.get("banmsg")

    if data.get("kickmsg") is None:
        kickmsg = server_defaults.get("kickmsg")
    else:
        kickmsg = data.get("kickmsg")

    if data.get("leavemsg") is None:
        leavemsg = server_defaults.get("leavemsg")
    else:
        leavemsg = data.get("leavemsg")

    if data.get("welcomemsg") is None:
        welcomemsg = server_defaults.get("welcomemsg")
    else:
        welcomemsg = data.get("welcomemsg")

    bases.append({
        "server:{}".format(s_id): {
            "banmsg": banmsg if len(banmsg) < 800 else server_defaults.get("banmsg"),
            "kickmsg": kickmsg if len(kickmsg) < 800 else server_defaults.get("kickmsg"),
            "leavemsg": leavemsg if len(leavemsg) < 800 else server_defaults.get("leavemsg"),
            "welcomemsg": welcomemsg if len(welcomemsg) < 800 else server_defaults.get("welcomemsg"),

            "invitefilter": bool(auto_int(data.get("filterinvite"))),
            "wordfilter": bool(auto_int(data.get("filterwords"))),
            "spamfilter": bool(auto_int(data.get("filterspam"))),

            "owner": data.get("owner"),
            "name": data.get("name"),
            "prefix": data.get("prefix") if len(data.get("prefix") or mklen(101)) < 100 else server_defaults.get("prefix"),
            "sleeping": bool(auto_int(data.get("sleeping"))),
            "logchannel": data.get("logchannel")
            # admins are removed!
            # (see update 3.4)
        }
    })

# print(commands, blacklists, mutes, bases, sep="\n")

print("Done parsing.\nCopying to Redis database...")

print("Adding {} servers' custom commands".format(len(commands)))
for serv in commands:
    for server_name, v in serv.items():
        for trig, resp in v.items():
            red.redis.hset(server_name, trig, resp)

print("Adding {} channel blacklists".format(len(blacklists)))
for serv in blacklists:
    for server_name, v in serv.items():
        for bl in v:
            red.redis.sadd(server_name, bl)

print("Adding {} mutes".format(len(mutes)))
for serv in mutes:
    for server_name, v in serv.items():
        for mute in v:
            red.redis.sadd(server_name, mute)

print("Adding {} base server entries".format(len(bases)))
for serv in bases:
    for server_name, v in serv.items():
        red.redis.hmset(server_name, v)


red.redis.bgsave()
print("DONE, took {}s".format(round(time.monotonic() - init), 5))
