from jinja2 import Environment, PackageLoader
from time import ctime
import os.path
import logging
try:
    from coderev.codediff import CodeDiffer
    CODEDIFF_SUPPORTED=True
except:
    logging.warning('codediff not available')
    CODEDIFF_SUPPORTED=False

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
            CODEDIFF = CODEDIFF_SUPPORTED and repository.internal
            with open('reports/report-%s.html' % repository.name, 'w') as f:
                f.write(repo_template.render(runtime = runtime, repository = repository, gdate = ctime(), codediff=CODEDIFF))
            if CODEDIFF and repository.internal:
                with open('templates/codediff.html') as f:
                    with open('templates/codediff.css') as css:
                        if repository.upstream:
                            codediff = CodeDiffer(repository.internal.name, repository.upstream.name,
                                    'reports/%s-d-%s' % (repository.name, repository.diff.target),
                                    title='Diff between %s and upstream' % repository.name,
                                    show_common_files = True,
                                    )
                            codediff._index_template = f.read()
                            codediff._style_template = css.read()
                            codediff.make_diff()
                        for (name, diff) in repository.diffs.items():
                            if diff.is_valid:
                                print repository.internal.name
                                print diff.repo1.module().working_dir
                                codediff = CodeDiffer(repository.internal.name, os.path.relpath(diff.repo1.module().working_dir),
                                        'reports/%s-d-%s' % (repository.name, diff.target), wrap_num=80,
                                        title='Diff between %s and its submodule in %s' % (repository.name, diff.target),
                                        show_common_files = True,
                                        )
                                codediff._index_template = f.read()
                                codediff._style_template = css.read()
                                codediff.make_diff()

