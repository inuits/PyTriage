# PyTriage

A tool to compare your git modules with upstream and submodules in your internal repositories.

# Setup

    virtualenv .
    source bin/activate
    pip install -r requirements.txt

# How to use

    pytriage.py config.ini

# Configuration

This script is configured with a `.ini` file as follow:


    [defaults]
    branch = master
    disable_update=1
    internal_branch = {branch}
    internal_path = puppetmaster/modules/{name}
    internal_project = {name}
    internal_source = redmine
    upstream_branch = {branch}
    upstream_project = puppet-{name}
    upstream_source = github
    upstream_username = example
    
    [config]
    title = Inuits Git Repositories Barometer
    
    [source:github]
    url = https://github.com/{username}/{project}.git
    http_address = https://github.com/{username}/{project}
    commit_address = https://github.com/{username}/{project}/commit/{id}
    ticket_address = https://github.com/{username}/{project}/pull/{id}
    ticket_prefix = PR-
    ticketing = pull requests
    plugin = github
    
    [source:redmine]
    url = ssh://git@redmine.example.com/{path}.git
    apiurl = https://redmine.example.com/
    http_address = https://redmine.example.com/projects/{project}
    commit_address = https://redmine.example.com/projects/{project}/repository/revisions/{id}
    ticket_address = https://redmine.example.com/issues/{id}
    ticket_prefix = #
    ticketing = issues
    plugin = redmineplugin
    apikey = yourredmineapikeyhere
    
    [super:example]
    short_identifier = I
    internal_project = example
    internal_path = {internal_project}
    
    [super:anothersuperrepo]
    short_identifier = M
    internal_project = another-puppet
    internal_path = another/{internal_project}
    
    [super:hosting]
    short_identifier = H
    internal_project = hosting-puppet
    internal_path = {internal_project}
    
    [solr]
    upstream_username = KrisBuytaert
    internal_project = inuits-puppet-{name}
    internal_path = puppetmaster/modules/{internal_project}
    
    [mysqloak]
    disable_upstream = 1
    internal_project = mysql-oak
    internal_path = puppetmaster/modules/{internal_project}
    
    [mysql-tools]
    disable_upstream = 1
    
    [ldap]
    disable_upstream = 1
    internal_project = inuits-puppet-openldap
    internal_path = puppetmaster/modules/{internal_project}
    
    [stdlib]
    upstream_username = puppetlabs
    upstream_project = puppetlabs-{name}
    internal_project = puppetlabs-puppet-{name}
    internal_path = puppetmaster/modules/{internal_project}
    
    [opsweekly]
    disable_upstream=1
    internal_path = puppetmaster/{internal_project}
    
    [filemapper]
    upstream_username = adrienthebo
    internal_branch = upstream
    
    [foreman]
    upstream_username = theforeman
    
    [logster]
    upstream_username = KrisBuytaert
    
    [gdash]
    upstream_username = KrisBuytaert
    
    [gitorious]
    disable_upstream=1
    
    [gitolite]
    disable_upstream=1
    
    [lvm]
    upstream_username = puppetlabs
    disable_update=2
    upstream_project = puppetlabs-{name}
    internal_branch = upstream
    internal_project = lvm
    internal_path = puppetmaster/modules/{internal_project}


# Result

It generates a bunch of HTML files in the reports directory.

# License

See License.txt (spoil: GPLv2)
