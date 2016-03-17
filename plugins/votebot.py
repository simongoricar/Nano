__author__ = "DefaltSimon"

# Voting plugin for AyyBot

class Vote:
    def __init__(self):
        self.votecontent = []
        self.voters = []
        self.votesgot1 = 0
        self.votesgot2 = 0
        self.votesgot3 = 0
        self.votesgot4 = 0
        self.votesgot5 = 0
        self.initiator = None
    def create(self,author,vote):
        self.hm = 0
        for this in str(vote).split('""'):
            self.hm += 1
            this = "**" + str(self.hm) + "**" + ". " + str(this).strip("(").strip(")")
            self.votecontent.append(this)
        self.initiator = str(author)
    def reset(self):
        self.votecontent = []
        self.voters = []
        self.votesgot1 = 0
        self.votesgot2 = 0
        self.votesgot3 = 0
        self.votesgot4 = 0
        self.votesgot5 = 0
    def getcontent(self):
        if not self.votecontent:
            return None
        else:
            return self.votecontent
    def countone(self,option,voter):
        option = int(option)
        self.voters.append(voter)
        if option == 1:
            self.votesgot1 += 1
        elif option == 2:
            self.votesgot2 += 1
        elif option == 3:
            self.votesgot3 += 1
        elif option == 4:
            self.votesgot4 += 1
        elif option == 5:
            self.votesgot5 += 1
    def returnvotes(self):
        list = [self.votesgot1,self.votesgot2,self.votesgot3,self.votesgot4,self.votesgot5]
        return list
    def returncontent(self):
        return self.votecontent