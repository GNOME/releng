#! /usr/bin/env python2
#
# Script to send an email to module maintainers
# Copyright (c) 2008 Frederic Peters <fpeters@gnome.org>
#
# Usage: mail-maintainers.py [ -q ] [ -s ] [ --force-email MAINTAINER ] [ -m MODULES ] MESSAGE
# 
# Options:
#   -s, --simulate        do not actually send emails
#   -q, --quiet           
#   -m MODULES, --modules=MODULES
#                         limit to those modules
#   --force-maintainers=MAINTAINERS
#                         force the maintainers to be MAINTAINERS
#   --blacklist=BLACKLIST
#                         ignore modules from this file (one module per line)
#
#  MESSAGE should point to a filename with the message to be sent, complete
#  with headers; for example:
#
#    ----------------------------------------------------------------------
#    To: $maintainer_emails
#    From: Vincent Untz <vuntz@gnome.org>
#    Subject: Howdy!
#    
#    Dear module maintainer,
#
#    Did you forget to send me icecream?
#    ----------------------------------------------------------------------
# 
#  There are a few variables that will be substituted in this file, namely:
#   - module_name, with the name of a module
#   - maintainer_emails, with the list of maintainers, with their email
#     addresses, to be useful in the To: header
#   - maintainers, with the list of maintainers, just their names
#
# Sample usages:
#   ./mail-maintainers.py --simulate roadmap-call-to-update.txt
#
#   ./mail-maintainers.py -m gnome-utils --force-maintainers=cosimoc \
#           roadmap-call-to-update.txt
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
#


import ldap
try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

import urllib2
import os
from optparse import OptionParser
import sys
from string import Template

SENDMAIL = '/usr/sbin/sendmail'
LDAP_URL = 'ldap://ldap-back'
MODULESET_URL = 'http://svn.gnome.org/svn/jhbuild/trunk/modulesets/gnome-suites-2.26.modules'

def sendmail(mssg):
    if options.simulate:
        return 0
    p = os.popen('%s -t' % SENDMAIL, 'w')
    p.write(mssg)
    return p.close()

def format_as_to(username):
    p = conn.search_s('ou=people,dc=gnome,dc=org', ldap.SCOPE_SUBTREE,
                      'uid=%s' % username) [0]
    name = p[1].get('cn')[0]
    email = p[1].get('mail')[0]
    email = '%s@svn.gnome.org' % (username,)
    return '%s <%s>' % (name, email)

def mail_maintainers(modules, message_filename):
    failed_modules = []

    message_template = Template(file(message_filename).read())

    modules_info = conn.search_s('ou=modules,dc=gnome,dc=org',
                        ldap.SCOPE_SUBTREE, 'objectClass=gnomeModule')
    modules_info.sort(lambda x,y: cmp(x[0], y[0]))

    for cn, info in modules_info:
        module_name = info.get('sn')[0]
        if module_name not in modules:
            continue
        maintainers = [x for x in info.get('maintainerUid')]
        if options.force_maintainers:
            maintainers = options.force_maintainers.split(',')
        maintainer_emails = [format_as_to(x) for x in maintainers]

        msg = message_template.substitute(
                maintainer_emails=', '.join(maintainer_emails),
                module_name=module_name,
                maintainers=', '.join(maintainers))
    
        print 'Sending email for %(module)s (%(maintainers)s)' % {
             'module': module_name, 'maintainers': ', '.join(maintainers)}

        if sendmail(msg):
            failed_modules.append(module_name)

    return failed_modules

if __name__ == '__main__':
    global options
    global conn

    parser = OptionParser(
            usage='%prog [ -q ] [ -s ] [ --force-email MAINTAINER ] [ -m MODULES ] MESSAGE')
    parser.add_option('-s', '--simulate', action='store_true', dest='simulate',
                help='do not actually send emails')
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet')
    parser.add_option('-m', '--modules', dest='modules',
                help='limit to those modules',  metavar='MODULES')
    parser.add_option('--force-maintainers', dest='force_maintainers',
                help='force the maintainers to be MAINTAINERS', metavar='MAINTAINERS')
    parser.add_option('--blacklist', dest='blacklist',
                help='ignore modules from this file (one module per line)',
                metavar='BLACKLIST',
                default='mail-maintainers.blacklisted-modules')
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_usage()
        print >> sys.stderr, 'You must pass a message'
        sys.exit(1)

    conn = ldap.initialize(LDAP_URL)

    if options.modules:
        modules = options.modules.split(',')
    else:
        suites = ET.parse(urllib2.urlopen(MODULESET_URL))
        modules = [x.attrib.get('id') for x in suites.getroot().getchildren() \
                   if x.tag not in ('repository', 'metamodule', 'include')]
        if options.blacklist:
            blacklist = [x.strip() for x in file(options.blacklist).readlines()]
            modules = [x for x in modules if not x in blacklist]

    if options.force_maintainers and len(modules) > 1:
        print >> sys.stderr, 'Forcing maintainers only works when there is a single module'
        sys.exit(1)

    if options.simulate:
        print '[[Simulation mode, no mail will be sent]]'

    failed_modules = mail_maintainers(modules, args[0])
    if failed_modules:
        print 'E: Failed to send message to:', ', '.join(failed_modules)

