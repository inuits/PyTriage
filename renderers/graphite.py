import graphitesend
import logging

class Renderer(object):
    def __init__(self, runtime):
        self.runtime = runtime

    def render(self):
        runtime = self.runtime
        metrics = {'upstream.repos.behind': 0,
                   'upstream.repos.ahead': 0,
                   'upstream.commits.ahead': 0,
                   'upstream.commits.behind': 0}
        for repository in runtime.repositories.values():
            if repository.behind and repository.behind > 0:
                metrics['upstream.repos.behind'] += 1
                metrics['upstream.commits.behind'] += repository.behind
            if repository.ahead and repository.ahead > 0:
                metrics['upstream.repos.ahead'] += 1
                metrics['upstream.commits.ahead'] += repository.ahead
            for (name, diff) in repository.diffs.items():
                if diff.is_valid:
                    for r in ('repos', 'commits'):
                        for b in ('behind', 'ahead'):
                            if not metrics.has_key('%s.%s.%s' % (diff.target, r, b)):
                                metrics['%s.%s.%s' % (diff.target, r, b)] = 0
                    if diff.behind and diff.behind > 0:
                        metrics['%s.repos.behind' % diff.target] += 1
                        metrics['%s.commits.behind' % diff.target] += diff.behind
                    if diff.ahead and diff.ahead > 0:
                        metrics['%s.repos.ahead' % diff.target] += 1
                        metrics['%s.commits.ahead' % diff.target] += diff.ahead
        if not self.runtime.config.has_key('graphite_host'):
            logging.error('No graphite server in config file')
        else:
            if not self.runtime.config.has_key('graphite_prefix'):
                prefix = 'pytriage'
            else:
                prefix = self.runtime.config['graphite_prefix']
            logging.info('Sending data to graphite')
            g = graphitesend.init(prefix=prefix, system_name='', graphite_server=self.runtime.config['graphite_host'])
            g.send_dict(metrics)


