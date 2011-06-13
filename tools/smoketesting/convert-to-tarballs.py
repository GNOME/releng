#!/usr/bin/python

# Copyright (c) 2005-2008, Elijah Newren
# Copyright (c) 2007-2009, Olav Vitters
# Copyright (c) 2006-2009, Vincent Untz
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

# Example of running:
#   $ ./convert-to-tarballs.py -t ~/src/tarball-gnome2/pkgs -v 2.11.91 \
#       ~/src/jhbuild/modulesets/gnome-2.12.modules
#   $ jhbuild -m `pwd`/gnome-2.11.91.modules build meta-gnome-desktop
#
# Explanation:
#   The first command reads ~/cvs/gnome/jhbuild/modulesets/gnome-2.12.modules
#   and creates:
#     ./gnome-2.11.91.modules
#     ./freedesktop-2.11.91.modules (pulled in by gnome-2.12.modules include)
#     ./versions (needs some hand editing first, though)
#     ~/cvs/tarball-gnome2/pkgs/<lots of tarballs>
#   The gnome-2.11.91.modules file should be useable for building with jhbuild;
#   the versions file should be useful for making a gnome release with the
#   release scripts in releng/tools/release_set_scripts
#
# Other useful files:
#   tarball-conversion.config (used to know how to do conversion)
#   sample-tarball.jhbuildrc  (you may not want to use your normal .jhbuildrc
#                              when building this tarball version of gnome)

# GOTCHAS:
#   - tarball-conversion.config may need to be updated over time
#   - the .modules files and version files aren't perfect and may
#     require some hand editing (seems to be minimial, though)
#   - tarball md5sums and sizes depend on correct downloading with
#     wget (I got a 0 size for mozilla once); easy to fix, though.
#   - this script can pick up too recent tarballs
#     (e.g. gstreamer-0.9.1 instead of 0.8.10) without warning; will
#     be fixed later, but can be detected by searching for 'revision'
#     in the .modules files.

# Examples of hand editing needed for 2.11.91:
# Manual editing of gnome-2.11.91.modules:
#   - remove pyorbit as gnome-python dependency
#   - fixed an incorrectly downloaded mozilla tarball md5sum & size (it
#     somehow got downloaded as an empty file)
#   - remove "--" from autogenargs for gstreamer and gst-plugins;
#     configure fails with it
#   - must manually downgrade gstreamer tarball to 0.8.10 as 0.9.1 isn't
#     meant for gnome-2.12; this should be considered a bug in my script,
#     but can be found by searching for "revision" in the .modules file
# Manual editing of versions:
#   - Add pkg-config


import sys, string
import re
import optparse
import os
import os.path
from posixpath import join as posixjoin # Handy for URLs
import signal
import subprocess
from ftplib import FTP
from xml.dom import minidom, Node
from sgmllib import SGMLParser
import urllib2
import urlparse
if not hasattr(__builtins__, 'set'):
    from sets import Set as set
import time
import socket
try:
    import hashlib
except ImportError:
    import md5 as hashlib
try: import psyco
except: pass

have_sftp = False
try:
    import paramiko

    have_sftp = True
except: pass

# Some TODOs
#   - Check timestamps on ftp tarballs, rejecting as 'too old' the ones that
#     were released too late
#   ? Make a useful help message

# TODOs for elsewhere
#   - Add times
#     (15 min for convert-to-tarballs, 15 minutes for fixing up output
#      files, 4.5 hours for build, 15 minutes to test (if development
#      version), 15 minutes to sanity check, 15 minutes to run relevant
#      release scripts, plus 15 minutes slush time or so -- total: 6
#      hours)

# Extra stuff to document (for myself or elsewhere)
#   - don't forget to mount of /usr/local on amr
#   - mention removing lines from $prefix/share/jhbuild/packagedb.xml

