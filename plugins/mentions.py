from random import randint

__author__ = "DefaltSimon"

# Mention module for AyyBot (handles @AyyBot mentions)

class MentionHandler:
    def __init__(self):
        pass

    def respond(self,message):
        """Return type: answer"""

        def has(*args):
            for arg in args:
                if arg in str(message.content).lower():
                    return True
                else:
                    return False

        if has("hi"):
            return "Hi there!"

        elif has("how are you"):
            rn = randint(0,3)
            lst = ["I'm awesome!", "Doing great.", "Doing awesome. Pumpin' dem messages out like it's christmas babyyy!"]
            return str(lst[rn])

        elif has("do you wanna build a snowman","do you want to build a snowman"):
            return "C'mon lets go out and play!"

        elif has("die"):
            return "I don't have plans to jk :wink:"