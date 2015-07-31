class Renderer(object):
    def __init__(self, runtime):
        self.runtime = runtime

    def render(self):
        with open('triage.txt', 'w') as f:
            f.write('''PUPPET MODULE TRIAGE


Open Questions
==============




Repositories
============

''')
            runtime = self.runtime
            repos = [k[1] for k in sorted(runtime.repositories.items(), key=lambda x: x[0])]
            for repository in repos:
                repo = repository

                if not repository.internal:
                    f.write('Repository has no internal remote\n')
                    continue

                f.write('%s\n' % repository.name)
                for i in xrange(0, len(repository.name)):
                    f.write('-')
                f.write('\n')


                if not repository.upstream:
                    pass
                else:
                    if len(repo.internal.tickets) > 0:
                        f.write('Internal tickets:\n\n')
                        for ticket in repo.internal.tickets:
                            f.write(' * %s%s - %s - %s\n   %s\n' % (repository.internal.ticket_prefix, ticket.reference, ticket.external.status[1], ticket.external.title, ticket.url))
                        f.write('\n\n')
                    if len(repo.upstream.tickets) > 0:
                        f.write('Upstream tickets:\n\n')
                        for ticket in repo.upstream.tickets:
                            f.write(' * %s%s - %s - %s\n   %s\n' % (repository.upstream.ticket_prefix, ticket.reference, ticket.external.status[1], ticket.external.title, ticket.url))
                        f.write('\n\n')
                    if repo.behind > 0:
                        f.write('Repo is behind upstream.\n\n')
                    if repo.ahead > 0:
                        f.write('Repository is ahead upstream.\n\n')

                    for diff in repo.diffs.values():
                        if diff.behind is not None:
                            if diff.behind == 0:
                                pass
                            else:
                                f.write('Repository is %s commits behind in super repo %s!\n\n' % (diff.behind, diff.target))
                            if diff.ahead == 0:
                                pass
                            else:
                                f.write('Repository is %s commits ahead in super repo %s!\n\n' % (diff.ahead, diff.target))


                f.write('\n')
                f.write('\n')