class Options:
    def __init__(self, filename):
        self.filename = filename
        self.mirrors = {}
        self.rename = {}
        self.drop_prefix = []
        self.release_sets = []
        self.release_set = []
        self.subdir = {}
        self.version_limit = {}
        self.real_name = {}
        self.cvs_locations = []
        self.module_locations = []
        self._read_conversion_info()

    def translate_name(self, modulename):
        # First, do the renames in the dictionary
        newname = self.rename.get(modulename, modulename)

        # Second, drop any given prefixes
        for drop in self.drop_prefix:
            newname = re.sub(r'^' + drop + '(.*)$', r'\1', newname)

        return newname

    def module_included(self, modulename):
        index = None
        realname = self.translate_name(modulename)
        for idx in range(len(self.release_sets)):
            try:
                index = self.release_set[idx].index(realname)
            except:
                index = None
            if index is not None:
                return True
        return False

    def get_base_site(self, cvssite, modulename):
        for list in self.module_locations:
            if list[0] == modulename:
                return list[1]
        for list in self.cvs_locations:
            if re.search(list[0] + '$', cvssite):
                return list[1]
        raise IOError('No download site found!\n')

    def get_download_site(self, cvssite, modulename):
        for list in self.module_locations:
            if list[0] == modulename:
                subdir = ''
                if len(list) == 3:
                    subdir = re.sub(r'\$module', modulename, list[2])
                return posixjoin(list[1], subdir)
        for list in self.cvs_locations:
            if re.search(list[0] + '$', cvssite):
                subdir = ''
                if len(list) == 3:
                    subdir = re.sub(r'\$module', modulename, list[2])
                return posixjoin(list[1], subdir)
        raise IOError('No download site found!\n')

    def _get_locations(self, locations_node):
        for node in locations_node.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'site':
                location = node.attributes.get('location').nodeValue
                if node.attributes.get('cvs') is not None:
                    cvs = node.attributes.get('cvs').nodeValue
                    subdir = node.attributes.get('subdir').nodeValue
                    self.cvs_locations.append([cvs, location, subdir])
                elif node.attributes.get('module') is not None:
                    module = node.attributes.get('module').nodeValue
                    if node.attributes.get('subdir'):
                        dir = node.attributes.get('subdir').nodeValue
                        self.module_locations.append([module, location, dir])
                    else:
                        self.module_locations.append([module, location])
            else:
                sys.stderr.write('Bad location node\n')
                sys.exit(1)

    def _get_mirrors(self, mirrors_node):
        for node in mirrors_node.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'mirror':
                old = node.attributes.get('location').nodeValue
                new = node.attributes.get('alternate').nodeValue
                if new.startswith('file://'):
                    if not node.attributes.get('host') or node.attributes.get('host').nodeValue != socket.getfqdn():
                        continue
                u = urlparse.urlparse(old)
                # Only add the mirror if we don't have one or if it's a local
                # mirror (in which case we replace what we had before)
                if not self.mirrors.has_key((u.scheme, u.hostname)) or u.scheme == 'file':
                    self.mirrors[(u.scheme, u.hostname)] = (old, new)
            else:
                sys.stderr.write('Bad mirror node\n')
                sys.exit(1)

    def _get_renames(self, renames_node):
        for node in renames_node.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'name':
                old = node.attributes.get('old').nodeValue
                new = node.attributes.get('new').nodeValue
                self.rename[old] = new
            elif node.nodeName == 'drop':
                prefix = node.attributes.get('prefix').nodeValue
                self.drop_prefix.append(prefix)
            else:
                sys.stderr.write('Bad rename node\n')
                sys.exit(1)

    def _get_modulelist(self, modulelist_node):
        for node in modulelist_node.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'package':
                name = node.attributes.get('name').nodeValue

                # Determine whether we have a version limit for this package
                if node.attributes.get('limit'):
                    max_version = node.attributes.get('limit').nodeValue
                    if re.match(r'[0-9]+\.[0-9]+\.[0-9]+', max_version):
                        sys.stderr.write('Bad limit for ' + name + ': ' + \
                          max_version + '. x.y.z versions not allowed; drop z\n')
                        sys.exit(1)
                    self.version_limit[name] = max_version

                if node.attributes.get('module'):
                    self.real_name[name] = node.attributes.get('module').nodeValue

                # Determine if we have a specified subdir for this package
                if node.attributes.get('subdir'):
                    self.subdir[name] = node.attributes.get('subdir').nodeValue
                else:
                    self.subdir[name] = ''

                # Find the appropriate release set
                if node.attributes.get('set'):
                    release_set = node.attributes.get('set').nodeValue
                else:
                    release_set = 'Other'

                # Add it to the lists
                try:
                    index = self.release_sets.index(release_set)
                except:
                    index = None
                if index is not None:
                    self.release_set[index].append(name)
                else:
                    self.release_sets.append(release_set)
                    self.release_set.append([ name ])
            else:
                sys.stderr.write('Bad whitelist node\n')
                sys.exit(1)

    def get_version_limit(self, modulename):
        # First, do the renames in the dictionary
        return self.version_limit.get(modulename, None)

    def get_real_name(self, modulename):
        # First, do the renames in the dictionary
        return  self.real_name.get(modulename, modulename)

    def get_subdir(self, modulename):
        # First, do the renames in the dictionary
        return self.subdir.get(modulename, None)

    def _read_conversion_info(self):
        document = minidom.parse(self.filename)
        conversion_stuff = document.documentElement
        for node in conversion_stuff.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'locations':
                self._get_locations(node)
            elif node.nodeName == 'mirrors':
                self._get_mirrors(node)
            elif node.nodeName == 'rename':
                self._get_renames(node)
            elif node.nodeName == 'whitelist':
                self._get_modulelist(node)
            else:
                sys.stderr.write('Unexpected conversion type: ' +
                                 node.nodeName + '\n')
                sys.exit(1)

