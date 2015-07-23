try:
    import github3
except:
    pass

class Ticket:
    def __init__(self, repository, reference):
        self.reference = reference
        self.repository = repository
        try:
            self.pull_request = github3.pull_request(repository.username, repository.project, reference)
            self.title = self.pull_request.title
            self.status = self.get_status()
        except:
            self.status = ('link', '?')
            self.title = 'Ticket %s in %s (Error while fetching external data)' % (self.reference, self.repository.name)

    def get_status(self):
        if self.pull_request.closed_at:
            if self.pull_request.is_merged():
                return ('success', 'closed/merged')
            else:
                return('success', 'closed')
        else:
            if self.pull_request.is_merged():
                return ('info', 'closed/merged')
            elif self.pull_request.mergeable:
                return ('default', 'open')
            else:
                return ('danger', 'open/not mergeable')

