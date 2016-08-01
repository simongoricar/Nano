# coding=utf-8

from random import randint

__author__ = "DefaltSimon"

# Mention module for AyyBot (handles @AyyBot mentions)

class MentionHandler:
    def __init__(self):
        pass

    @staticmethod
    def respond(message):
        """Return type: answer"""

        def has(*args):
            for arg in args:
                if arg in str(message.content).lower():
                    return True

            return False

        if has("hi", "hey"):
            return "Hi there!"

        elif has("how are you"):
            lst = ["I'm awesome!", "Doing great.", "Doing awesome. Pumpin' dem messages out like it's christmas babyyy!"]
            rn = randint(0,len(lst))

            return str(lst[rn])

        elif has("do you wanna build a snowman", "do you want to build a snowman"):
            return "C'mon lets go out and play!"

        elif has("die"):
            return ":wink:"

        elif has("do you ever get tired"):
            return "Not really."

        elif has("ayy"):
            return "Ayy. Lmao."

        elif has("rip"):
            return "Rest in peperonni indeed."

        elif has("do you have a master"):
            return "Dobby has no master."

        elif has("what is this"):
            return "SPARTA!"

        elif has("help"):
            return "Use !help to get help, (! is the default prefix)"