class urllister(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.urls = []

    def start_a(self, attrs):
        href = [v for k, v in attrs if k=='href']
        if href:
            self.urls.extend(href)

class TarballLocator:
    def __init__(self, tarballdir, mirrors, determine_stats=True, local_only=False):
        self.tarballdir = tarballdir
        self.urlopen = urllib2.build_opener()
        self.have_sftp = self._test_sftp()
        self.get_stats = determine_stats
        self.local_only = local_only
        if hasattr(hashlib, 'sha256'):
            self.hash_algo = 'sha256'
        else:
            self.hash_algo = 'md5'
        self.cache = {}
        for key in mirrors.keys():
            mirror = mirrors[key]
            if mirror[1].startswith('sftp://'):
                hostname = urlparse.urlparse(mirror[1]).hostname
                if not self.have_sftp or not self._test_sftp_host(hostname):
                    sys.stderr.write("WARNING: Removing sftp mirror %s due to non-working sftp setup\n" % mirror[1])
                    del(mirrors[key])
        self.mirrors = mirrors
        if not os.path.exists(tarballdir):
            os.mkdir(tarballdir)

    def cleanup(self):
        """Clean connection cache, close any connections"""
        if 'ftp' in self.cache:
            for connection in self.cache['ftp'].itervalues():
                connection.quit()
        if 'sftp' in self.cache:
            for connection in self.cache['sftp'].itervalues():
                connection.sock.get_transport().close()

    def _test_sftp(self):
        """Perform a best effort guess to determine if sftp is available"""
        global have_sftp
        if not have_sftp: return False

        try:
            self.sftp_cfg = paramiko.SSHConfig()
            self.sftp_cfg.parse(file(os.path.expanduser('~/.ssh/config'), 'r'))

            self.sftp_keys = paramiko.Agent().get_keys()
            if not len(self.sftp_keys): raise KeyError('no sftp_keys')

            self.sftp_hosts = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        except:
            have_sftp = False

        return have_sftp

    def _test_sftp_host(self, hostname):
        do_sftp = True
        try:
            cfg = self.sftp_cfg.lookup(hostname)
            cfg.get('user') # require a username to be defined
            if not self.sftp_hosts.has_key(hostname): raise KeyError('unknown hostname')
        except KeyError:
            do_sftp = False

        return do_sftp

    def _bigger_version(self, a, b):
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
    def _version_greater_or_equal_to_max(self, a, max_version):
        if not max_version:
            return False
        a_nums = a.split('.')
        b_nums = max_version.split('.')
        num_fields = min(len(a_nums), len(b_nums))
        for i in range(0,num_fields):
            if   int(a_nums[i]) > int(b_nums[i]):
                return True
            elif int(a_nums[i]) < int(b_nums[i]):
                return False
        return True

    def _get_latest_version(self, versions, max_version):
        biggest = versions[0]
        for version in versions[1:]:
            if (version == self._bigger_version(biggest, version) and \
                not self._version_greater_or_equal_to_max(version, max_version)):
                biggest = version
        return biggest

    def _get_tarball_stats(self, location, filename):
        def default_sigpipe():
            "restore default signal handler (http://bugs.python.org/issue1652)"
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        MAX_TRIES = 10
        newfile = os.path.join(self.tarballdir, filename)
        hashfile = newfile + '.' + self.hash_algo + 'sum'
        if newfile.endswith('gz'):
            flags = 'xfzO'
        elif newfile.endswith('xz'):
            flags = 'xfJO'
        else:
            flags = 'xfjO'

        tries = MAX_TRIES
        while tries:
            if tries < MAX_TRIES:
                sys.stderr.write('Trying again\n')
                time.sleep(12)

            if not os.path.exists(newfile) or tries != MAX_TRIES:
                print "Downloading", filename, newfile
                # one of those options will make Curl resume an existing download
                cmd = ['curl', '-C', '-', '-#kRfL', '--disable-epsv',  location, '-o', newfile]
                retcode = subprocess.call(cmd)
                if retcode != 0:
                    # Curl gives an error when an existing file cannot be continued
                    # in which case the existing file is likely corrupt somehow
                    try: os.unlink(newfile)
                    except OSError: pass

                    sys.stderr.write('Couldn\'t download ' + filename + '!\n')
                    tries -= 1
                    continue

                if os.path.exists(hashfile):
                    os.unlink(hashfile)

            if not os.path.exists(hashfile):
                time.sleep(1)
                cmd = ['tar', flags, newfile]
                devnull = file('/dev/null', 'wb')
                retcode = subprocess.call(cmd, stdout=devnull, preexec_fn=default_sigpipe)
                devnull.close()
                if retcode:
                    sys.stderr.write('Integrity check for ' + filename + ' failed!\n')
                    tries -= 1
                    continue

            break
        else:
            sys.stderr.write('Too many tries. Aborting this attempt\n')
            return '', ''

        size = os.stat(newfile)[6]
        if not os.path.exists(hashfile):
            sum = getattr(hashlib, self.hash_algo)()
            fp = open(newfile, 'rb')
            data = fp.read(32768)
            while data:
                sum.update(data)
                data = fp.read(32768)
            fp.close()
            hash = sum.hexdigest()
            file(hashfile, 'w').write(hash)
        else:
            hash = file(hashfile).read()
        return '%s:%s' % (self.hash_algo, hash), str(size)

    def _get_files_from_ftp(self, parsed_url, max_version):
        ftp = FTP(parsed_url.hostname)
        ftp.login(parsed_url.username or 'anonymous', parsed_url.password or '')
        ftp.cwd(parsed_url.path)
        path = parsed_url.path
        good_dir = re.compile('^([0-9]+\.)*[0-9]+$')
        def hasdirs(x): return good_dir.search(x)
        while True:
            files = ftp.nlst()
            newdirs = filter(hasdirs, files)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                path = posixjoin(path, newdir)
                ftp.cwd(newdir)
            else:
                break
        ftp.quit()

        newloc = list(parsed_url)
        newloc[2] = path
        location = urlparse.urlunparse(newloc)
        return location, files

    def _get_files_from_file(self, parsed_url, max_version):
        files = []
        path = parsed_url.path
        good_dir = re.compile('^([0-9]+\.)*[0-9]+$')
        def hasdirs(x): return good_dir.search(x)
        while True:
            try:
                files = os.listdir(path)
            except OSError:
                break

            newdirs = filter(hasdirs, files)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                path = posixjoin(path, newdir)
            else:
                break

        newloc = list(parsed_url)
        newloc[2] = path
        location = urlparse.urlunparse(newloc)
        return location, files

    def _get_files_from_sftp(self, parsed_url, max_version):
        hostname = parsed_url.hostname

        if hostname in self.cache.setdefault('sftp', {}):
            sftp = self.cache['sftp'][hostname]
        else:
            hostkeytype = self.sftp_hosts[hostname].keys()[0]
            hostkey = self.sftp_hosts[hostname][hostkeytype]
            cfg = self.sftp_cfg.lookup(hostname)
            hostname = cfg.get('hostname', hostname).replace('%h', hostname)
            port = parsed_url.port or cfg.get('port', 22)
            username = parsed_url.username or cfg.get('user')

            t = paramiko.Transport((hostname, port))
            t.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            t.connect(hostkey=hostkey)

            for key in self.sftp_keys:
                try:
                    t.auth_publickey(username, key)
                    break
                except paramiko.SSHException:
                    pass

            if not t.is_authenticated():
                t.close()
                sys.stderr('ERROR: Cannot authenticate to %s' % hostname)
                sys.exit(1)

            sftp = paramiko.SFTPClient.from_transport(t)
            self.cache['sftp'][hostname] = sftp

        path = parsed_url.path
        good_dir = re.compile('^([0-9]+\.)*[0-9]+$')
        def hasdirs(x): return good_dir.search(x)
        while True:
            files = sftp.listdir(path)

            newdirs = filter(hasdirs, files)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                path = posixjoin(path, newdir)
            else:
                break

        newloc = list(parsed_url)
        newloc[2] = path
        location = urlparse.urlunparse(newloc)
        return location, files

    def _get_files_from_http(self, parsed_url, max_version):
        obj = self.urlopen
        good_dir = re.compile('^([0-9]+\.)*[0-9]+/?$')
        def hasdirs(x): return good_dir.search(x)
        def fixdirs(x): return re.sub(r'^([0-9]+\.[0-9]+)/?$', r'\1', x)
        location = urlparse.urlunparse(parsed_url)
        # Follow 302 codes when retrieving URLs, speeds up conversion by 60sec
        redirect_location = location
        while True:
            # Get the files
            usock = obj.open(redirect_location)
            parser = urllister()
            parser.feed(usock.read())
            usock.close()
            parser.close()
            files = parser.urls

            # Check to see if we need to descend to a subdirectory
            newdirs = filter(hasdirs, files)
            newdirs = map(fixdirs, newdirs)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                redirect_location = posixjoin(usock.url, newdir)
                location = posixjoin(location, newdir)
            else:
                break
        return location, files

    def find_tarball(self, baselocation, modulename, max_version):
        print "LOOKING for " + modulename + " tarball at " + baselocation
        u = urlparse.urlparse(baselocation)

        mirror = self.mirrors.get((u.scheme, u.hostname), None)
        if mirror:
            baselocation = baselocation.replace(mirror[0], mirror[1], 1)
            u = urlparse.urlparse(baselocation)

        if u.scheme != 'file' and self.local_only:
            return 'http://somewhere.in.france/', '', 'blablablaihavenorealclue', 'HUGE'

        # Determine which function handles the actual retrieving
        locator = getattr(self, '_get_files_from_%s' % u.scheme, None)
        if locator is None:
            sys.stderr.write('Invalid location for ' + modulename + ': ' +
                             baselocation + '\n')
            sys.exit(1)

        location, files = locator(u, max_version)

        basenames = set()
        tarballs = []
        if location.find("ftp.debian.org") != -1:
            extensions = [
                '.tar.xz',
                '.tar.bz2',
                '.tar.gz',
            ]
        else:
            extensions = [
                '.tar.xz',
                'orig.tar.bz2',
                '.tar.bz2',
                'orig.tar.gz',
                '.tar.gz',
            ]


        # Has to be checked by extension first; we prefer .tar.xz over .tar.bz2 and .tar.gz
        for ext in extensions:
            for file in files:
                basename = file[:-len(ext)] # only valid when file ends with ext
                if file.endswith(ext) and basename not in basenames:
                    basenames.add(basename)
                    tarballs.append(file)

        # Only include tarballs for the given module
        tarballs = [tarball for tarball in tarballs if modulename in tarball]

        re_tarball = r'^'+re.escape(modulename)+'[_-](([0-9]+[\.\-])*[0-9]+)(\.orig)?\.tar.*$'
        ## Don't include -beta -installer -stub-installer and all kinds of
        ## other stupid inane tarballs, and also filter tarballs that have a
        ## name that includes the module name but is different (eg, Gnome2-VFS
        ## instead of Gnome2)
        tarballs = filter(lambda t: re.search(re_tarball, t), tarballs)

        versions = map(lambda t: re.sub(re_tarball, r'\1', t), tarballs)

        if not len(versions):
            raise IOError('No versions found')
        version = self._get_latest_version(versions, max_version)
        index = versions.index(version)

        location = posixjoin(location, tarballs[index])
        if mirror: # XXX - doesn't undo everything -- not needed
            location = location.replace(mirror[1], mirror[0], 1)

        # Only get tarball stats if we're not in a hurry
        if self.get_stats:
            hash, size = self._get_tarball_stats(location, tarballs[index])
        else:
            hash = 'md5:blablablaihavenorealclue'
            size = 'HUGE'
        return location, version, hash, size

class ConvertToTarballs:
    def __init__(self, tarballdir, version, sourcedir, options, force, versions_only, local_only):
        self.tarballdir = tarballdir
        self.version = version
        self.sourcedir = sourcedir
        self.options = options
        self.force = force
        self.versions_only = versions_only
        self.ignored = []
        self.not_found = []
        self.all_tarballs = []
        self.all_versions = []
        self.no_max_version = []
        self.locator = TarballLocator(tarballdir, options.mirrors, not versions_only, local_only)
        self.known_repositories = []
        self.known_repositories_nodes = []

    def _create_tarball_repo_node(self, document, href):
        repo = document.createElement('repository')
        self.known_repositories_nodes.append({'href': href, 'name': href, 'type': 'tarball'})

    def _create_tarball_node(self, document, node):
        assert node.nodeName != 'tarball'
        tarball = document.createElement(node.nodeName)
        attrs = node.attributes
        cvsroot = None
        for attrName in attrs.keys():
            if attrName == 'cvsroot':
                cvsroot = attrs.get(attrName).nodeValue
                continue
            if attrName == 'id':
                id = attrs.get(attrName).nodeValue
                if not self.options.module_included(id):
                    self.ignored.append(id)
                    return None
            if attrName == 'checkoutdir':
                # Must trim these or jhbuild complains when the directory is
                # named libxml2-2.6.22 instead of libxml2...
                continue
            attrNode = attrs.get(attrName)
            attrValue = attrNode.nodeValue
            tarball.setAttribute(attrName, attrValue)

        branch_node = document.createElement('branch')
        tarball.appendChild(branch_node)

        if cvsroot == None:  # gnome cvs
            cvsroot = 'gnome.org'

        max_version = None
        revision = None
        for subnode in node.getElementsByTagName('branch'):
            # see if it has a 'version' attribute
            attrs = subnode.attributes
            if attrs.get('revision') != None:
                revision = attrs.get('revision').nodeValue
        try:
            name = self.options.translate_name(id)
            real_name = self.options.get_real_name(name)
            repo = self.options.get_base_site(cvsroot, real_name)
            if not repo in self.known_repositories:
                self._create_tarball_repo_node(document, repo)
                self.known_repositories.append(repo)
            baselocation = self.options.get_download_site(cvsroot, real_name)
            max_version = self.options.get_version_limit(name)
            location, version, hash, size = \
                      self.locator.find_tarball(baselocation, real_name, max_version)
            print '  ', location, version, hash, size
            branch_node.setAttribute('version', version)
            branch_node.setAttribute('repo', repo)
            branch_node.setAttribute('module', location[len(repo):])
            branch_node.setAttribute('size', size)
            branch_node.setAttribute('hash', hash)
            self.all_tarballs.append(name)
            self.all_versions.append(version)
        except IOError:
            print '**************************************************'
            print 'Could not find site for ' + id
            print '**************************************************'
            print ''
            if not id in self.not_found:
                self.not_found.append(id)
            branch_node.setAttribute('version', 'EAT-YOUR-BRAAAAAANE')
            branch_node.setAttribute('repo', 'http://somewhere.over.the.rainbow/')
            branch_node.setAttribute('module', 'where/bluebirds/die')
            branch_node.setAttribute('size', 'HUGE')
            branch_node.setAttribute('hash', 'md5:blablablaihavenorealclue')
        if revision and not max_version:
            self.no_max_version.append(id)
        return tarball

    def _walk(self, oldRoot, newRoot, document):
        for node in oldRoot.childNodes:
            if node.nodeType == Node.ELEMENT_NODE:
                save_entry_as_is = False
                if node.nodeName == 'perl':
                    continue
                elif node.nodeName == 'repository':
                    # We are interested in tarball repositories but not
                    # cvs/svn/git/arch/bzr/scm-du-jour repositories
                    attrs = node.attributes
                    type = attrs.get('type').nodeValue
                    if type == 'tarball':
                        save_entry_as_is = True
                    else:
                        continue
                elif node.nodeName == 'distutils' or \
                     node.nodeName == 'waf' or \
                     node.nodeName == 'cmake' or \
                     node.nodeName == 'autotools':
                    # Distutils and autotools modules are kind of
                    # complicated; they may be a tarball or a source code
                    # repo like cvs; first, assume it'll be a tarball and
                    # try to get name and version
                    attrs = node.attributes
                    name    = attrs.get('id').nodeValue
                    version = None

                    # Now, try to find the 'branch' childNode
                    for subnode in node.getElementsByTagName('branch'):
                        # We're working with the 'branch' childNode;
                        # see if it has a 'version' attribute
                        attrs = subnode.attributes
                        if attrs.get('version') != None:
                            version = attrs.get('version').nodeValue

                    # If we found a version, treat it like a tarball
                    if version != None:
                        self.all_tarballs.append(name)
                        self.all_versions.append(version)
                        save_entry_as_is = True
                    else:
                        # Otherwise, treat it like a source code repository
                        entry = self._create_tarball_node(document, node)

                elif node.nodeName == 'mozillamodule':
                    entry = self._create_tarball_node(document, node)
                elif node.nodeName == 'tarball':
                    attrs = node.attributes
                    name    = attrs.get('id').nodeValue
                    version = attrs.get('version').nodeValue
                    self.all_tarballs.append(name)
                    self.all_versions.append(version)
                    save_entry_as_is = True
                elif node.nodeName == 'include':
                    location = node.attributes.get('href').nodeValue
                    newname = self.fix_file(location)
                    # Write out the element name.
                    entry = document.createElement(node.nodeName)
                    # Write out the attributes.
                    attrs = node.attributes
                    for attrName in attrs.keys():
                        if attrName == 'href':
                            entry.setAttribute(attrName, newname)
                        else:
                            attrValue = attrs.get(attrName).nodeValue
                            entry.setAttribute(attrName, attrValue)
                else:
                    save_entry_as_is = True
                    if node.nodeName == 'branch':
                        if len(node.attributes.keys()) == 0:
                            continue

                if save_entry_as_is:
                    # Write out the element name.
                    entry = document.createElement(node.nodeName)
                    # Write out the attributes.
                    attrs = node.attributes
                    for attrName in attrs.keys():
                        attrNode = attrs.get(attrName)
                        attrValue = attrNode.nodeValue
                        entry.setAttribute(attrName, attrValue)
                if entry:   # entry can be None if we want to skip this tarball
                    # Walk the child nodes.
                    self._walk(node, entry, document)
                    # Append the new node to the newRoot
                    newRoot.appendChild(entry)

    def cleanup(self):
        self.locator.cleanup()

    def fix_file(self, input_filename):
        newname = re.sub(r'^([-a-z]+?)(?:-[0-9\.]*)?(.modules)$',
                         r'\1-' + self.version + r'\2',
                         input_filename)

        if not self.versions_only and os.path.isfile(newname):
            if self.force:
                os.unlink(newname)
            else:
                sys.stderr.write('Cannot proceed; would overwrite '+newname+'\n')
                sys.exit(1)
        if os.path.isfile('versions'):
            if self.force:
                os.unlink('versions')
            else:
                sys.stderr.write('Cannot proceed; would overwrite versions\n')
                sys.exit(1)

        old_document = minidom.parse(os.path.join(self.sourcedir, input_filename))
        oldRoot = old_document.documentElement

        new_document = minidom.Document()
        newRoot = new_document.createElement(oldRoot.nodeName)
        new_document.appendChild(newRoot)

        self._walk(oldRoot, newRoot, new_document)

        # modules converted to tarball nodes may need the definition of some
        # new repositories, add all of them to the moduleset.
        for repo_dict in self.known_repositories_nodes:
            repo = new_document.createElement('repository')
            for attr in repo_dict.keys():
                repo.setAttribute(attr, repo_dict.get(attr))
            newRoot.appendChild(repo)

        if not self.versions_only:
            newfile = file(newname, 'w+')
            new_document.writexml(newfile, "", "  ", '\n')

        old_document.unlink()
        new_document.unlink()

        return newname

    def get_unused_with_subdirs(self):
        full_whitelist = []
        for release_set in self.options.release_set:
            full_whitelist.extend(release_set)
        unique = set(full_whitelist) - set(self.all_tarballs)
        for module in unique:
          subdir = self.options.get_subdir(module)
          if subdir is None:
              pass
          try:
              name = self.options.translate_name(module)
              baselocation = self.options.get_download_site('gnome.org', name)
              max_version = self.options.get_version_limit(name)
              real_name = self.options.get_real_name(name)
              location, version, hash, size = \
                        self.locator.find_tarball(baselocation, real_name, max_version)
              print '  ', location, version, hash, size
              self.all_tarballs.append(name)
              self.all_versions.append(version)
          except IOError:
              print '**************************************************'
              print 'Could not find site for ' + module
              print '**************************************************'
              print ''
              if not module in self.not_found:
                  self.not_found.append(module)

    def show_ignored(self):
        if not len(self.ignored): return

        print '**************************************************'
        print 'The following modules were ignored: '
        print ' '.join(sorted(self.ignored))

    def show_unused_whitelist_modules(self):
        full_whitelist = []
        for release_set in self.options.release_set:
            full_whitelist.extend(release_set)
        unique = set(full_whitelist) - set(self.all_tarballs)

        if not len(unique): return

        print '**************************************************'
        print 'Unused whitelisted modules:'
        print ' '.join(sorted(unique))

    def show_not_found(self):
        if not len(self.not_found): return

        print '**************************************************'
        print 'Tarballs were not found for the following modules: '
        print ' '.join(sorted(self.not_found))

    def show_missing_max_versions(self):
        if not len(self.no_max_version): return

        print '**************************************************'
        print 'The following modules lack a max_version in the tarball-conversion file:'
        print ', '.join(sorted(self.no_max_version))

    def create_versions_file(self):
        print '**************************************************'
        versions = open('versions', 'w')
        for idx in range(len(self.options.release_sets)):
            release_set = self.options.release_sets[idx]
            if release_set != 'Other':
                versions.write('## %s\n' % string.upper(release_set))
                modules_sorted = self.options.release_set[idx]
                modules_sorted.sort()
                subdirs = {}
                for module in modules_sorted:
                    try:
                        real_module = self.options.get_real_name(module)
                        index = self.all_tarballs.index(module)
                        version = self.all_versions[index]
                        subdir = self.options.get_subdir(module)
                        if subdir != '':
                            if not subdirs.has_key(subdir):
                                subdirs[subdir] = []
                            subdirs[subdir].append ('%s:%s:%s:%s\n' %
                                     (release_set, real_module, version, subdir))
                        else:
                            versions.write('%s:%s:%s:\n' %
                                           (release_set, real_module, version))
                    except:
                        print 'No version found for %s' % module
                subdirs_keys = subdirs.keys()
                subdirs_keys.sort ()
                for subdir in subdirs_keys:
                    versions.write('\n')
                    versions.write('# %s\n' % subdir.title())
                    modules_sorted = subdirs[subdir]
                    modules_sorted.sort()
                    for module in modules_sorted:
                        versions.write(module)
                versions.write('\n')
        versions.close()

def get_path(filename, path):
    for dir in path:
        if os.path.isfile(os.path.join(dir, filename)):
            return dir
    return None

def main(args):
    program_dir = os.path.abspath(sys.path[0] or os.curdir)

    parser = optparse.OptionParser()
    parser.add_option("-t", "--tarballdir", dest="tarballdir",
                      help="location of tarballs", metavar="DIR")
    parser.add_option("-v", "--version", dest="version",
                      help="GNOME version to build")
    parser.add_option("-f", "--force", action="store_true", dest="force",
                      default=False, help="overwrite existing versions and *.modules files")
    parser.add_option("-c", "--config", dest="config",
                      help="tarball-conversion config file", metavar="FILE")
    parser.add_option("-o", "--versions-only", action="store_true", dest="versions_only",
                      default=False, help="only create a versions file, without downloading the tarballs")
    parser.add_option("-l", "--local-only", action="store_true", dest="local_only",
                      default=False, help="only look for files on a local file system")

    if os.path.exists(os.path.join(os.getcwd(), 'tarballs')):
        parser.set_defaults(tarballdir=os.path.join(os.getcwd(), 'tarballs'))

    (options, args) = parser.parse_args()

    if not options.version:
        parser.print_help()
        sys.exit(1)

    if options.versions_only and not options.tarballdir:
        options.tarballdir = os.getcwd()

    if not options.tarballdir:
        sys.stderr.write("ERROR: destination directory of tarballs is not defined\n")
        sys.exit(1)

    splitted_version = options.version.split(".")
    if (len(splitted_version) != 3):
        sys.stderr.write("ERROR: Version number is not valid\n")
        sys.exit(1)

    is_stable = (int(splitted_version[1]) % 2 == 0)
    if is_stable:
        conversion = Options(os.path.join(program_dir, 'tarball-conversion-stable.config'))
        jhbuildrc = os.path.join(program_dir, 'sample-tarball-stable.jhbuildrc')
    else:
        conversion = Options(os.path.join(program_dir, 'tarball-conversion.config'))
        jhbuildrc = os.path.join(program_dir, 'sample-tarball.jhbuildrc')
    if options.config:
        conversion = Options(os.path.join(program_dir, options.config))

    jhbuild_dir = get_path('jhbuild.in', (os.path.expanduser('~/src/jhbuild'), '/cvs/jhbuild'))

    moduleset = None
    if len(args):
        moduleset = args[-1]
    elif jhbuild_dir:
        # Determine file_location from jhbuild checkoutdir
        if is_stable:
            moduleset = os.path.join(jhbuild_dir, 'modulesets',
                                     'gnome-suites-%s.%s.modules' % (splitted_version[0],
                                                              splitted_version[1]))
        else:
            moduleset = os.path.join(jhbuild_dir, 'modulesets',
                                     'gnome-suites-%s.%s.modules' % (splitted_version[0],
                                                              str(int(splitted_version[1])+1)))

        # Make sure the jhbuild checkout directory is up to date
        retcode = subprocess.call(['git', 'pull', '--rebase'], cwd=jhbuild_dir)
        if retcode != 0:
            sys.stderr("WARNING: Error updating jhbuild checkout directory\n")

    if not moduleset or not os.path.exists(moduleset):
        sys.stderr.write("ERROR: No valid module file specified!\n")
        parser.print_help()
        sys.exit(1)
    file_location, filename = os.path.split(moduleset)

    if jhbuild_dir and not options.tarballdir:
        sys.path.insert(0, jhbuild_dir)
        import jhbuild.config
        jhbuild.config.Config.setup_env = lambda self: None
        jhbuild_opts = jhbuild.config.Config(jhbuildrc)
        options.tarballdir = jhbuild_opts.tarballdir

    convert = ConvertToTarballs(options.tarballdir, options.version, file_location, conversion, options.force, options.versions_only, options.local_only)
    try:
        convert.fix_file(filename)
        convert.get_unused_with_subdirs() #FIXME: this should probably be get_unused_bindings
        convert.show_ignored()
        convert.show_unused_whitelist_modules()
        convert.show_not_found()
        convert.show_missing_max_versions()
        convert.create_versions_file()
    finally:
        convert.cleanup()

if __name__ == '__main__':
    try:
      main(sys.argv)
    except KeyboardInterrupt:
      pass
