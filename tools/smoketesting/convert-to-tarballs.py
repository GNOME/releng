#!/usr/bin/env python3

# Copyright (c) 2005-2008, Elijah Newren
# Copyright (c) 2007-2009, Olav Vitters
# Copyright (c) 2006-2009, Vincent Untz
# Copyright (c) 2017, Codethink Limited
# Copyright 2020, Abderrahim Kitouni
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



import sys
import optparse
import os
from xml.etree import ElementTree
from ruamel import yaml
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from downloadsites import SITE_KINDS


class Options:
    def __init__(self, filename):
        self.filename = filename
        self.release_sets = defaultdict(list)
        self.version_limit = {}
        self.real_name = {}
        self.default_site = None
        self.module_locations = []
        self._read_conversion_info()

    def get_module_info(self, modulename):
        realname = self.real_name.get(modulename, modulename)
        limit = self.version_limit.get(modulename, None)

        for module, site in self.module_locations:
            if module == realname:
                break
        else:
            site = self.default_site

        return realname, limit, site

    def _read_conversion_info(self):
        document = ElementTree.parse(self.filename)

        for element in document.findall('locations/site'):
            kind = element.get('kind', default='tarballs')
            location = element.get('location')
            site = SITE_KINDS[kind](location)

            if element.get('default') is not None:
                assert self.default_site is None, "only one default site can be specified"
                self.default_site = site
            elif element.get('module') is not None:
                module = element.get('module')
                self.module_locations.append([module, site])

        for element in document.findall('whitelist/package'):
            name = element.get('name')

            # Determine whether we have a version limit for this package
            max_version = element.get('limit')
            if max_version:
                self.version_limit[name] = max_version

            real_name = element.get('module')
            if real_name:
                self.real_name[name] = real_name

            # Find the appropriate release set
            release_set = element.get('set', default='Other')

            # Add it to the lists
            self.release_sets[release_set].append(name)

class ConvertToTarballs:
    def __init__(self, options, directory, convert=True, refs=False):
        self.options = options
        self.convert = convert
        self.refs = refs

        self.all_tarballs = []
        self.all_versions = []

        self.errors = []
        self.warnings = []

        with open(os.path.join(directory, 'project.conf')) as f:
            projectconf = yaml.safe_load(f)
            self.aliases = projectconf['aliases']

    def _get_module_kind(self, element):
        if 'sources' not in element:
            return 'skip'

        kind = element['sources'][0]['kind']

        if kind == 'local':
            return 'skip'
        elif kind.startswith('git'):
            return 'git'

        assert kind in ('tar', 'zip'), 'unexpected source kind {}'.format(kind)
        return 'tarball'

    def _convert_one_module(self, name, fatal):
        errors = self.errors if fatal else self.warnings
        real_name, max_version, site = self.options.get_module_info(name)

        if site.modules and real_name not in site.modules:
            errors.append(name)
            return None, None

        location, version, checksum = site.find_tarball(real_name, max_version, self.refs)

        if None in (location, version):
            errors.append(name)
        else:
            self.all_tarballs.append(name)
            self.all_versions.append(version)

        return location, checksum

    def _write_bst_file(self, fullpath, element, location, checksum):
        for alias, url in self.aliases.items():
            if location.startswith(url):
                location = alias + ':' + location[len(url):]

        if self._get_module_kind(element) == 'git':
            # Replace the first source with a tarball
            element['sources'][0] = { 'kind': 'tar', 'url': location}
            if checksum:
                element['sources'][0]['ref'] = checksum

            # cargo sources shouldn't be needed in tarballs as tarballs should
            # vendor their dependencies
            element['sources'] = [source for source in element['sources'] if source['kind'] != 'cargo']
        elif element['sources'][0]['url'] == location:
            # only change existing tarballs if the url changed. this allows us to invalidate the
            # ref if we don't have a new one
            return
        else:
            element['sources'][0]['url'] = location
            if checksum or 'ref' in element['sources'][0]:
                element['sources'][0]['ref'] = checksum

        # Dump it now
        with open(fullpath, 'w') as f:
            yaml.round_trip_dump(element, f)

    def print_errors(self):
        print("\033[91mErrors:\033[0m") # in red
        for module in self.errors:
            print("- Can't find tarball for module '{}'".format(module))

    def print_warnings(self):
        print("Warnings:")
        for module in self.warnings:
            print("- Can't update tarball for module '{}'".format(module))

    def convert_modules(self, directories):
        to_convert = {}
        to_update = {}

        for directory in directories:
            for filename in os.listdir(directory):
                if not filename.endswith('.bst'):
                    continue

                name = filename[:-len('.bst')]
                fullpath = os.path.join(directory, filename)

                with open(fullpath) as f:
                    element = yaml.round_trip_load(f)

                module_kind = self._get_module_kind(element)
                if module_kind == 'git':
                    to_convert[name] = fullpath, element
                elif module_kind == 'tarball':
                    to_update[name] = fullpath, element

        executor = ThreadPoolExecutor()

        converted = None
        if self.convert:
            converted = {executor.submit(self._convert_one_module, name, True): name for name in to_convert}

        updated = {executor.submit(self._convert_one_module, name, False): name for name in to_update}

        if converted:
            for future in tqdm(as_completed(converted), 'Converting git repos',
                               unit='', total=len(converted)):
                name = converted[future]
                fullpath, element = to_convert[name]
                location, checksum = future.result()

                if location:
                    self._write_bst_file(fullpath, element, location, checksum)

        for future in tqdm(as_completed(updated), 'Updating existing tarballs',
                           unit='', total=len(updated)):
            name = updated[future]
            fullpath, element = to_update[name]
            location, checksum = future.result()

            if location:
                self._write_bst_file(fullpath, element, location, checksum)

    def create_versions_file(self):
        versions = []

        for release_set, modules in self.options.release_sets.items():
            if release_set == 'Other':
                continue

            versions.append('## %s\n' % release_set.upper())

            for module in sorted(modules):
                real_module, _, _ = self.options.get_module_info(module)
                index = self.all_tarballs.index(module)
                version = self.all_versions[index]

                triplet = '%s:%s:%s:\n' % (release_set, real_module, version)
                if triplet not in versions:
                    versions.append(triplet)

        with open('versions', 'w') as f:
            f.writelines(versions)


