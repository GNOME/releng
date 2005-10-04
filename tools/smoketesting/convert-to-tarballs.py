#!/usr/bin/python

# Example of running:
#   $ ./convert-to-tarballs.py -t ~/cvs/tarball-gnome2/pkgs -v 2.11.91 \
#       ~/cvs/gnome/jhbuild/modulesets/gnome-2.12.modules
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
#   - Add java and perl bindings
#   - Add evolution-exchange
#   - Add pkg-config



## Stuff that I (Elijah) run while debugging and extending (ignore this):
# rm -f freedesktop-2.11.92.modules gnome-2.11.92.modules; ./convert-to-tarballs.py -v 2.11.92 ~/floss-development/gnome/jhbuild/modulesets/gnome-2.12.modules
# jhbuild -m `pwd`/gnome-2.11.92.modules list meta-gnome-desktop

import sys, string
import re
import getopt
import os
from ftplib import FTP
import md5
from xml.dom import minidom, Node
from sgmllib import SGMLParser
import urllib
import sets

usage = ' -t tarball-directory -v version /some/random/path/filename-to-convert'
help = \
'''Get a psychiatrist.'''

# Some TODOs
#   ? Make a useful help message
#   ? Automatically figure out the sourcedir from ~/.jhbuildrc
#   ? Consider automatically removing pyorbit (and libgtkhtml?)
#   - Directory search with mozilla (allow removing hardcode of mozilla-1.7.11)
#   - versions file doesn't have subdirs for c++/java/perl/python
#   - versions file doesn't separate c++/java/perl/python
#   - get rid of duplicated code between ftp and http
#   - warn about modules with revision specified that don't have a
#     limit on the tarball number
#   - abort if 'versions' exists in the current directory already

# TODOs for elsewhere
#   - Add times
#     (15 min for convert-to-tarballs, 15 minutes for fixing up output
#      files, 4.5 hours for build, 15 minutes to test (if development
#      version), 15 minutes to sanity check, 15 minutes to run relevant
#      release scripts, plus 15 minutes slush time or so -- total: 6
#      hours)
#   - Add a big README file saying how to use stuff, basics of how it
#     works, and how to modify it

# Extra stuff to document (for myself or elsewhere)
#   - don't forget to mount of /usr/local on amr
#   - mention removing lines from $prefix/share/jhbuild/packagedb.xml

