# coding=utf-8
import os
import logging
from asyncio import sleep
from datetime import datetime

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def log_backup(content):
    with open("data/log.txt", "a") as file:
        date = datetime.now()
        cn = date.strftime("%d-%m-%Y %H:%M:%S") + " - " + str(content)
        print(cn)
        file.write(cn + "\n")

class BackupManager:
    def __init__(self, time=86400):  # 86400 seconds = one day (backup is executed once a day)
        log.info("Enabled")

        if not os.path.isdir("backup"):
            os.mkdir("backup")

        self.servers = os.path.join("backup", "servers.yml.bak")
        self.stats = os.path.join("backup", "stats.yml.bak")

        self.time = int(time)

        self.running = True

    def stop(self):
        self.running = False

    def double_backup(self):
        if not self.running:
            return

        if not os.path.isfile(os.path.join("backup", "servers.yml.bak")) or not os.path.isfile(os.path.join("backup", "stats.yml.bak")):
            log_backup("servers.yml.bak does not exist, not doing a double backup.")
            return

        d = None
        with open(self.servers, "r") as b:
            d = b.read()

        with open(os.path.join("backup", "servers.yml.bak2"), "w") as b2:
            b2.write(d)

        d = None
        with open(self.stats, "r") as b:
            d = b.read()

        with open(os.path.join("backup", "stats.yml.bak2"), "w") as b2:
            b2.write(d)

    def backup(self):
        if not self.running:
            return

        # To be safe
        self.double_backup()

        if not self.running:
            return

        # Servers backup
        data = None
        with open("data/servers.yml", "r") as servers:
            data = servers.read()

        with open(self.servers, "w") as new:
            new.write(data)

        # Stats backup
        data = None
        with open("plugins/stats.yml", "r") as servers:
            data = servers.read()

        with open(self.stats, "w") as new:
            new.write(data)

    async def run_backup_now(self):
        self.backup()
        log_backup("Server and stats backup completed (ignored wait time)")

    async def run_forever(self):
        while self.running:
            await sleep(self.time)

            self.backup()

            if not self.running:
                break

            log_backup("Server and stats backup completed.")

        return