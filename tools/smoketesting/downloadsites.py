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

import re
import requests
import os

from html.parser import HTMLParser
from posixpath import join as posixjoin # Handy for URLs

# Classes that define the different types of sites we can download from
class DownloadSite:
    def __init__(self, baseurl):
        self.modules = set()
        self.baseurl = baseurl
    def find_tarball(self, modulename, max_version, wantchecksum):
        raise NotImplementedError

class Tarballs(DownloadSite):
    def __init__(self, baseurl):
        super().__init__(baseurl)

    def find_tarball(self, modulename, max_version, wantchecksum):
        good_dir = re.compile('^([0-9]+\.)*[0-9]+/?$')
        def hasdirs(x): return good_dir.search(x)
        def fixdirs(x): return re.sub(r'^([0-9]+\.[0-9]+)/?$', r'\1', x)

        location = self.baseurl.format(module=modulename)

        while True:
            req = requests.get(location)
            req.raise_for_status()
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

        re_tarball = r'^'+re.escape(modulename)+'[_-](([0-9]+[\.\-])*[0-9]+)(\.orig)?\.tar.*$'

        tarballs = [t for t in tarballs if re.search(re_tarball, t)]
        versions = [re.sub(re_tarball, r'\1', t) for t in tarballs]

        if not versions:
            return None, None, None

        version = get_latest_version(versions, max_version)
        index = versions.index(version)

        location = posixjoin(location, tarballs[index])

        return location, version, None

# mapping from name to DownloadSite subclasses
SITE_KINDS = {
    'tarballs': Tarballs,
}

# utility functions
def get_links(html):
    class urllister(HTMLParser):
        def reset(self):
            HTMLParser.reset(self)
            self.urls = []

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                href = [v for k, v in attrs if k=='href']
                if href:
                    self.urls.extend(href)

    parser = urllister()
    parser.feed(html)
    parser.close()
    return parser.urls

def get_latest_version(versions, max_version):
    def bigger_version(a, b):
        a_nums = a.split('.')
        b_nums = b.split('.')
        num_fields = min(len(a_nums), len(b_nums))
        for i in range(0,num_fields):
            if   int(a_nums[i]) > int(b_nums[i]):
                return a
            elif int(a_nums[i]) < int(b_nums[i]):
                return b
        if len(a_nums) > len(b_nums):
            return a
        else:
            return b

    # This is nearly the same as _bigger_version, except that
    #   - It returns a boolean value
    #   - If max_version is None, it just returns False
    #   - It treats 2.13 as == 2.13.0 instead of 2.13 as < 2.13.0
    # The second property is particularly important with directory hierarchies
    def version_greater_or_equal_to_max(a, max_version):
        if not max_version:
            return False
        a_nums = a.split('.')
        b_nums = max_version.split('.')
        num_fields = min(len(a_nums), len(b_nums))
        for i in range(num_fields):
            if   int(a_nums[i]) > int(b_nums[i]):
                return True
            elif int(a_nums[i]) < int(b_nums[i]):
                return False
        return True

    biggest = None
    versions = [ v.rstrip(os.path.sep) for v in versions ]

    for version in versions:
        if ((biggest is None or version == bigger_version(biggest, version)) and \
            not version_greater_or_equal_to_max(version, max_version)):
            biggest = version
    return biggest