class Options:
    def __init__(self, filename):
        self.filename = filename
        self.rename = {}
        self.drop_prefix = []
        self.release_sets = []
        self.release_set = []
        self.version_limit = {}
        self.cvs_locations = []
        self.module_locations = []
        self._read_conversion_info()

    def translate_name(self, modulename):
        # First, do the renames in the dictionary
        try:
            newname = self.rename[modulename]
        except KeyError:
            newname = modulename

        # Second, drop any given prefixes
        for drop in self.drop_prefix:
            newname = re.sub(r'^' + drop + '(.*)$', r'\1', newname)

        return newname

    def module_included(self, modulename):
        index = None
        realname = self.translate_name(modulename)
        for set in range(len(self.release_sets)):
            try:
                index = self.release_set[set].index(realname)
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
                return os.path.join(list[1], subdir)
        for list in self.cvs_locations:
            if re.search(list[0] + '$', cvssite):
                subdir = ''
                if len(list) == 3:
                    subdir = re.sub(r'\$module', modulename, list[2])
                return os.path.join(list[1], subdir)
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
                
                # Find the appropriate release set
                if node.attributes.get('set'):
                    set = node.attributes.get('set').nodeValue
                else:
                    set = 'Other'

                # Add it to the lists
                try:
                    index = self.release_sets.index(set)
                except:
                    index = None
                if index is not None:
                    self.release_set[index].append(name)
                else:
                    self.release_sets.append(set)
                    self.release_set.append([ name ])
            else:
                sys.stderr.write('Bad whitelist node\n')
                sys.exit(1)

    def get_version_limit(self, modulename):
        # First, do the renames in the dictionary
        try:
            limit = self.version_limit[modulename]
        except KeyError:
            limit = None

        return limit

    def _read_conversion_info(self):
        document = minidom.parse(self.filename)
        conversion_stuff = document.documentElement
        for node in conversion_stuff.childNodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'locations':
                self._get_locations(node)
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
    def __init__(self, tarballdir):
        self.tarballdir = tarballdir
        if not os.path.exists(tarballdir):
            os.mkdir(tarballdir)

    def _bigger_version(self, a, b):
        a_nums = re.split(r'\.', a)
        b_nums = re.split(r'\.', b)
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
        a_nums = re.split(r'\.', a)
        b_nums = re.split(r'\.', max_version)
        num_fields = min(len(a_nums), len(b_nums))
        for i in range(0,num_fields):
            if   int(a_nums[i]) > int(b_nums[i]):
                return True
            elif int(a_nums[i]) < int(b_nums[i]):
                return False
        return True

    def _get_latest_version(self, versions, max_version):
        biggest = versions[0]
        skip_version_check = not max_version
        for version in versions[1:]:
            if (version == self._bigger_version(biggest, version) and \
                not self._version_greater_or_equal_to_max(version, max_version)):
                biggest = version
        return biggest

    def _get_files_in_tarball_dir(self, ftp):
        location = ''
        good_dir = re.compile('^([0-9]+\.)*[0-9]+$')
        def hasdirs(x): return good_dir.search(x)
        while True:
            files = ftp.nlst()
            newdirs = filter(hasdirs, files)
            if newdirs:
                newdir = self._get_latest_version(newdirs)
                location = os.path.join(location, newdir)
                ftp.cwd(newdir)
            else:
                break
        return location, files

    def _get_tarball_stats(self, location, filename):
        newfile = os.path.join(self.tarballdir, filename)
        if not os.path.exists(newfile):
            print "Downloading ", filename
            print 'wget ' + location + ' -O ' + newfile
            file = os.popen('wget ' + location + ' -O ' + newfile)
            error = file.close()
            if error:
                sys.stderr.write('Couldn''t download ' + filename + '!\n')
                return '', ''
        size = os.stat(newfile)[6]
        sum = md5.new()
        fp = open(newfile, 'rb')
        data = fp.read(4096)
        while data:
            sum.update(data)
            data = fp.read(4096)
        fp.close()
        md5sum = sum.hexdigest()
        return md5sum, str(size)

    def _get_files_in_http_tarball_dir(self, location, max_version):
        good_dir = re.compile('^([0-9]+\.)*[0-9]+/?$')
        def hasdirs(x): return good_dir.search(x)
        def fixdirs(x): return re.sub(r'^([0-9]+\.[0-9]+)/?$', r'\1', x)
        while True:
            usock = urllib.urlopen(location)
            parser = urllister()
            parser.feed(usock.read())
            usock.close()
            parser.close()
            files = parser.urls
            newdirs = filter(hasdirs, files)
            newdirs = map(fixdirs, newdirs)
            if newdirs:
                newdir = self._get_latest_version(newdirs, max_version)
                location = os.path.join(location, newdir)
            else:
                break
        return location, files

    def _get_http_tarball(self, location, modulename, max_version):
        print "LOOKING for " + modulename + " tarball at " + location
        location, files = \
          self._get_files_in_http_tarball_dir(location, max_version)

        def isbz2tarball(x): return x.endswith('.tar.bz2')
        def isgztarball(x):  return x.endswith('.tar.gz')
        tarballs = filter(isbz2tarball, files)
        if not tarballs:
            tarballs = filter(isgztarball, files)

        # Only include tarballs for the given module
        def has_modulename(x): return re.match(re.escape(modulename), x)
        tarballs = filter(has_modulename, tarballs)

        ## Don't include -beta -installer -stub-installer and all kinds of
        ## other stupid inane tarballs
        #def valid_tarball(x): return re.search(r'([0-9]+\.)*[0-9]+\.tar', x)
        #tarballs = filter(valid_tarball, tarballs)

        def getversion(x):
            return re.sub(r'^.*-(([0-9]+\.)*[0-9]+)\.tar.*$', r'\1', x)
        versions = map(getversion, tarballs)

        if len(versions) == 0:
            raise IOError('No versions found')
        version = self._get_latest_version(versions, max_version)
        index = versions.index(version)

        location = os.path.join(location, tarballs[index])
        md5sum, size = self._get_tarball_stats(location, tarballs[index])
        return location, version, md5sum, size

    def _get_ftp_tarball(self, site, basedir, modulename):
        print "LOOKING for " + modulename + " tarball at " + \
              "ftp://" + site + "/" + basedir
        ftp = FTP(site)
        ftp.login('anonymous', '')
        ftp.cwd(basedir)
        subdir, files = self._get_files_in_tarball_dir(ftp)

        def isbz2tarball(x): return x.endswith('.tar.bz2')
        def isgztarball(x):  return x.endswith('.tar.gz')
        tarballs = filter(isbz2tarball, files)
        if not tarballs:
            tarballs = filter(isgztarball, files)

        def getversion(x):
            return re.sub(r'^.*-(([0-9]+\.)*[0-9]+)\.tar.*$', r'\1', x)
        versions = map(getversion, tarballs)
        version = self._get_latest_version(versions)
        index = versions.index(version)

        location = os.path.join ('ftp://'+site, basedir)
        location = os.path.join (location, subdir)
        location = os.path.join (location, tarballs[index])
        md5sum, size = self._get_tarball_stats(location, tarballs[index])
        ftp.quit()
        return location, version, md5sum, size

    def find_tarball(self, baselocation, modulename, max_version):
        if re.match(r'^ftp://', baselocation):
            bla = re.match(r'^[a-z]+://([a-z0-9\._]*)/(.*)', baselocation)
            site = bla.group(1)
            subdirs = bla.group(2)
            return self._get_ftp_tarball(site, subdirs, modulename, max_version)
        elif re.match(r'^http://', baselocation):
            return self._get_http_tarball(baselocation, modulename, max_version)
        else:
            sys.stderr.write('Invalid location for ' + modulename + ': ' +
                             baselocation + '\n')
            sys.exit(1)

