#!/usr/bin/env python3

import datetime
import time
import re
import string
import os
import os.path
import sys

# Careful! Don't push any changes to NEWSTABLE_RELEASE until after the release
# cycle has ended, or you will break Discourse release reminders.
NEWSTABLE_RELEASE=50

# Careful! The summary should contain the GNOME version number to ensure a
# unique subject line so it doesn't fail if Discourse is configured to disallow
# topics with duplicate titles.
class GnomeReleaseEvent:
    definitions = {}
    categories = {
        "release": {
            "prio": 1,
            "summary_template": 'GNOME $version $detail release',
            'description_template': 'GNOME $version $detail release',
        },
        "newstabletarball": {
            "prio": 2,
            "automail": True,
            'summary_template': 'GNOME $version $detail tarballs due',
            "description_template": """Tarballs are due on $date before 23:59 UTC for the GNOME
$version $detail release, which will be delivered next week. All modules
that had an unstable release during the current release cycle must
release to ensure a stable version number, even if there have been no
changes since the previous release.

Please make sure that your tarballs will be uploaded before Saturday 23:59
UTC. Tarballs uploaded later than that will probably be too late. If
you need help, please contact the release team and we'll find someone to
handle the release for you.""",
        },
        "develtarball": {
            "prio": 3,
            "automail": True,
            'summary_template': 'GNOME $version $detail tarballs due',
            "description_template": """Tarballs are due on $date before 23:59 UTC for the GNOME
$version $detail release, which will be delivered next week. In order to
ensure adequate testing, core modules should try to release according to
the unstable schedule if they have nontrivial changes.

Please make sure that your tarballs will be uploaded before Saturday 23:59
UTC. Tarballs uploaded later than that will probably be too late.""",
        },
        "tarball": {
            "prio": 4,
            "automail": True,
            'summary_template': 'GNOME $version $detail tarballs due',
            "description_template": """Tarballs are due on $date before 23:59 UTC for the GNOME
$version $detail release, which will be delivered next week. Core modules
are not expected to follow the schedule for stable releases. Instead,
please release when you judge that a new stable release is required.
Modules released before this deadline will be included in the $version
update of the GNOME runtime.""",
        },
        "freeze": {
            "prio": 5,
            "automail": True,
            "summary_template": {
                'the-freeze': 'API/ABI, UI and Feature Addition Freeze; String Change Announcement Period for GNOME $newstable',
                'string': 'String Freeze for GNOME $newstable',
            },
            'description_template': {
                'the-freeze': """API freeze begins on $date at 23:59 UTC. No API or ABI changes should be made in the platform libraries. This provides a stable development platform for the rest of the schedule.

Feature freeze begins on $date at 23:59 UTC. No new modules or features will be accepted for this release period. Bug fixes of existing features are not affected. This allows developers to concentrate on refining the new features instead of adding yet more functionality.

UI freeze begins on $date at 23:59 UTC. No major UI changes may be made without confirmation from the release team. Small fixes do not require permission.""",
                'string': """String freeze begins on $date at 23:59 UTC. No string changes may be made without confirmation from the i18n team.

From this point, developers can concentrate on stability and bugfixing. Translators can work without worrying that the original English strings will change, and documentation writers can take accurate screenshots. [[https://handbook.gnome.org/release-planning/freezes.html#string-freeze|Explanation of the string freeze]]""",
            },
        },
        "task": {
            "prio": 6,
            "automail": True,
            "summary_template": {
                'api-doc': 'New APIs for GNOME $newstable must be fully documented',
                'release-notes-start': 'Writing of GNOME $newstable release notes begins',
                'translation-deadline': 'Soft translation deadline for GNOME $newstable'
            },
            'description_template': {
                'api-doc': 'New APIs must be fully documented',
                'release-notes-start': 'Writing of release notes begins',
                'translation-deadline': 'Soft translation deadline is $date at 23:59 UTC. Translations committed after this point may be too late to be included. Maintainers should not release stable tarballs until after this day.'
            }
        },
        "conference": {
            "prio": 7,
            "summary_template": '$detail conference ($date)',
        },
        "hackfest": {
            "prio": 8,
            "summary_template": '$detail hackfest ($date)',
        },
        "eol": {
            "prio": 9,
            "summary_template": 'End of life for $oldstable',
        }
    }

    def __init__ (self, date, week, category, detail, version=None, assignee=None):
        self.date = date
        self.isoweek = (date.isocalendar()[0] * 100) + date.isocalendar()[1]
        self.rel_week = week
        self.category = category
        self.detail = detail
        self.version = version
        self.assignee = assignee
        self.prio = None
        self.automail = False
        self.description_template = None
        self.summary_template = None

        for name, value in self.categories[category].items():
            setattr(self, name, value)

    def __getitem__(self, item):
        """Allows the GnomeReleaseEvent class to be used in a string.Template"""
        if hasattr(self, item):
            return getattr(self, item)
        else:
            return self.__class__.definitions[item]

    def __repr__(self):
        v = self.version
        if v is None:
            v = ''
        else:
            v = ' ' + v
        return "<%s: %s %s %s%s>" % (self.__class__, self.date, self.category, self.detail, v)

    @property
    def summary(self):
        text = self.make_text(self.summary_template)

        if text is None:
            return repr(self)
        else:
            return text

    @property
    def description(self):
        text = self.make_text(self.description_template)

        if text is None:
            return ""
        else:
            return text

    def make_text(self, predef):
        text = None

        if type(predef) == dict:
            text = predef.get(self.detail)
        elif type(predef) == str:
            text = predef

        if text is not None and '$' in text:
            text = string.Template(text).safe_substitute(self)

        return text

    def __lt__ (self, other):
        if self.date != other.date:
            return self.date < other.date
        if self.prio == None:
            return True
        if other.prio == None:
            return False
        return self.prio < other.prio

