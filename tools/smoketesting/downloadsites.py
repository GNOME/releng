# Copyright 2020, Abderrahim Kitouni
#
# based on code from convert-to-tarballs.py
#
# Copyright 2005-2008, Elijah Newren
# Copyright 2007-2009, Olav Vitters
# Copyright 2006-2009, Vincent Untz
# Copyright 2017, Codethink Limited
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

import os
import re
import requests
import time

from html.parser import HTMLParser
from posixpath import join as posixjoin # Handy for URLs
from urllib.parse import unquote

# Classes that define the different types of sites we can download from
class DownloadSite:
    def __init__(self, baseurl):
        self.modules = set()
        self.baseurl = baseurl
    def find_tarball(self, modulename, max_version, wantchecksum):
        raise NotImplementedError

def perform_request(location):
    req = None
    while True:
        req = requests.get(location, headers={'user-agent': 'org.gnome.Releng/0.0.1'}, timeout=15.0)
        if req.status_code == 429:
            # Too Many Requests: we hit a rate limit
            time.sleep(1)
            continue
        req.raise_for_status()
        return req

class Tarballs(DownloadSite):
    def __init__(self, baseurl):
        super().__init__(baseurl)

    def find_tarball(self, modulename, max_version, wantchecksum):
        good_dir = re.compile(r'^([0-9]+\.)*[0-9]+/?$')
        def hasdirs(x): return good_dir.search(x)
        def fixdirs(x): return re.sub(r'^([0-9]+\.[0-9]+)/?$', r'\1', x)

        location = self.baseurl.format(module=modulename)
        files = []

        while True:
            if "freedesktop.org" in location:
                break

            req = perform_request(location)
            files = get_links(req.text)

            # Check to see if we need to descend to a subdirectory
            newdirs = [fixdirs(dir) for dir in files if hasdirs(dir)]
            if newdirs:
                assert max_version is None or len(max_version.split('.')) <= 2, "limit can't have micro version when the project uses subdirs"
                newdir = get_latest_version(newdirs, max_version)
                location = posixjoin(req.url, newdir, "")
            else:
                break

        basenames = set()
        tarballs = []
        extensions = ['.tar.xz', '.tar.bz2', '.tar.gz']

        # Has to be checked by extension first; we prefer .tar.xz over .tar.bz2 and .tar.gz
        for ext in extensions:
            for file in files:
                basename = file[:-len(ext)] # only valid when file ends with ext
                if file.endswith(ext) and basename not in basenames:
                    basenames.add(basename)
                    tarballs.append(file)

        re_tarball = r'^'+re.escape(modulename)+r'[_-](([0-9]+[\.\-])*[0-9]+)(\.orig)?\.tar.*$'

        tarballs = [t for t in tarballs if re.search(re_tarball, t)]
        versions = [re.sub(re_tarball, r'\1', t) for t in tarballs]

        if not versions:
            return None, None, None

        version = get_latest_version(versions, max_version)
        index = versions.index(version)

        location = posixjoin(location, tarballs[index])

        return location, version, None

class GNOME(DownloadSite):
    def __init__(self, baseurl):
        super().__init__(baseurl)

        resp = perform_request(self.baseurl)

        moduleregex = re.compile('([^/]+)/')

        for link in sorted(get_links(resp.text)):
            m = moduleregex.match(link)
            if m:
                self.modules.add(m.group(1))

    def find_tarball(self, modulename, max_version, wantchecksum):
        if modulename not in self.modules:
            return None, None, None

        resp = perform_request(posixjoin(self.baseurl, modulename, 'cache.json'))
        versions = resp.json()[1][modulename]
        latest = get_latest_version(versions.keys(), max_version)

        if not latest:
            return None, None, None

        extensions = ['tar.xz', 'tar.bz2', 'tar.gz']
        for ext in extensions:
            if ext in versions[latest]:
                tarball = versions[latest][ext]
                break
        else:
            # unknown extension
            return None, None, None

        checksum = None
        if wantchecksum and 'sha256sum' in versions[latest]:
            resp = perform_request(posixjoin(self.baseurl, modulename, versions[latest]['sha256sum']))

            basename = os.path.basename(tarball)
            for l in resp.text.splitlines():
                l = l.split()
                if basename == l[1]:
                    checksum = l[0]
                    break

        return posixjoin(self.baseurl, modulename, tarball), latest, checksum

# mapping from name to DownloadSite subclasses
SITE_KINDS = {
    'tarballs': Tarballs,
    'gnome': GNOME,
}

# utility functions
def get_links(html):
    class urllister(HTMLParser):
        def reset(self):
            HTMLParser.reset(self)
            self.urls = []

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                href = [unquote(v) for k, v in attrs if k=='href']
                if href:
                    self.urls.extend(href)

    parser = urllister()
    parser.feed(html)
    parser.close()
    return parser.urls


re_version = re.compile(r'([-.]|\d+|[^-.\d]+)')


# https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
def cmp(a, b):
    return (a > b) - (a < b)


def version_cmp(a, b):
    """Compares two versions

    Returns
    -1 if a < b
    0  if a == b
    1  if a > b

    Logic from Bugzilla::Install::Util::vers_cmp

    Logic actually carbon copied from ftpadmin
    https://gitlab.gnome.org/Infrastructure/sysadmin-bin/-/blob/78880cd100f6a73acc9dbd8c0dc3cb9a52e6fc23/ftpadmin#L88-141
    """
    assert(a is not None)
    assert(b is not None)

    A = re_version.findall(a.lstrip('0'))
    B = re_version.findall(b.lstrip('0'))

    while A and B:
        a = A.pop(0)
        b = B.pop(0)

        if a == b:
            continue
        elif a == '-':
            return -1
        elif b == '-':
            return 1
        elif a == '.':
            return -1
        elif b == '.':
            return 1
        elif a.isdigit() and b.isdigit():
            c = cmp(a, b) if (a.startswith('0') or b.startswith('0')) else cmp(int(a, 10), int(b, 10))
            if c:
                return c
        elif a.isalpha() and b.isdigit():
            if a == 'alpha' or a == 'beta' or a == 'rc':
                return -1
        elif a.isdigit() and b.isalpha():
            if b == 'alpha' or b == 'beta' or b == 'rc':
                return 1
        else:
            c = cmp(a.upper(), b.upper())
            if c:
                return c

    return cmp(len(A), len(B))


def get_latest_version(versions, max_version=None):
    """Gets the latest version number

    if max_version is specified, gets the latest version number before
    max_version"""
    latest = None
    versions = [ v.rstrip(os.path.sep) for v in versions ]
    for version in versions:
        if ( latest is None or version_cmp(version, latest) > 0 ) \
           and ( max_version is None or version_cmp(version, max_version) < 0 ):
            latest = version
    return latest
