# coding=utf-8

import requests
import json
#import sys

#if len(sys.argv) > 1:
#    servercount = sys.argv[1]
#else:
#    servercount = input("Server count:")

def upload(num, token):
    url = "https://bots.discord.pw/api/bots/:user_id/stats/".replace(":user_id", "171633949532094464")
    payload = { "server_count": num }
    head = {
        "Content-Type": "application/json",
        "Authorization": str(token)
    }

    resp = requests.post(url, data=json.dumps(payload), headers=head)
    return True

#upload(servercount)
#print("DONE!")