class ConvertToTarballs:
    def __init__(self, tarballdir, version, sourcedir, options):
        self.tarballdir = tarballdir
        self.version = version
        self.sourcedir = sourcedir
        self.options = options
        self.ignored = []
        self.not_found = []
        self.all_tarballs = []
        self.all_versions = []
        self.locator = TarballLocator(tarballdir)

    def _create_tarball_node(self, document, node):
        tarball = document.createElement('tarball')
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
        source_node = document.createElement('source')
        tarball.appendChild(source_node)

        if cvsroot == None:  # gnome cvs
            cvsroot = 'gnome.org'

        try:
            name = self.options.translate_name(id)
            baselocation = self.options.get_download_site(cvsroot, name)
            max_version = self.options.get_version_limit(name)
            location, version, md5sum, size = \
                      self.locator.find_tarball(baselocation, name, max_version)
            print '  ', location, version, md5sum, size
            tarball.setAttribute('version', version)
            source_node.setAttribute('href', location)
            source_node.setAttribute('size', size)
            source_node.setAttribute('md5sum', md5sum)
            self.all_tarballs.append(name)
            self.all_versions.append(version)
        except IOError:
            print '**************************************************'
            print 'Could not find site for ' + id
            print '**************************************************'
            print ''
            self.not_found.append(id)
            tarball.setAttribute('version', 'EAT-YOUR-BRAAAAAANE')
            source_node.setAttribute('href', 'http://somewhere.over.the.rainbow/where/bluebirds/die')
            source_node.setAttribute('size', 'HUGE')
            source_node.setAttribute('md5sum', 'blablablaihavenorealclue')
        return tarball

    def _walk(self, oldRoot, newRoot, document):
        for node in oldRoot.childNodes:
            if node.nodeType == Node.ELEMENT_NODE:
                save_entry_as_is = False
                if node.nodeName == 'cvsroot' or \
                   node.nodeName == 'svnroot' or \
                   node.nodeName == 'arch-archive':
                    continue
                elif node.nodeName == 'cvsmodule' or     \
                     node.nodeName == 'mozillamodule' or \
                     node.nodeName == 'svnmodule':
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

    def fix_file(self, input_filename):
        newname = re.sub(r'^([a-z]+).*(.modules)$',
                         r'\1-' + self.version + r'\2',
                         input_filename)
        if (os.path.isfile(newname)):
            sys.stderr.write('Can''t proceed; would overwrite '+newname+'\n')
            sys.exit(1)

        old_document = minidom.parse(os.path.join(self.sourcedir, input_filename))
        oldRoot = old_document.documentElement

        new_document = minidom.Document()
        newRoot = new_document.createElement(oldRoot.nodeName)
        new_document.appendChild(newRoot)

        self._walk(oldRoot, newRoot, new_document)

        newfile = file(newname, 'w+')
        new_document.writexml(newfile, "", "  ", '\n')

        old_document.unlink()
        new_document.unlink()

        return newname

    def show_ignored(self):
        print '**************************************************'
        if len(self.ignored) > 0:
            print 'The following modules were ignored: ',
            for module in self.ignored:
                print module,
            print ''
        else:
            print 'No modules were ignored.'

    def show_unused_whitelist_modules(self):
        print '**************************************************'
        full_whitelist = []
        for set in self.options.release_set:
            full_whitelist.extend(set)
        unique = sets.Set(full_whitelist) - sets.Set(self.all_tarballs)
        if len(unique) > 0:
            print 'Unused whitelisted modules: ',
            for module in unique:
                print module,
            print ''
        else:
            print "No unused whitelisted modules!"

    def show_not_found(self):
        print '**************************************************'
        if len(self.not_found) > 0:
            print 'Tarballs were not found for the following modules: ',
            for module in self.not_found:
                print module,
            print ''
        else:
            print "Tarballs were found for all non-ignored modules!"

    def create_versions_file(self):
        print '**************************************************'
        versions = open('versions', 'w')
        for set in range(len(self.options.release_sets)):
            release_set = self.options.release_sets[set]
            if release_set != 'Other':
                versions.write('## %s\n' % string.upper(release_set))
                modules_sorted = self.options.release_set[set]
                modules_sorted.sort()
                for module in modules_sorted:
                    try:
                        index = self.all_tarballs.index(module)
                        version = self.all_versions[index]
                        versions.write('%s:%s:%s:\n' %
                                       (release_set, module, version))
                    except:
                        print 'No version found for %s' % module
                versions.write('\n')
        versions.close()

def main(args):
    program_name = args[0]
    if len(args) % 2 != 0:
        sys.stderr.write(program_name + usage + '\n')
        sys.exit(1)
    try:
        opts, args = getopt.getopt(args[1:], 't:v:h',
                                   ['tarballdir=', 'version=', 'help'])
    except getopt.error, exc:
        sys.stderr.write(program_name % ': %s\n' % str(exc))
        sys.stderr.write(program_name + usage + '\n')
        sys.exit(1)

    tarballdir = os.path.join(os.getcwd(), 'tarballs')
    version = None
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print program_name + usage
            print help
            sys.exit(0)
        elif opt in ('-t', '--tarballdir'):
            tarballdir = arg
        elif opt in ('-v', '--version'):
            version = arg
    if not version:
        sys.stderr.write(program_name + usage + '\n')
        sys.exit(1)

    options = Options('tarball-conversion.config')
    file_location, filename = os.path.split(args[-1])
    convert = ConvertToTarballs(tarballdir, version, file_location, options)
    convert.fix_file(filename)
    convert.show_ignored()
    convert.show_unused_whitelist_modules()
    convert.show_not_found()
    convert.create_versions_file()
    
if __name__ == '__main__':
    main(sys.argv)
