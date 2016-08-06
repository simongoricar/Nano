# coding=utf-8

__author__ = "DefaltSimon"

# Voting plugin for Nano v2

class Vote:
    def __init__(self):
        self.voteheader = {}
        self.votecontent = {}

        self.voters = {}
        self.votes = {}
        self.progress = {}

        self.author = {}

    def need_save(self):
        return bool(self.voteheader != {} or self.votecontent != {} or self.progress != {})

    def create(self,author,server,vote):

        # Reference - !vote start "Vote for this mate" one|two|three
        self.voteheader[server.id] = str(vote).split("\"")[1]
        votenames = str(vote).split("\"")[2]

        voteob = votenames.split("|")

        self.votes[server.id] = {}
        self.voters[server.id] = []
        count = 0
        for this in voteob:
            voteob[count] = this.strip(" ")

            try:
                self.votes[server.id][str(this).strip(" ")] = 0
            except KeyError:
                self.votes[server.id] = []

            count += 1

        self.votecontent[server.id] = voteob

        self.author[server.id] = str(author)

        self.progress[server.id] = True

    def getcontent(self,server):

        if not self.votecontent[server.id]:
            return None
        else:
            return self.votecontent[server.id]

    def inprogress(self,server):
        try:
            if self.progress[server.id] is True:
                return True
            else:
                return False
        except KeyError:
            return False

    def countone(self,option,voter,server):
        try:
            option = int(option)
        except ValueError:
            return False

        if voter in self.voters[server.id]:
            return -1

        self.voters[server.id].append(voter)

        if option > len(self.votes):
            return False
        else:
            item = self.votecontent[server.id][option-1]
            try:
                self.votes[server.id][item] += 1
            except KeyError:
                self.votes[server.id][item] = 1
                return

    def returnvotes(self,server):
        return self.votes[server.id]

    def returnvoteheader(self,server):
        return str(self.voteheader[server.id])

    def returncontent(self,server):
        return self.votecontent[server.id]

    def end_voting(self, server):
        self.progress[server.id] = False

        self.votes.pop(server.id)
        self.voters.pop(server.id)

        self.voteheader.pop(server.id)
        self.votecontent.pop(server.id)

        self.author.pop(server.id)