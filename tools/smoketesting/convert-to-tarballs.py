#!/usr/bin/env python2

# Copyright (c) 2005-2008, Elijah Newren
# Copyright (c) 2007-2009, Olav Vitters
# Copyright (c) 2006-2009, Vincent Untz
# Copyright (c) 2017, Codethink Limited
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

from __future__ import print_function

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
import requests
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

try:
    from ruamel import yaml
except ImportError:
    print("Converting to BuildStream requires the ruamel.yaml library.")
    sys.exit(1)

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
        return self.real_name.get(modulename, modulename)

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
    def __init__(self, tarballdir, mirrors, local_only=False):
        self.tarballdir = tarballdir
        self.have_sftp = self._test_sftp()
        self.get_stats = False
        self.local_only = local_only
        if hasattr(hashlib, 'sha256'):
            self.hash_algo = 'sha256'
        else:
            raise Exception("sha256 hashing required")
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
            if not hostname in self.sftp_hosts: raise KeyError('unknown hostname')
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
        biggest = None
        versions = [ v.rstrip(os.path.sep) for v in versions ]

        for version in versions:
            if ((biggest is None or version == self._bigger_version(biggest, version)) and \
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
                print("Downloading", filename, newfile)
                # one of those options will make Curl resume an existing download
                # speed-limit ensures 1KB/s over 30sec average (in case of connection problems)
                cmd = ['curl', '-C', '-', '-#kRfL', '--speed-limit', '1024', '--disable-epsv',  location, '-o', newfile]
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
        return hash, str(size)

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
        good_dir = re.compile('^([0-9]+\.)*[0-9]+/?$')
        def hasdirs(x): return good_dir.search(x)
        def fixdirs(x): return re.sub(r'^([0-9]+\.[0-9]+)/?$', r'\1', x)
        location = urlparse.urlunparse(parsed_url)
        # Follow 302 codes when retrieving URLs, speeds up conversion by 60sec
        redirect_location = location
        while True:
            # Get the files
            req = requests.get(redirect_location)
            if req.status_code != requests.codes.ok:
                files = None
                break
            parser = urllister()
            parser.feed(req.content)
            parser.close()
            files = parser.urls

            # Check to see if we need to descend to a subdirectory
            newdirs = filter(hasdirs, files)
            newdirs = map(fixdirs, newdirs)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                redirect_location = posixjoin(req.url, newdir, "")
                location = posixjoin(location, newdir, "")
            else:
                break
        return location, files

    _get_files_from_https = _get_files_from_http

    def find_tarball(self, baselocation, modulename, max_version):
        print("LOOKING for " + modulename + " tarball at " + baselocation)
        u = urlparse.urlparse(baselocation)

        mirror = self.mirrors.get((u.scheme, u.hostname), None)
        if mirror:
            baselocation = baselocation.replace(mirror[0], mirror[1], 1)
            u = urlparse.urlparse(baselocation)

        if u.scheme != 'file' and self.local_only:
            return None, '', None, None

        # Determine which function handles the actual retrieving
        locator = getattr(self, '_get_files_from_%s' % u.scheme, None)
        if locator is None:
            sys.stderr.write('Invalid location for ' + modulename + ': ' +
                             baselocation + '\n')
            sys.exit(1)

        location, files = locator(u, max_version)
        files = files or []
        
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
            hash = None
            size = None
        return location, version, hash, size


class ConvertToTarballs:
    def __init__(self, options, locator, directory, convert=True):
        self.options = options
        self.locator = locator
        self.convert = convert

        self.all_tarballs = []
        self.all_versions = []

        self.ignored_tarballs = []

        with open(os.path.join(directory, 'project.conf')) as f:
            projectconf = yaml.load(f)
            self.aliases = projectconf['aliases']

    def find_tarball_by_name(self, name):
        translated_name = self.options.translate_name(name)

        real_name = self.options.get_real_name(translated_name)
        max_version = self.options.get_version_limit(translated_name)
        baselocation = self.options.get_download_site('gnome.org', real_name)

        # Ask the locator to hunt down a tarball
        location, version, hash, size = self.locator.find_tarball(baselocation, real_name, max_version)
        # Save the versions
        self.all_tarballs.append(translated_name)
        self.all_versions.append(version)

        return location, version, hash, size

    def write_bst_file(self, fullpath, element, location):
        # Replace the first source with a tarball
        element['sources'][0]['kind'] = 'tar'
        element['sources'][0]['url'] = location

        if 'submodules' in element['sources'][0]:
            del element['sources'][0]['submodules']

        # we may not have track if we are updating for a stable release
        if 'track' in element['sources'][0]:
            del element['sources'][0]['track']

        # special case rsvg for now, this will hopefully go away
        # once we switch to bst 1.4
        if fullpath.endswith('librsvg.bst'):
            # keep only the tarball
            element['sources'] = [element['sources'][0]]

        # Dump it now
        with open(fullpath, 'w') as f:
            yaml.round_trip_dump(element, f)

    def process_one_file(self, dirname, basename):
        module_name = re.sub('\.bst$', '', basename)
        fullpath = os.path.join(dirname, basename)

        element = None
        with open(fullpath) as f:
            try:
                element = yaml.load(f, yaml.loader.RoundTripLoader)
            except (yaml.scanner.ScannerError, yaml.composer.ComposerError, yaml.parser.ParserError) as e:
                raise Exception("Malformed YAML:\n\n{}\n\n{}\n".format(e.problem, e.problem_mark))

        if element.get('kind', None) == 'stack':
            print("IGNORE stack element {}".format(basename))
            return

        sources = element.get('sources', [])
        if not sources:
            print("IGNORE element without sources {}".format(basename))
            return

        kind = sources[0].get('kind', None)
        if kind == 'local':
            print("IGNORE element with only local sources {}".format(basename))
            return

        if not self.convert and kind == 'git':
            print("IGNORE git element {} (not converting)".format(basename))
            return

        try:
            print("REWRITE {}".format(basename))
            location, version, hash, size = self.find_tarball_by_name(module_name)

            for alias, url in self.aliases.items():
                if location.startswith(url):
                    location = alias + ':' + location[len(url):]

            self.write_bst_file(fullpath, element, location)

        except IOError:
            if kind == 'tar' or kind == 'zip':
                print('IGNORE: Could not find site for ' + module_name)
                self.ignored_tarballs.append(module_name)
            else:
                print('FATAL: Could not find site for ' + module_name)
                sys.exit(1)

    def process_bst_files(self, directory):
        for root, dirs, files in os.walk(directory):
            for name in files:
                if name.endswith(".bst"):
                    self.process_one_file(root, name)

    def create_versions_file(self):
        print('**************************************************')
        versions = open('versions', 'w')
        done = {}
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
                            triplet = '%s:%s:%s:\n' % (release_set, real_module, version)
                            if not triplet in done:
                                versions.write(triplet)
                                done[triplet] = True
                    except:
                        print('FATAL: module %s missing from BuildStream projects' % module)
                        os.remove('versions')
                        sys.exit(1)
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


def main(args):
    program_dir = os.path.abspath(sys.path[0] or os.curdir)

    parser = optparse.OptionParser()
    parser.add_option("-t", "--tarballdir", dest="tarballdir",
                      help="location of tarballs", metavar="DIR")
    parser.add_option("-d", "--directory", dest="directory",
                      help="buildstream project directory", metavar="DIR")
    parser.add_option("-v", "--version", dest="version",
                      help="GNOME version to build")
    parser.add_option("-f", "--force", action="store_true", dest="force",
                      default=False, help="overwrite existing versions file")
    parser.add_option("-c", "--config", dest="config",
                      help="tarball-conversion config file", metavar="FILE")
    parser.add_option("-l", "--local-only", action="store_true", dest="local_only",
                      default=False, help="only look for files on a local file system")
    parser.add_option("", "--no-convert", action="store_false", dest="convert",
                      default=True, help="do not convert, only try to update elements that already use tarballs")
    (options, args) = parser.parse_args()

    if not options.version:
        parser.print_help()
        sys.exit(1)

    if not options.tarballdir:
        tarballdir = os.path.join(os.getcwd(), 'tarballs')
        try:
            os.mkdir(tarballdir)
        except OSError:
            pass
        options.tarballdir = tarballdir

    splitted_version = options.version.split(".")
    if (len(splitted_version) != 3):
        sys.stderr.write("ERROR: Version number is not valid\n")
        sys.exit(1)

    if options.config:
        try:
            config = Options(os.path.join(program_dir, options.config))
        except IOError:
            try:
                config = Options(options.config)
            except IOError:
                sys.stderr.write("ERROR: Config file could not be loaded from file: {}\n".format(options.config))
                sys.exit(1)
    else:
        is_stable = (int(splitted_version[1]) % 2 == 0)
        if is_stable:
            config = Options(os.path.join(program_dir, 'tarball-conversion-stable.config'))
        else:
            config = Options(os.path.join(program_dir, 'tarball-conversion.config'))

    if os.path.isfile('versions'):
        if options.force:
            os.unlink('versions')
        else:
            sys.stderr.write('Cannot proceed; would overwrite versions\n')
            sys.exit(1)

    if not options.directory:
        sys.stderr.write('Must specify the directory of the GNOME buildstream project to convert\n\n')
        parser.print_help()
        sys.exit(1)

    locator = TarballLocator(options.tarballdir, config.mirrors, options.local_only)
    convert = ConvertToTarballs(config, locator, options.directory, options.convert)
    convert.process_bst_files(os.path.join(options.directory, 'elements', 'core-deps'))
    convert.process_bst_files(os.path.join(options.directory, 'elements', 'core'))
    convert.process_bst_files(os.path.join(options.directory, 'elements', 'sdk'))

    if options.convert:
        convert.create_versions_file()

    if convert.ignored_tarballs:
        print("Could not find a download site for the following modules:")
        for module_name in convert.ignored_tarballs:
            print("- {}".format(module_name))

if __name__ == '__main__':
    try:
      main(sys.argv)
    except KeyboardInterrupt:
      pass
