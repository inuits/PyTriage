#!/usr/bin/env python
import logging
import argparse
from git import Repo
from string import Formatter
from configparser import ConfigParser
from time import ctime

class NamedRepo(Repo):
    def __init__(self, name, *args, **kwargs):
        self.name=name
        return super(NamedRepo, self).__init__(*args, **kwargs)
    def module(self):
        return self

from jinja2 import Environment, PackageLoader

def normalizegiturl(url):
    if url.endswith('.git'):
        return normalizegiturl(url[:-4])
    if url.startswith('ssh+git:'):
        return normalizegiturl('ssh%s' % url[7:])
    if url.startswith('git+ssh:'):
        return normalizegiturl('ssh%s' % url[7:])
    return url

def commitmessagefilter(message):
    firstline = message.split("\n")[0].encode("unicode-escape")
    if len(firstline) > 80:
        return '%s...' % firstline[0:80]
    return firstline

def datetimefilter(date):
    return ctime(date)

def numberfilter(number):
    if number is None:
        return 'N/A'
    return number

def numberclassfilter(number):
    if number is None:
        return 'default'
    if number == 0:
        return 'success'
    else:
        return 'primary'

class LazyFormatter(Formatter):
    def __init__(self, namespace={}):
        Formatter.__init__(self)

    def get_value(self, key, args, kwds):
        if isinstance(key, str) or isinstance(key, unicode):
            try:
                return kwds[key]
            except KeyError:
                return '{%s}' % key
        else:
            self.get_value(key, args, kwds)

fmt = LazyFormatter()

class TriageObject(object):
    def __init__(self, runtime, name):
        self.runtime = runtime
        self.name = name
        self.properties = {}

    def __getattr__(self, name):
        if self.properties.has_key(name):
            return self.properties[name]
        else:
            raise AttributeError

    def add_property(self, key, val):
        self.properties[key] = val

    def check_property(self, key, value='1'):
        return self.properties.has_key(key) and self.properties[key] == value

class Ticket(TriageObject):

    def __init__(self, repository, *args, **kwargs):
        super(Ticket, self).__init__(*args, **kwargs)
        self.repository = repository

    def set_external_ticket(self):
        self.external = self.repository.source.externalticket(self.repository, self.reference)
        self.repository.source.tickets_status.add(self.external.status)
        print self.repository.source.tickets_status


class Source(TriageObject):
    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.tickets_status = set()

    def configure(self):
        self.externalticket = NoPluginTicket
        if self.properties.has_key('plugin'):
            loadedplugin = __import__('plugins.%s' % self.plugin)
            self.externalticket = getattr(loadedplugin, self.plugin).Ticket

class NoPluginTicket(object):
    def __init__(self, repository, reference):
        self.repository = repository
        self.reference = reference
        self.status = ('pending', 'N/A')
        self.title = 'Ticket %s in %s' % (self.reference, self.repository.name)

class TriageCommit(TriageObject):
    def __init__(self, repo, commit, *args, **kwargs):
        super(TriageCommit, self).__init__(*args, **kwargs)
        self.commit = commit
        self.repo = repo

    def get_url(self):
        return fmt.format(self.repo.commit_address, id=self.commit.hexsha)

    def url(self, cssclass=""):
        return '<a href="%s" class="%s">%s</a>' % (self.get_url(), cssclass,self.commit.hexsha[0:8])

    def author(self):
        return u'%s &lt;%s&gt;' % (self.commit.author.name.encode('unicode-escape'), self.commit.author.email.encode('unicode-escape'))

    def message(self):
        msg = self.commit.message.split('\n')[0].encode('unicode-escape')
        if len(msg) > 80:
            return '%s...' % msg[0:80]
        return msg

    def adate(self):
        return datetimefilter(self.commit.authored_date)

