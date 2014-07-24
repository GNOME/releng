#! /usr/bin/env python2
#
# Script to publish the list of module maintainers
# Copyright (c) 2012 Frederic Peters <fpeters@gnome.org>
#
# Usage: publish-maintainers.py [ -q ] [ -m MODULES ] FILENAME
# 
# Options:
#   -q, --quiet           
#   -m MODULES, --modules=MODULES
#                         limit to those modules
#   --blacklist=BLACKLIST
#                         ignore modules from this file (one module per line)
#
# Notes:
#  + You should run this script on a machine that can connect to
#    the LDAP server
#  + You should check that MODULESET_URL points to the current jhbuild
#    moduleset.
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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import ldap
try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

import urlparse
import urllib2
import os
from optparse import OptionParser
import sys
import StringIO

LDAP_URL = 'ldap://ldap-back'
MODULESET_URL = 'http://git.gnome.org/browse/jhbuild/plain/modulesets/gnome-apps-3.6.modules'

class Module:
    name = None
    moduleset = None
    metamodule = None
    maintainers = None

    def __init__(self, name, moduleset, metamodule):
        self.name = name
        self.moduleset = moduleset
        self.metamodule = metamodule


def format_as_name(username):
    p = conn.search_s('ou=people,dc=gnome,dc=org', ldap.SCOPE_SUBTREE,
                      'uid=%s' % username) [0]
    name = p[1].get('cn')[0]
    return name

def lookup_maintainers(modules):
    modules_info = conn.search_s('ou=modules,dc=gnome,dc=org',
                        ldap.SCOPE_SUBTREE, 'objectClass=gnomeModule')
    modules_info.sort(lambda x,y: cmp(x[0], y[0]))

    for cn, info in modules_info:
        module_name = info.get('sn')[0]
        try:
            module = [x for x in modules if x.name == module_name][0]
        except IndexError:
            continue
        maintainers = [x for x in info.get('maintainerUid')]
        maintainer_names = [format_as_name(x) for x in maintainers]
        module.maintainers = maintainer_names


def get_list_of_modules(url):
    suites = ET.parse(urllib2.urlopen(url))
    moduleset = '-'.join(url.split('/')[-1].split('-')[:-1])
    metamodules = {}
    for metamodule in [x for x in suites.getroot().getchildren() if x.tag == 'metamodule']:
        for module in metamodule.findall('dependencies/dep'):
            metamodules[module.attrib.get('package')] = metamodule.attrib.get('id')
    modules = [Module(x.attrib.get('id'), moduleset, metamodules.get(x.attrib.get('id'))) \
               for x in suites.getroot().getchildren() \
               if x.tag not in ('repository', 'metamodule', 'include', 'systemmodule')]
    for include in [x.attrib.get('href') for x in suites.getroot().getchildren() \
                    if x.tag == 'include']:
        include_url = urlparse.urljoin(url, include)
        modules.extend(get_list_of_modules(include_url))
    return modules

if __name__ == '__main__':
    global options
    global conn

    parser = OptionParser(
            usage='%prog [ -q ] [ -m MODULES ] FILENAME')
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet')
    parser.add_option('-m', '--modules', dest='modules',
                help='limit to those modules',  metavar='MODULES')
    parser.add_option('--blacklist', dest='blacklist',
                help='ignore modules from this file (one module per line)',
                metavar='BLACKLIST')
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_usage()
        print >> sys.stderr, 'You must pass a filename'
        sys.exit(1)

    filename = args[0]

    conn = ldap.initialize(LDAP_URL)

    if options.modules:
        modules = options.modules.split(',')
    else:
        modules = get_list_of_modules(MODULESET_URL)
        if options.blacklist:
            blacklist = [x.strip() for x in file(options.blacklist).readlines()]
            modules = [x for x in modules if not x.name in blacklist]

    lookup_maintainers(modules)

    fd = file(filename, 'w')
    print >> fd, '<html><head><link rel="stylesheet" href="maintainers.css"/></head><body>'
    for moduleset in ('gnome-suites-core-deps-base', 'gnome-suites-core-deps', 'gnome-suites-core', 'gnome-apps'):
        modules_subset = [x for x in modules if x.moduleset == moduleset and (moduleset != 'gnome-apps' or x.metamodule == 'meta-gnome-apps-tested')]
        print >> fd, '<h1>%s</h1>' % moduleset
        print >> fd, '<dl>'
        for module in sorted(modules_subset, lambda x,y:cmp(x.name, y.name)):
            if module.maintainers is None: continue
            print >> fd, '<dt>%s</dt>' % module.name
            print >> fd, '<dd>%s</dd>' % ', '.join(module.maintainers)
        print >> fd, '</dl>'

    print >> fd, '</body></html>'