def main(args):
    program_dir = os.path.abspath(sys.path[0] or os.curdir)

    parser = optparse.OptionParser()
    parser.add_option("-d", "--directory", dest="directory",
                      help="buildstream project directory", metavar="DIR")
    parser.add_option("-v", "--version", dest="version",
                      help="GNOME version to build")
    parser.add_option("-f", "--force", action="store_true", dest="force",
                      default=False, help="overwrite existing versions file")
    parser.add_option("-c", "--config", dest="config",
                      help="tarball-conversion config file", metavar="FILE")
    parser.add_option("", "--no-convert", action="store_false", dest="convert",
                      default=True, help="do not convert, only try to update elements that already use tarballs")
    (options, args) = parser.parse_args()

    if not options.version:
        parser.print_help()
        sys.exit(1)

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
            config = Options(os.path.join(program_dir, 'tarball-conversion-{}-{}.config'.format(splitted_version[0], splitted_version[1])))
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

    if int(splitted_version[1]) % 2 == 0:
        flatpak_branch = '{}.{}'.format(splitted_version[0], splitted_version[1])
        qualifier = ''
        update_flatpak_branch = True
    elif int(splitted_version[2]) >= 90:
        flatpak_branch = '{}.{}'.format(splitted_version[0], int(splitted_version[1]) + 1)
        qualifier = 'beta'
        update_flatpak_branch = True
    else:
        update_flatpak_branch = False

    convert = ConvertToTarballs(config, options.directory, options.convert, update_flatpak_branch)
    convert.convert_modules([os.path.join(options.directory, 'elements', directory)
                             for directory in ('core-deps', 'core', 'sdk-deps', 'sdk')])

    if convert.errors:
        convert.print_errors()
        exit(1)

    if convert.warnings:
        convert.print_warnings()

    if options.convert:
        convert.create_versions_file()

        # update variables in the .gitlab-ci.yml
        if update_flatpak_branch:
            cifile = os.path.join(options.directory, '.gitlab-ci.yml')
            with open(cifile) as f:
                ci = yaml.round_trip_load(f, preserve_quotes=True)

            ci['variables']['FLATPAK_BRANCH'] = flatpak_branch + qualifier

            if 'BST_STRICT' in ci['variables']:
                ci['variables']['BST_STRICT'] = '--strict'

            with open(cifile, 'w') as f:
                yaml.round_trip_dump(ci, f, width=200)

            # update project.conf
            projectconf = os.path.join(options.directory, 'project.conf')
            with open(projectconf) as f:
                conf = yaml.round_trip_load(f, preserve_quotes=True)

            conf['variables']['branch'] = flatpak_branch
            conf['variables']['qualifier'] = qualifier
            conf['ref-storage'] = 'inline'

            with open(projectconf, 'w') as f:
                yaml.round_trip_dump(conf, f, width=200)

            # move junction refs to the respective files
            junctionrefs = os.path.join(options.directory, 'junction.refs')
            if os.path.exists(junctionrefs):
                with open(junctionrefs) as f:
                    refs = yaml.safe_load(f)['projects']['gnome']

                for element in refs.keys():
                    elfile = os.path.join(options.directory, conf['element-path'], element)
                    with open(elfile) as f:
                        eldata = yaml.round_trip_load(f, preserve_quotes=True)

                    for i in range(len(refs[element])):
                        if not refs[element][i]: # source has no ref
                            continue

                        eldata['sources'][i]['ref'] = refs[element][i]['ref']

                    with open(elfile, 'w') as f:
                        yaml.round_trip_dump(eldata, f)

                os.unlink(junctionrefs)

if __name__ == '__main__':
    try:
      main(sys.argv)
    except KeyboardInterrupt:
      pass