def find_date(year, week):
    guessed = datetime.date(year, 2, 1)
    (iso_y, iso_w, iso_d) = guessed.isocalendar()
    return guessed - datetime.timedelta((iso_d - 1) + (iso_w - week) * 7)

def line_input (file):
    for line in file:
        if line[-1] == '\n':
            yield line[:-1]
        else:
            yield line

def parse_file (filename=f'{NEWSTABLE_RELEASE}.schedule', cls=GnomeReleaseEvent):
    try:
        file = open(filename, 'r')
    except IOError:
        file = open(os.path.join(os.path.abspath(sys.path[0] or os.curdir), filename), 'r')

    events = []
    start = None

    definitions = cls.definitions

    for line in line_input(file):
        # ignore comments & empty lines
        if line == '' or line[0] == "#":
            continue

        if not ':' in line:
            print(f"Error: line '{line[0:-1]}' is not parseable")
            return None

        info = [item.strip() for item in line.split(':')]

        if len(info) == 2:
            if info[0].lower() == 'yearweek':
                if start:
                    print("Error: more than one start date specified")
                    return None

                year = int(info[1][:4])
                week = int(info[1][-2:])
                if year < 2007 or year > 2030:
                    print("Error: %s is not a valid year for the start date" % year)
                    return None
                if week > 54:
                    print("Error: %s is not a valid week for the start date" % week)
                    return None
                start = find_date(year, week)
            else:
                definitions[info[0].lower()] = info[1]
            continue
        else:
            if not start or 'stable' not in definitions:
                print("Error: Need yearweek and stable definitions before line '%s'" % line[0:-1])
                return None

            fixedDate = False

            if info[0].isdigit():
                week = int(info[0])
                if week < -10 or week > 53:
                    print("Error: %s is not a valid week for an event" % week)
                    return None
                date = start + datetime.timedelta(week * 7) - datetime.timedelta(2)
            else:
                date = datetime.date(*(time.strptime(info[0], '%Y-%m-%d')[0:3]))
                fixedDate = True
            category = info[1].lower()
            event = info[2]
            if category not in cls.categories:
                print("Error: %s is not a valid category for an event" % category)
                return None

            # Expand event info
            version = None
            assignee = None
            if category in ['release', 'tarball', 'develtarball'] and '.' in event:
                if ' ' in event:
                    i = event.split(' ', 1)
                    event = i[0]
                    if i[1].strip():
                        assignee = i[1].strip()

                i = event.split('.', 1)
                if not '.' in i[1]:
                    event = i[0]
                    i[0] = definitions.get(i[0])
                    version = '.'.join(i)
            if category in ['release', 'tarball', 'develtarball'] and version is None:
                print(f"Error: line '{line[0:-1]}' is not parseable")
                return None

            if event == 'translation-deadline' and not fixedDate:
                date = date + datetime.timedelta(4)

            if category == 'release' and event == 'newstable':
                rel_event = cls(date, week, 'newstabletarball', event, version, assignee)
                events.append (rel_event)

            if category == 'release' and not fixedDate:
                date = date + datetime.timedelta(4)

            rel_event = cls(date, week, category, event, version, assignee)
            events.append (rel_event)
            continue

    file.close ()

    if not start:
        print("Error: empty data file")
        return None

    events.sort()

    return events

if __name__ == '__main__':
    d = datetime.date(1980,1,7)
    end = datetime.date(2030,1,1)
    adv = datetime.timedelta(7)
    while d < end:
        yw = d.isocalendar()[:2]
        dcalc = find_date(yw[0], yw[1])
        print(yw, dcalc, d, "" if d == dcalc else "WRONG")

        d += adv
