from jinja2 import Environment, PackageLoader
from time import ctime

def commitmessagefilter(message):
    firstline = message.split("\n")[0].encode("unicode-escape")
    if len(firstline) > 80:
        return '%s...' % firstline[0:80]
    return firstline

def datetimefilter(date):
    return ctime(int(date))

def numberfilter(number):
    if number is None:
        return 'N/A'
    return number

def numberclassfilter(number, diff):
    if number is None:
        return 'default'
    if number == 0:
        return 'success'
    elif len(diff.common_commits) == 0:
        return 'danger'
    else:
        return 'primary'

class Renderer(object):
    def __init__(self, runtime):
        self.runtime = runtime

    def render(self):
        runtime = self.runtime
        env = Environment(loader=PackageLoader('pytriage', 'templates'))
        env.filters['datetimefilter'] = datetimefilter
        env.filters['numberfilter'] = numberfilter
        env.filters['numberclassfilter'] = numberclassfilter
        env.filters['commitmessage'] = commitmessagefilter
        with open('reports/index.html', 'w') as f:
            template = env.get_template('home.html')
            repos = [k[1] for k in sorted(runtime.repositories.items(), key=lambda x: x[0])]
            f.write(template.render(runtime = runtime, repos = repos, gdate = ctime()))
        repo_template = env.get_template('repository.html')
        for repository in runtime.repositories.values():
            with open('reports/report-%s.html' % repository.name, 'w') as f:
                f.write(repo_template.render(runtime = runtime, repository = repository, gdate = ctime()))
