#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import datetime
import libschedule
import json
import sys

events = libschedule.parse_file()
NEWSTABLE_RELEASE = libschedule.NEWSTABLE_RELEASE


def freezes():
    the_freezes = [event for event in events if event.category == 'freeze' and event.detail == 'the-freeze']
    if len(the_freezes) != 1:
        print('the-freeze is missing from the schedule, or appears more than once')
        sys.exit(1)
    the_freeze = the_freezes[0]

    string_freezes = [event for event in events if event.category == 'freeze' and event.detail == 'string']
    if len(string_freezes) != 1:
        print('string freeze is missing from the schedule, or appears more than once')
        sys.exit(1)
    string_freeze = string_freezes[0]

    freezes = [{
        'type': 'API/ABI',
        'start_date': str(the_freeze.date),
    }, {
        'type': 'Feature',
        'start_date': str(the_freeze.date),
    }, {
        'type': 'UI',
        'start_date': str(the_freeze.date),
    }, {
        'type': 'String Announcement',
        'start_date': str(the_freeze.date),
    }, {
        'type': 'String',
        'start_date': str(string_freeze.date),
    }]

    return freezes


def find_soft_translation_deadline():
    deadlines = [event for event in events if event.category == 'task' and event.detail == 'translation-deadline']
    if len(deadlines) != 1:
        print('soft translation deadline is missing from the schedule, or appears more than once')
        sys.exit(1)
    return str(deadlines[0].date)


def find_newstable_release_date():
    newstable_release_date = None
    for event in events:
        if event.category == 'release' and event.version == str(f'{NEWSTABLE_RELEASE}.0'):
            newstable_release_date = event.date
            break
    if newstable_release_date == None:
        print(f'The newstable release {NEWSTABLE_RELEASE}.0 is missing from the schedule!')
        sys.exit(1)
    return newstable_release_date


def find_oldstable_eol_date():
    eols = [event for event in events if event.category == 'eol']
    if len(eols) != 1:
        print('eol is missing from the schedule, or appears more than once')
        sys.exit(1)
    eol = eols[0]

    if eol.detail != 'oldstable':
        print(f'eol detail "{eol.detail}" should be "oldstable"')
        sys.exit(1)

    return eol.date


def releases():
    all_releases = [event for event in events if event.category in ('tarball', 'develtarball', 'release')]
    the_releases = []
    newstable_tarball_deadline = find_newstable_release_date() - datetime.timedelta(4)  # Wednesday - 4 days = Saturday
    oldstable_eol_date = find_oldstable_eol_date()

    for release in all_releases:
        release_type = ''
        match release.detail:
            case 'oldstable':
                release_type = 'old-stable' if release.date < oldstable_eol_date else 'eol'
            case 'stable':
                release_type = 'stable' if release.date < newstable_tarball_deadline else 'old-stable'
            case 'newstable':
                release_type = 'unstable' if release.date < newstable_tarball_deadline else 'stable'
            case _:
                print(f'Event detail "{release.detail}" should be oldstable, stable, or newstable')
                sys.exit(1)

        this_release = {
            'version': release.version,
            'type': release_type,
            'tarballs_due_date': str(release.date),
        }

        if release.version == str(f'{NEWSTABLE_RELEASE - 1}.0'):
            continue

        if release.version == str(f'{NEWSTABLE_RELEASE}.0'):
            this_release |= [
                # For the .0 release, the date represents the actual release
                # date, not the tarball deadline.
                ('tarballs_due_date', str(newstable_tarball_deadline)),
                ('release_date', str(release.date)),
                ('soft_translation_deadline', find_soft_translation_deadline()),
            ]

        the_releases.append(this_release)

    return the_releases


def past_releases():
    with open('past-releases.json') as file:
        releases = json.load(file)

        # Validate that we didn't forget to add the previous release.
        previous_version = str(NEWSTABLE_RELEASE - 1)
        last_release = [release for release in releases if release['version'] == previous_version]
        if last_release == []:
            print(f'You need to add the previous release {previous_version} to past-releases.json')
            sys.exit(1)

        return releases


output = {
    'title': 'GNOME Release Calendar',
    'unstable': str(NEWSTABLE_RELEASE),
    'stable': str(NEWSTABLE_RELEASE - 1),
    'old_stable': str(NEWSTABLE_RELEASE - 2),
    'freezes': freezes(),
    'releases': releases(),
    'past_releases': past_releases()
}

print(json.dumps(output, indent=4))
