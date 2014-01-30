#! /usr/bin/env python

# Copyright (C) 2014  Frederic Peters
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


import datetime
import urllib2
import string
import subprocess
import hashlib
import os
import xml.etree.ElementTree as ET
import xml.etree.ElementTree
import json


CACHE_DIR = 'cache'
GIT_REPOSITORIES_DIR = '/scratch/jhbuild/src/'
modules = {}


def setup():
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)


def url_cache_read(url, prefix = ''):
    s = prefix + hashlib.md5(url).hexdigest()
    cache_file = os.path.join(CACHE_DIR, s)
    if os.path.exists(cache_file):
        return file(cache_file).read()
    try:
        st = urllib2.urlopen(url).read()
    except:
        return ''
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)
    file(cache_file, 'w').write(st)
    return st


def tryint(x):
    try:
        return int(x)
    except ValueError:
        return x

def version_cmp(x, y):
    try:
        return cmp([tryint(j) for j in x.split('.')], [tryint(k) for k in y.split('.')])
    except ValueError:
        return 0


def get_latest_gnome_version():
    versions = []
    for line in url_cache_read('ftp://ftp.gnome.org/pub/GNOME/teams/releng/').splitlines():
        version = line.strip().split()[-1]
        if version[0] in string.digits:
            versions.append(version)
    versions.sort(version_cmp)
    return versions[-1]

def pick_moduleset_infos():
    for line in url_cache_read(
            'ftp://ftp.gnome.org/pub/GNOME/teams/releng/%s/versions' % \
                    get_latest_gnome_version()).splitlines():
        if line.startswith('#') or not line.strip():
            continue
        category, name, version = line.split(':', 4)[:3]
        if not name in modules:
            modules[name] = {}
            modules[name]['module'] = name
        modules[name]['jhbuild_category'] = category
        modules[name]['jhbuild_version'] = version

def pick_doap_infos():
    DOAP_NS = 'http://usefulinc.com/ns/doap#'
    RDF_NS = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    RDF_RESOURCE = '{%s}resource' % RDF_NS
    for module in modules.keys():
        doap = url_cache_read('https://git.gnome.org/browse/%s/plain/%s.doap' % \
                (module, module))
        try:
            tree = ET.fromstring(doap)
        except xml.etree.ElementTree.ParseError:
            modules[module]['doap_error'] = True
            continue
        for attribute in ('{%s}name' % DOAP_NS,
                '{%s}shortdesc' % DOAP_NS,
                '{%s}description' % DOAP_NS,
                '{%s}programming-language' % DOAP_NS,
                ):
            key = attribute.split('}')[-1].replace('-', '')
            try:
                modules[module][key] = tree.find(attribute).text
            except AttributeError:
                pass

        for attribute in ('{%s}mailing-list' % DOAP_NS,
                '{%s}category' % DOAP_NS,
                '{%s}homepage' % DOAP_NS,
                '{%s}license' % DOAP_NS,
                '{%s}bug-database' % DOAP_NS,
                ):
            key = attribute.split('}')[-1].replace('-', '')
            try:
                modules[module][key] = tree.find(attribute).attrib.get(RDF_RESOURCE)
            except AttributeError:
                pass
        modules[module]['maintainers'] = []
        for maintainer in tree.findall('{%s}maintainer' % DOAP_NS):
            name = maintainer.find('{http://xmlns.com/foaf/0.1/}Person/{http://xmlns.com/foaf/0.1/}name').text
            try:
                t = maintainer.find('{http://xmlns.com/foaf/0.1/}Person/{http://xmlns.com/foaf/0.1/}mbox').attrib.get(RDF_RESOURCE)
            except AttributeError:
                t = None
            if t and t.startswith('mailto:'):
                email = t.split(':')[-1]
            try:
                userid = maintainer.find('{http://xmlns.com/foaf/0.1/}Person/{http://api.gnome.org/doap-extensions#}userid').text
            except AttributeError:
                userid = None
            modules[module]['maintainers'].append({'name': name,
                'email': email, 'userid': userid})

class Commit:
    date = None
    msg = u''
    files = None
    translation_commit = False
    author = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if type(self.date) is unicode:
            self.date = datetime.datetime.strptime(self.date, '%Y-%m-%d %H:%M')

    def to_dict(self):
        d = self.__dict__.copy()
        d['date'] = datetime.datetime.strftime(d['date'], '%Y-%m-%d %H:%M')
        return d

