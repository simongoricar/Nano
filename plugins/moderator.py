# coding=utf-8

import re
import logging
from pickle import load

__author__ = "DefaltSimon"
# Moderation plugin for Nano

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

accepted_chars = "abcdefghijklmnopqrstuvwxyz "


def normalize(line):
    # Ignores punctuation, new lines, etc...
    accepted = ""
    for char in line:
        if char in accepted_chars:
            accepted += char

    return accepted


def two_chars(line):  # Normalizes
    norm = normalize(line)
    for rn in range(0, len(norm) - 1):
        yield norm[rn:rn + 1], norm[rn + 1:rn + 2]


class BotModerator:
    def __init__(self):
        log.info("Enabled")
        self.word_list = []

        with open("plugins/wordlist.txt", "r") as file:
            file = file.readlines()
            for line in file:
                self.word_list.append(line.strip("\n"))

        # Gibberish detector
        self.model = load(open("plugins/spam_model.pki", "rb"))

        self.data = self.model["data"]
        self.threshold = self.model["threshold"]
        self.char_p = self.model["positions"]

        # Mute system
        self.muted_users = {}

        # Entropy calculator
        self.chars2 = "abcdefghijklmnopqrstuvwxyz,.-!?_;:|1234567890*=)(/&%$#\"~<> "
        self.pos2 = dict([(c, index) for index, c in enumerate(self.chars2)])

    def checkfilter(self, message):
        """Returns True if there is a banned word
        :param message: Discord Message content
        """

        # Builds a list
        messagewords = str(message).lower().split(" ")

        # Checks for matches
        # Each word is compared to each banned word
        for mword in messagewords:
            for bword in self.word_list:

                if str(mword).find(str(bword)) != -1:
                    return True

        # If no banned words are found, return False
        return False

    def checkspam(self, message):
        """
        Does a set of checks.
        :param message: string to check
        :return: bool
        """

        #if len(message) > 10:  # This detector is 'effective' only when the string is
        #    result = bool(self.detectgibberish(message))
        #else:
        #    result = bool(self.detectcharspam(message))

        result = bool(self.detectgibberish(message))  # Currently uses only the gibberish detector since the other one does not have much (or enough) better detection of repeated chars

        return result

    def detectgibberish(self, message):
        """Returns True if spam is found
        :param message: string
        """
        if not message:
            return

        th = len(message) / 2.4
        c = float(0)
        for ca, cb in two_chars(message):

            if self.data[self.char_p[ca]][self.char_p[cb]] < self.threshold[self.char_p[ca]]:
                c += 1

        return bool(c >= th)

    def detectcharspam(self, message):
        """
        String entropy calculator.
        :param message: string
        :return: bool
        """

        counts = [[0 for c in range(len(self.chars2))] for ac in range(len(self.chars2))]

        for o, t in two_chars(message):
            counts[self.pos2[o]][self.pos2[t]] += 1

        thr = 0
        for this in counts:
            for another in this:
                thr += another

        thr /= 3.5

        for this in counts:
            for another in this:
                if another > thr:
                    print("Threshold {}, got {}".format(thr, another))
                    return True

        return False

    def checkinvite(self, message):
        """
        Checks for invites
        :param message: string
        :return: bool
        """
        rg = re.compile(r'(http(s)?://)?discord.gg/\w+')

        res = rg.search(str(message))
        if res is not None:
            return True, res
        else:
            return False, None
