# coding=utf-8

import requests
import json
#import sys

#if len(sys.argv) > 1:
#    servercount = sys.argv[1]
#else:
#    servercount = input("Server count:")

def upload(num):
    url = "https://bots.discord.pw/api/bots/:user_id/stats/".replace(":user_id", "171633949532094464")
    payload = { "server_count": num }
    head = {
        "Content-Type": "application/json",
        "Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiIxMjUyOTc1MDQ4Mjc3MzYwNjQiLCJyYW5kIjoyMjQsImlhdCI6MTQ3MDEyNzE3MX0.GjC0XlaZaL9qx8T71Yb72-8S-Lh2ov1q9gVnXyIZPUw"
    }

    resp = requests.post(url, data=json.dumps(payload), headers=head)
    return True

#upload(servercount)
#print("DONE!")