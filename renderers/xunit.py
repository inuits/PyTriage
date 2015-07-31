import xunitgen

class Renderer(object):
    def __init__(self, runtime):
        self.runtime = runtime

    def render(self):
        destination = xunitgen.XunitDestination('xunit')
        runtime = self.runtime
        repos = [k[1] for k in sorted(runtime.repositories.items(), key=lambda x: x[0])]
        tests = []
        for repository in repos:

            if not repository.internal:
                continue
            tests = []
            if not repository.upstream:
                tests.append({'name': '%s has no upstream' % repository.name, 'fail': False})
            else:
                tests.append({'name': '%s is %s commit(s) behind upstream' % (repository.name, repository.behind), 'fail': repository.behind > 0})
                tests.append({'name': '%s is %s commit(s) ahead upstream' % (repository.name, repository.ahead), 'fail': repository.ahead > 0})
                tests.append({'name': '%s has at least one common commit with upstream' % (repository.name), 'fail': len(repository.diff.common_commits) == 0})
            for diff in repository.diffs.values():
                if diff.is_valid:
                    tests.append({'name': '%s is %s commit(s) behind in super repo %s' % (repository.name, diff.behind, diff.target), 'fail': diff.behind > 0})
                    tests.append({'name': '%s is %s commit(s) ahead in super repo %s' % (repository.name, diff.ahead, diff.target), 'fail': diff.ahead > 0})
            with xunitgen.Recorder(destination, repository.name, package_name=repository.name) as recorder:
                for test in tests:
                    with recorder.step(test['name']) as step:
                        if test['fail']:
                            step.error(test['name'])

