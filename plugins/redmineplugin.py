try:
    from redmine import Redmine
    from redmine.exceptions import ResourceAttrError
except ImportError:
    pass

class Ticket:
    def __init__(self, repository, reference):
        self.reference = reference
        self.repository = repository
        try:
            self.redmine = Redmine(repository.source.apiurl, username = repository.source.apikey)
            self.issue = self.redmine.issue.get(int(reference))
            self.title = self.issue.subject
            issuestatus = self.issue.status['name']
            try:
                closed = [i for i in self.redmine.issue_status.all() if i['name'] == issuestatus][0].is_closed
            except ResourceAttrError:
                closed = False
            if closed:
                status = 'success'
            else:
                status = 'default'
            self.status = (status, issuestatus)
        except:
            self.status = ('link', '?')
            self.title = 'Ticket %s in %s (Error while fetching external data)' % (self.reference, self.repository.name)


