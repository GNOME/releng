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
import argparse
import os
from xml.etree import ElementTree
from ruamel.yaml import YAML
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
    def __init__(self, options, directory, yaml, convert=True):
        self.options = options
        self.convert = convert
        self.yaml = yaml

        self.all_tarballs = []
        self.all_versions = []

        self.errors = []
        self.warnings = []

        if os.path.exists(os.path.join(directory, 'include/aliases.yml')):
            fname = 'include/aliases.yml'
        else:
            fname = 'project.conf'

        with open(os.path.join(directory, fname)) as f:
            conf = yaml.load(f)

        self.aliases = conf['aliases']

    def _get_module_kind(self, element):
        if 'sources' not in element:
            return 'skip'

        kind = element['sources'][0]['kind']

        if kind == 'local':
            return 'skip'
        elif kind.startswith('git'):
            return 'git'

        assert kind in ('tar', 'zip', 'remote'), 'unexpected source kind {}'.format(kind)
        return 'tarball'

    def _convert_one_module(self, name, fatal):
        errors = self.errors if fatal else self.warnings
        real_name, max_version, site = self.options.get_module_info(name)

        # https://gitlab.freedesktop.org/cairo/cairo/-/issues/828
        if name == 'cairo' or name == 'cairomm':
            return None, None

        if site.modules and real_name not in site.modules:
            errors.append(name)
            return None, None

        location, version, checksum = site.find_tarball(real_name, max_version, self.convert)

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
            # check if there any git_module sources and
            # remove them since we are converting to tarballs
            element["sources"] = [
                source
                for source in element["sources"]
                if source.get("kind") != "git_module"
            ]

            # Replace the first source with a tarball
            element['sources'][0] = { 'kind': 'tar', 'url': location}
            if checksum:
                element['sources'][0]['ref'] = checksum

        elif element['sources'][0]['url'] == location:
            # only change existing tarballs if the url changed. this allows us to invalidate the
            # ref if we don't have a new one
            return
        else:
            element['sources'][0]['url'] = location
            if checksum:
                element['sources'][0]['ref'] = checksum
            elif 'ref' in element['sources'][0]:
                del element['sources'][0]['ref']

        # Dump it now
        with open(fullpath, 'w') as f:
            self.yaml.dump(element, f)

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
                name, ext = os.path.splitext(filename)
                if ext not in ('.bst', '.inc'):
                    continue

                fullpath = os.path.join(directory, filename)

                with open(fullpath) as f:
                    element = self.yaml.load(f)

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

    parser = argparse.ArgumentParser()
    parser.add_argument("directory",
                        help="buildstream project directory", metavar="DIR")
    parser.add_argument("-v", "--version", dest="version",
                        help="GNOME version to build")
    parser.add_argument("-f", "--force", action="store_true", dest="force",
                        default=False, help="overwrite existing versions file")
    parser.add_argument("--no-convert", action="store_false", dest="convert",
                        default=True, help="do not convert, only try to update elements that already use tarballs")
    args = parser.parse_args()

    if args.version:
        splitted_version = args.version.split(".")
        if len(splitted_version) == 3:
            branch = "{}-{}".format(*splitted_version[:2])
            flatpak_branch = "{}.{}".format(*splitted_version[:2])
            is_stable = True
            qualifier = ''
        elif len(splitted_version) == 2:
            flatpak_branch = branch = splitted_version[0]
            is_stable = splitted_version[1].isnumeric()
            qualifier = '' if is_stable else 'beta'
        else:
            print("ERROR: Version number is not valid", file=sys.stderr)
            exit(1)

        branch_config = 'tarball-conversion-{}.config'.format(branch)
        if is_stable or os.path.exists(branch_config):
            config = Options(os.path.join(program_dir, branch_config))
        else:
            config = Options(os.path.join(program_dir, 'tarball-conversion.config'))

    elif not args.convert:
        config = Options(os.path.join(program_dir, 'tarball-conversion.config'))
    else:
        print("ERROR: Need either --version or --no-convert", file=sys.stderr)
        exit(1)

    if args.convert and os.path.isfile('versions'):
        if args.force:
            os.unlink('versions')
        else:
            print('Cannot proceed; would overwrite versions', file=sys.stderr)
            exit(1)

    if not args.directory:
        print('Must specify the directory of the GNOME buildstream project to convert\n', file=sys.stderr)
        parser.print_help()
        exit(1)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 200

    convert = ConvertToTarballs(config, args.directory, yaml, args.convert)
    convert.convert_modules([os.path.join(args.directory, 'elements', directory)
                             for directory in ('core-deps', 'core', 'incubator', 'sdk-deps', 'sdk')])

    if convert.errors:
        convert.print_errors()
        exit(1)

    if convert.warnings:
        convert.print_warnings()

    if args.convert:
        convert.create_versions_file()

        # update variables in .gitlab-ci.yml
        cifile = os.path.join(args.directory, '.gitlab-ci.yml')
        with open(cifile) as f:
            ci = yaml.load(f)

        ci['variables']['FLATPAK_BRANCH'] = flatpak_branch + qualifier
        # flatpak_branch is just the major version, ex: 47, we have already split
        # qualifier from it. (end result 47beta)
        # For OCI_BRANCH we never want the qualifier and instead only use the version
        # ex. (core-47)
        # https://gitlab.gnome.org/GNOME/gnome-build-meta/-/merge_requests/2739
        ci['variables']['OCI_BRANCH'] = flatpak_branch

        if 'BST_STRICT' in ci['variables']:
            ci['variables']['BST_STRICT'] = '--strict'

        with open(cifile, 'w') as f:
            yaml.dump(ci, f)

        # update project.conf
        projectconf = os.path.join(args.directory, 'project.conf')
        with open(projectconf) as f:
            conf = yaml.load(f)

        conf['variables']['branch'] = flatpak_branch
        conf['variables']['qualifier'] = qualifier

        with open(projectconf, 'w') as f:
            yaml.dump(conf, f)

        # move junction refs to the respective files
        junctionrefs = os.path.join(args.directory, 'junction.refs')
        if os.path.exists(junctionrefs):
            with open(junctionrefs) as f:
                refs = yaml.load(f)['projects']['gnome']

            for element in refs.keys():
                elfile = os.path.join(args.directory, conf['element-path'], element)
                with open(elfile) as f:
                    eldata = yaml.load(f)

                for i in range(len(refs[element])):
                    if not refs[element][i]: # source has no ref
                        continue

                    eldata['sources'][i]['ref'] = refs[element][i]['ref']

                with open(elfile, 'w') as f:
                    yaml.dump(eldata, f)

            os.unlink(junctionrefs)

if __name__ == '__main__':
    try:
      main(sys.argv)
    except KeyboardInterrupt:
      pass
