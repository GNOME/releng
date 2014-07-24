#!/usr/bin/env python2
#
# Python script useful to maintainers.
# Copyright (C) 2007 Martyn Russell <martyn@imendio.com> 
#
#
# This script will:
#  - Prepare an announcement email ready for you to just click 'Send'
#
# Usage:
#  - You should run this script from the directory of the project you maintain.
#  - You need to specify an address to send to, this will NOT send it for you.
#  
# Changes:
#  - If you make _ANY_ changes, please send them in so I can incorporate them.
#
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

import sys
import os
import re
import optparse
import gnomevfs, gobject
import StringIO
from string import Template

# Script
script_name = 'Release Mail Templater'
script_version = '0.1'
script_about = 'A script to create a release email templates.'

# Email variables
email_signature = '''--
Regards,
Martyn

Imendio AB, http://www.imendio.com'''

# Templates
body_template = '''Hi,

A new version of $product is now available:

$release_url

The changes are:

$changes
$signature'''


def get_svn_root():
        info = os.popen('svn info --xml').read()

        key = '<root>'
        start = info.find(key)
        if start == -1:
                print 'Could not get Root (start) for subversion details'
                sys.exit(1)

        start += len(key)

        key = '</root>'
        end = info.find(key, start)
        if end == -1:
                print 'Could not get Root (end) for subversion details'
                sys.exit(1)

        return info[start:end]

def get_debian_product():
	f = open('debian/changelog', 'r')
	s = f.readline()
	f.close()

	exp = '^(?P<product>.*) \((?P<release>.*)\)'
	pattern = re.compile(exp, re.S | re.M)
	match = pattern.match(s)

	if match:
		product = match.group('product')
	else:
                print 'Could not get product and release from debian/changelog'
                sys.exit()

	return product

def get_debian_release():
        f = open('debian/changelog', 'r')
        s = f.readline()
        f.close()

        exp = '^(?P<product>.*) \((?P<release>.*)\) '
        pattern = re.compile(exp, re.S | re.M)
        match = pattern.match(s)

        if match:
                release = match.group('release')
        else:   
                print 'Could not get product and release from debian/changelog'
                sys.exit()

        return release

def get_debian_changes():
        f = open('debian/changelog', 'r')
        s = f.read()
        f.close()

        exp = '\A.*\n\n(?P<changes>(  \* .*\n)+)'
        pattern = re.compile(exp)
        match = pattern.match(s)

        if match:
                changes = match.group('changes')
        else:
                print 'Could not get changes from debian/changelog'
                sys.exit()

        return changes

def get_release_url():
	root = get_svn_root()
	release = get_debian_release()
	product = get_debian_product()

	url = "%s/tags/%s/%s" % (root, product, release)
	
	return url

def get_release_body(product, release_url, changes, signature):
        t = Template(body_template)
        text = t.substitute(locals())

	body = ''

 	for line in text.splitlines():
		body = body + line + '%0d'

	return body


# Start
usage = "usage: %s -t <email-address> [options]" % sys.argv[0]

popt = optparse.OptionParser(usage)
popt.add_option('-v', '--version',
                action = 'count',
                dest = 'version',
                help = 'show version information')
popt.add_option('-t', '--to',
                action = 'store',
                dest = 'to',
                help = 'Who to send the mail to')
popt.add_option('-c', '--cc',
                action = 'store',
                dest = 'cc',
                help = 'Who to cc the mail to')

(opts, args) = popt.parse_args()

if opts.version:
        print '%s %s\n%s\n' % (script_name, script_version, script_about)
        sys.exit()

if not opts.to:
	print 'No address to send the mail to specified'
	print usage
	sys.exit()

# Create template
product = get_debian_product()
release = get_debian_release()
changes = get_debian_changes()
release_url = get_release_url()
body = get_release_body(product, release_url, changes, email_signature)

subject = 'ANNOUNCE: %s %s released' % (product, release)

if opts.cc:
	url = 'mailto:%s?cc=%s&subject=%s&body=%s' % (opts.to, opts.cc, subject, body)
else:
	url = 'mailto:%s?subject=%s&body=%s' % (opts.to, subject, body)
	
gnomevfs.url_show(url)