class CommitDiff(TriageObject):
    def __init__(self, repo1, repo2, target, src1, src2, *args, **kwargs):
        super(CommitDiff, self).__init__(*args, **kwargs)
        self.is_valid = repo1 and repo2
        self.target = target
        self.repo1 = repo1
        self.repo2 = repo2
        self.reposrc1 = src1
        self.reposrc2 = src2
        self.behind = None
        self.ahead = None
        if self.is_valid:
            self.run()

    def run(self):
        commits = {}
        commits[self.repo1.name] = []
        commits[self.repo2.name] = []
        for repo in (self.repo1, self.repo2):
            for commit in repo.module().iter_commits():
                if len(commit.parents) < 2:
                    commits[repo.name].append(commit.hexsha)

        self.unique_commits = {self.repo1.name: [], self.repo2.name: []}
        for (repoa, repob, src) in ((self.repo1, self.repo2, self.reposrc1), (self.repo2,self.repo1, self.reposrc2)):
            for commit in repoa.module().iter_commits():
                if len(commit.parents) < 2:
                    if commit.hexsha not in commits[repob.name]:
                        self.unique_commits[repoa.name].append(TriageCommit(src,commit,self,'Commit'))
        (repoa, repob) = (self.repo1, self.repo2)

        self.common_commits = []
        for commit in repoa.module().iter_commits():
            if len(commit.parents) < 2:
                if commit.hexsha in commits[repob.name]:
                    self.common_commits.append(TriageCommit(self.reposrc1,commit,self,'Unique Commit'))

        self.behind = len(self.unique_commits[self.repo2.name])
        self.ahead = len(self.unique_commits[self.repo1.name])


class Remote(TriageObject):
    def __init__(self, is_internal, parent, *args, **kwargs):
        super(Remote, self).__init__(*args, **kwargs)
        self.is_internal = is_internal
        self.parent = parent
        if self.is_internal:
            self.status = 'internal'
        else:
            self.status = 'upstream'
        self.source = None
        self.tickets = []

class Repository(TriageObject):
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)
        self.properties['name'] = self.name
        self.upstream = None
        self.internal = None
        self.behind = None
        self.ahead = None
        self.diff = None
        self.diffs = {}

    # 0: no internal
    # 2: OK
    # 4: INFO: behind/ahead master
    # 6: Warnig: Submodule BEHIND
    # 8: DANGER: Submodule AHEAD
    def status_color(self):
        level = 0
        if not self.internal:
            return self.runtime.get_color(level)
        for diff in self.diffs.values():
            if diff.behind == diff.ahead == None or diff.behind == diff.ahead == 0:
                pass
            elif diff.behind > 0:
                level = max(level, 6)
            elif diff.ahead > 0:
                level = max(level, 8)
        if self.behind == self.ahead == 0 or self.behind == self.ahead == None:
            level = max(level, 2)
        else:
            level = max(level, 4)
        return self.runtime.get_color(level)

    def add_remote(self, remote):
        if self.check_property('disable_%s' % remote):
            return

        remote_obj = Remote(remote == 'internal', self, self.runtime, '%s-%s' % (self.name, remote))
        source = self.properties['%s_source' % remote]
        remote_obj.source = self.runtime.sources[source]
        for (key, val) in self.properties.items():
            if key.startswith('%s_' % remote):
                keyname = '_'.join(key.split('_')[1:])
                remote_obj.add_property(keyname, fmt.vformat(val, [], remote_obj.properties))
        for (key, val) in remote_obj.source.properties.items():
            if not remote_obj.properties.has_key(key):
                remote_obj.add_property(key, fmt.vformat(val, [], remote_obj.properties))
        if remote == 'internal':
            self.internal = remote_obj
        else:
            self.upstream = remote_obj

    def configure_remotes(self):
        self.configure_remote(self.internal)
        self.configure_remote(self.upstream)

    def get_submodule(self, name):
        try:
            return [s for s in self.runtime.repo.submodules if s.path == name][0]
        except IndexError:
            return None

    def get_level2_submodule(self, url):
        try:
            this_repo = NamedRepo('%s-internal' % self.name, '%s-internal' % self.name)
            return [u for u in this_repo.submodules if normalizegiturl(u.url) == normalizegiturl(url)][0]
        except IndexError:
            return None

    def configure_remote(self, remote):
        if remote is None:
            return
        if self.check_property('disable_%s' % remote.status):
            return
        if self.check_property('super') and remote.status == 'upstream':
            return
        try:
            repo = NamedRepo(remote.name, remote.name)
        except:
            Repo.init(remote.name)
            repo = NamedRepo(remote.name, remote.name)
        try:
            gitremote = repo.remotes.origin
        except:
            gitremote = repo.create_remote('origin', remote.url)
            logging.debug('Creating remote for %s' % remote.name)
        if gitremote.url != remote.url:
            cw = gitremote.config_writer
            cw.set("url", remote.url)
            logging.debug('Changing remote url for %s' % remote.name)
            cw.release()
        #repo.delete_head('master')
        if not remote.parent.check_property('disable_update'):
            logging.debug('Fetching remote for %s...' % remote.name)
            gitremote.fetch()
            if remote.parent.check_property('super'):
                logging.debug('Running git submodules sync')
                repo.git.submodule('sync')
            logging.debug('Fetching remote for %s. done.' % remote.name)
        if not remote.branch in gitremote.refs:
            logging.error('Can not find %s branch in %s')
            exit(1)
        if not 'master' in repo.heads:
            branch = repo.create_head('master', gitremote.refs[remote.branch]).set_tracking_branch(gitremote.refs[remote.branch])
        else:
            branch = repo.heads['master']
            branch.set_tracking_branch(gitremote.refs[remote.branch])

        repo.head.set_reference(branch)
        repo.head.reset(gitremote.refs[remote.branch].commit, index=True, working_tree=True)
        if not remote.parent.check_property('disable_update') and remote.parent.check_property('super'):
            for sm in repo.submodules:
                logging.debug('Updating %s...' % sm.path)
                sm.update(force=True, recursive=False)

    def add_remotes(self):
        self.add_remote('internal')
        self.add_remote('upstream')

    def setup(self):
        self.add_remotes()
        self.configure_remotes()

