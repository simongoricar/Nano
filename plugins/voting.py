# coding=utf-8

__author__ = "DefaltSimon"
# Voting plugin for Nano v2


class Vote:
    def __init__(self):
        self.vote_header = {}
        self.vote_content = {}

        self.voters = {}
        self.votes = {}
        self.progress = {}

        self.author = {}

    def need_save(self):
        return bool(self.vote_header != {} or self.vote_content != {} or self.progress != {})

    def create(self,author,server,vote):

        # Reference - !vote start "Vote for this mate" one|two|three
        self.vote_header[server.id] = str(vote).split("\"")[1]
        vote_names = str(vote).split("\"")[2]

        voteob = vote_names.split("|")

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

        self.vote_content[server.id] = voteob

        self.author[server.id] = str(author)

        self.progress[server.id] = True

    def getcontent(self, server):

        if not self.vote_content[server.id]:
            return None
        else:
            return self.vote_content[server.id]

    def inprogress(self, server):
        try:
            if self.progress[server.id] is True:
                return True
            else:
                return False
        except KeyError:
            return False

    def countone(self, option, voter, server):
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
            item = self.vote_content[server.id][option - 1]
            try:
                self.votes[server.id][item] += 1
            except KeyError:
                self.votes[server.id][item] = 1
                return

    def returnvotes(self, server):
        return self.votes.get(server.id)

    def returnvoteheader(self, server):
        return self.vote_header.get(server.id)

    def returncontent(self, server):
        return self.vote_content.get(server.id)

    def end_voting(self, server):
        self.progress[server.id] = False

        self.votes.pop(server.id)
        self.voters.pop(server.id)

        self.vote_header.pop(server.id)
        self.vote_content.pop(server.id)

        self.author.pop(server.id)