def get_git_log(cwd):
    cmd = ['git', 'log', '--stat', '--date=short', '--format=fuller']
    p = subprocess.Popen(cmd,
            close_fds=True,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=None,
            cwd=cwd)
    current_commit = None
    logs = []
    for line in p.stdout:
        if line.startswith('commit '):
            if current_commit:
                yield current_commit
            current_commit = Commit()
            current_commit.id = line[7:].strip()
            current_commit.files = []
            continue
        if line.startswith('AuthorDate:'):
            date = line.split(':')[-1].strip()
            current_commit.date = datetime.datetime.strptime(date, '%Y-%m-%d')
        elif line.startswith('Author:'):
            author = line.split(':')[-1].strip()
            current_commit.author = unicode(author, 'utf-8', errors='ignore')
        elif line.startswith('Commit:'):
            committer = line.split(':')[-1].strip()
            current_commit.committer = unicode(committer, 'utf-8', errors='ignore')
        elif line.startswith(' '*4):
            current_commit.msg += unicode(line[4:], 'utf-8', errors='ignore')
        elif line.startswith(' '):
            if '|' in line:
                current_commit.files.append(line.split('|')[0].strip())
                if '.po' in current_commit.files[-1]:
                    current_commit.translation_commit = True

    yield current_commit


def pick_git_infos():
    if not os.path.exists(os.path.join(CACHE_DIR, 'git')):
        os.mkdir(os.path.join(CACHE_DIR, 'git'))
    for i, module in enumerate(modules.keys()):
        print module
        if not os.path.exists(os.path.join(GIT_REPOSITORIES_DIR, module)):
            continue
        if os.path.exists(os.path.join(CACHE_DIR, 'git', '%s.json' % module)):
            git_log = [Commit(**x) for x in json.load(file(os.path.join(CACHE_DIR, 'git', '%s.json' % module)))]
        else:
            git_log = list(get_git_log(os.path.join(GIT_REPOSITORIES_DIR, module)))
            json.dump([x.to_dict() for x in git_log],
                    file(os.path.join(CACHE_DIR, 'git', '%s.json' % module), 'w'))
        modules[module]['git'] = {}
        most_recent_commit = [x for x in git_log if not x.translation_commit][0]
        modules[module]['git']['most_recent_commit'] = most_recent_commit.date.strftime('%Y-%m-%d')
        modules[module]['git']['first_commit'] = git_log[-1].date.strftime('%Y-%m-%d')
        one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
        modules[module]['git']['commits_in_12m'] = len(
                [x for x in git_log if x.date > one_year_ago])
        committers = {}
        authors = {}
        maintainers = {}
        for maintainer in modules[module].get('maintainers', []):
            maintainers[maintainer.get('email')] = 0
        for commit in git_log:
            if commit.date < one_year_ago:
                continue
            if commit.translation_commit:
                continue
            committers[commit.committer] = True
            committer_email = commit.committer.split('<')[1][:-1]
            if committer_email in maintainers.keys():
                maintainers[committer_email] += 1
            authors[commit.author] = True
        for maintainer in modules[module].get('maintainers', []):
            maintainer['commits_in_12m'] = maintainers.get(maintainer.get('email'))
        modules[module]['git']['committers_in_12m'] = len(committers.keys())
        modules[module]['git']['authors_in_12m'] = len(authors.keys())

        extensions = {}
        for filename in subprocess.Popen(['git', 'ls-files'],
                stdout=subprocess.PIPE,
                cwd=os.path.join(GIT_REPOSITORIES_DIR, module)).stdout.readlines():
            extension = os.path.splitext(filename.strip())[-1]
            if not extension in extensions.keys():
                extensions[extension] = 0
            extensions[extension] += 1
        language = None
        for extension in ('.vala', '.js', '.py', '.cpp', '.cc', '.cxx', '.c'):
            if extensions.get(extension) > 5:
                if extensions.get('.c') > extensions.get(extension, 0)*2:
                    extension = '.c'
            if extensions.get(extension) > 5:
                language = {
                    '.vala': 'Vala',
                    '.js': 'JavaScript',
                    '.py': 'Python',
                    '.cpp': 'C++',
                    '.cc': 'C++',
                    '.cxx': 'C++',
                    '.c': 'C'
                    }.get(extension)
                break
        modules[module]['git']['language'] = language


if __name__ == '__main__':
    pick_moduleset_infos()
    pick_doap_infos()
    pick_git_infos()
    json.dump(modules.values(), file('data.json', 'w'), indent=2)