class Super(Repository):
    pass

class TriageRuntime:
    def __init__(self):
        self.defaults = {}
        self.sources = {}
        self.repositories = {}
        self.super_repositories = {}
        self.parse_options()
        self.title = 'Git Repositories Barometer'

    def get_status_color_values(self):
        return xrange(0,9,2)

    def get_color(self, value):
        return ['default','','success','','primary','','warning','','danger'][value]

    def get_color_info(self, value):
        if value == 0:
            return ('No module', 'That module has no internal repository')
        if value == 2:
            return ('Up-to-date', 'Everything is in sync: upstream and super repos')
        if value == 4:
            return ('Out-of-sync/upstream', 'Upstream is behind or ahead internal repository')
        if value == 6:
            return ('Behind/super', 'Out of sync with super repository (behind)')
        if value == 8:
            return ('Ahead/super', 'Out of sync with super repository (ahead)')

    def parse_options(self):
        parser = argparse.ArgumentParser(prog='PyTriage',
                description='''
                This software is used to check the state of internal git
                repositories compared to upstream repositories. It can also
                compare the git repositories within multiple super repositories.
                Please take a look at the examples directory for some configurations.''',
                epilog='''Distributed under the GPL License, version 2. See LICENSE.txt''')
        parser.add_argument('config', help='configuration file to use')
        parser.add_argument('--debug', '-d', help='Print debug information', action='store_true')
        args = parser.parse_args()
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
        self.config_file = args.config

    def get_section_type(self, section):
        if section == 'config':
            return ('config', section)
        if section == 'defaults':
            return ('defaults', section)
        if ':' in section:
            prefix = section.split(':')[0]
            suffix = section.split(':')[1]
        else:
            prefix = None
        if prefix is not None:
            return (prefix, suffix)
        else:
            return ('repository', section)

    def parse_configuration(self):
        config = ConfigParser(strict = True, interpolation = None)
        config.read(self.config_file)
        for section in config.sections():
            (section_type, name) = self.get_section_type(section)
            if section_type == 'config':
                self.set_config(config, name)
            elif section_type == 'defaults':
                self.set_defaults(config, name)
            elif section_type == 'source':
                self.add_source(config, section, name)
            elif section_type == 'super':
                self.add_repository(config, section, name, super_repo=True)
            elif section_type == 'repository':
                self.add_repository(config, section, name)


    def set_config(self, config, section):
        logging.debug('Setting configuration')
        for (key, val) in config.items(section):
            if key == 'title':
                self.title = val

    def set_defaults(self, config, section):
        logging.debug('Setting defaults')
        for (key, val) in config.items(section):
            self.defaults[key] = fmt.vformat(val, [], self.defaults)

    def add_source(self, config, section, name):
        logging.debug('Adding source %s' % name)
        source = Source(self, name)
        self.sources[name] = source
        for (key, val) in config.items(section):
            defaults = self.defaults.copy()
            defaults.update(source.properties)
            source.add_property(key, fmt.vformat(val, [], defaults))
        source.configure()

    def add_repository(self, config, section, name, super_repo=False):
        logging.debug('Adding repository %s' % name)
        if super_repo:
            repo = Super(self, name)
            repo.add_property('super', '1')
            repo.add_property('disable_upstream', '1')
            self.super_repositories[name] = repo
        else:
            repo = Repository(self, name)
            self.repositories[name] = repo
        for (key, val) in self.defaults.items():
            repo.add_property(key, fmt.vformat(val, [], repo.properties))
        for (key, val) in config.items(section):
            defaults = self.defaults.copy()
            defaults.update(repo.properties)
            repo.add_property(key, fmt.vformat(val, [], defaults))
        repo.setup()

    def compare_submodules(self):
        for (name, repository) in self.repositories.items():
            if len(filter(None, (repository.upstream, repository.internal))) == 2:
                logging.debug('Comparing repository %s with upstream' % name)
                sm = {}
                sm['upstream'] = NamedRepo(repository.upstream.name, repository.upstream.name)
                sm['internal'] = NamedRepo(repository.internal.name, repository.internal.name)
                diff = CommitDiff(sm['internal'], sm['upstream'], 'upstream', repository.internal, repository.upstream, self, 'Diff between %s and %s' % (repository.internal.name, repository.upstream.name))
                repository.diff = diff
                repository.behind = diff.behind
                repository.ahead = diff.ahead
            else:
                repository.diff = TriageObject(self, 'Diff between %s-internal and %s-upstream' % (repository.name, repository.name))

    def compare_submodule_with_super(self, name, repository, super_repo):
        if repository.internal:
            logging.debug('Comparing repository %s with super repo %s' % (name, super_repo.name))
            sm = {}
            sm['internal'] = NamedRepo(repository.internal.name, repository.internal.name)
            sm['super'] = super_repo.get_level2_submodule(repository.internal.url)
            diff = CommitDiff(sm['super'], sm['internal'], super_repo.name, repository.internal, repository.internal, self, 'Status of %s in %s' % (repository.internal.name, super_repo.internal.name))
            repository.diffs[super_repo.short_identifier] = diff

    def compare_submodules_with_super(self):
        for (name, repository) in self.repositories.items():
            for (super_name, super_repository) in self.super_repositories.items():
                self.compare_submodule_with_super(name,repository,super_repository)

    def run(self):
        logging.debug('Parsing configuration...')
        self.parse_configuration()
        logging.debug('Parse Tickets...')
        self.parse_tickets()
        logging.debug('Comparing versions')
        self.compare_submodules()
        self.compare_submodules_with_super()
        logging.debug('Generating report')
        self.generate_report()

    def parse_tickets(self):
        for (name, repository) in self.repositories.items():
            logging.debug('Parsing tickets in %s' % name)
            for sm in filter(None, (repository.upstream, repository.internal)):
                if sm.properties.has_key('tickets'):
                    for ticket in sm.properties['tickets'].split():
                        reference = ticket
                        if sm.properties.has_key('ticket_%s_title' % reference):
                            title = '%s%s - %s' % (sm.ticket_prefix, reference, sm.properties['ticket_%s_title' % reference])
                        else:
                            title = '%s%s' % (sm.ticket_prefix, reference)
                        t = Ticket(sm, self, title)
                        t.add_property('id', reference)
                        t.add_property('reference', reference)
                        t.add_property('url', fmt.vformat(sm.ticket_address, [], t.properties))
                        t.set_external_ticket()
                        sm.tickets.append(t)

    def generate_report(self):
        env = Environment(loader=PackageLoader('pytriage', 'templates'))
        env.filters['datetimefilter'] = datetimefilter
        env.filters['numberfilter'] = numberfilter
        env.filters['numberclassfilter'] = numberclassfilter
        env.filters['commitmessage'] = commitmessagefilter
        with open('reports/index.html', 'w') as f:
            template = env.get_template('home.html')
            repos = [k[1] for k in sorted(self.repositories.items(), key=lambda x: x[0])]
            f.write(template.render(runtime = self, repos = repos, gdate = ctime()))
        repo_template = env.get_template('repository.html')
        for repository in self.repositories.values():
            with open('reports/report-%s.html' % repository.name, 'w') as f:
                f.write(repo_template.render(runtime = self, repository = repository, gdate = ctime()))


if __name__ == '__main__':
    TriageRuntime().run()
