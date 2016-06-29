__author__ = "DefaltSimon"
# Moderator plugin for AyyBot

class BotModerator:
    def __init__(self):
        self.wordlist = []

        with open("plugins/wordlist.txt","r") as file:
            file = file.readlines()
            for line in file:
                self.wordlist.append(line.strip("\n"))


    def checkfilter(self,message):
        """Returns True if there is a banned word
        :param message: Discord Message content
        """

        # Builds a list
        messagewords = str(message).lower().split(" ")

        # Checks for matches
        # Each word is compared to each banned word
        for mword in messagewords:
            for bword in self.wordlist:

                if str(mword).find(str(bword)) != -1:
                    return True

        # If no banned words are found, return False
        return False

    @staticmethod
    def checkspam(message):
        """Returns True if spam is found
        :param message: Discord Message content
        """

        mostallowedlong = 0.8
        mostalloedshort = 1.34

        current = 0

        wwhitelist = ["ha", ":"]
        cwhitelist = ["h", "a"]

        # Checks if it's a sticker
        def issticker(*args):
            for arg in args:
                msg = str(arg).strip(" ")

                if msg.startswith(":") and msg.endswith(":") or msg == "?":
                    return True
                else:
                    return False

        # First a word repetition check

        wordss = str(message).lower().split(" ")
        for n, word in enumerate(wordss):
            try:
                twoback = wordss[n-2]
            except IndexError:
                twoback = None

            try:
                oneback = wordss[n-1]
            except IndexError:
                oneback = None

            if word == oneback or word == twoback:
                if (word not in wwhitelist) and not issticker(word):
                    current += 2

            # Check for caps
            if word.isupper() and oneback.isupper() and twoback.isupper():
                current += 1


            # Character repetition check
            for char in word:
                try:
                    twocback = word[word.index(char)-2]
                except IndexError:
                    continue

                try:
                    onecback = word[word.index(char)-1]
                except IndexError:
                    continue

                if char == twocback or char == onecback:
                    if (char in cwhitelist) or char == "*" or issticker(char, twocback, onecback):
                        pass
                    else:
                        current += 2

        # If repetition count it above the threshold, return True

        # Adjusted to the length of the text
        # Not the best system right now, but I plan on calculating string entropy

        calc = len(message)/2

        if len(message) > 14:
            if current/calc > mostallowedlong:
                return True
            else:
                return False
        else:
            if current/calc > mostalloedshort:
                return True
            else:
                return False