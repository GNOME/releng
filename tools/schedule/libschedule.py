#!/usr/bin/env python2

import datetime
import time
import re
import string
import os
import os.path
import sys

DEFAULT_SCHEDULE='3.38.schedule'

class GnomeReleaseEvent:
    definitions = {}
    categories = {
        "release": {
            "prio": 1,
            "summary_template": 'GNOME $version $detail release',
            'wiki_template': 'GNOME $version $detail release',
            'description_template': 'GNOME $version $detail release',
        },
        "tarball": {
            "prio": 2,
            "automail": True,
            'summary_template': 'GNOME $version $detail tarballs due',
            "wiki_template": 'GNOME $version $detail tarballs due',
            "description_template": """Tarballs are due on $date before 23:59 UTC for the GNOME
$version $detail release, which will be delivered next week. Core modules
should try to follow the unstable schedule so everyone can test them.

Please make sure that your tarballs will be uploaded before Saturday 23:59
UTC: tarballs uploaded later than that will probably be too late to get
in $version. If you are not able to make a tarball before this deadline or
if you think you'll be late, please send a mail to the release team and
we'll find someone to roll the tarball for you!""",
        },
        "freeze": {
            "prio": 3,
            "automail": True,
            "summary_template": {
                'feature': 'Feature and Module Freeze',
                'the-freeze': 'API/ABI, UI and Feature Addition Freeze; String Change Announcement Period',
                'string': 'String Freeze',
                'hard-code': 'Hard Code Freeze',
                'hard-code-end': 'Hard Code Freeze ends',
            },
            "wiki_template": {
                'feature': '[[ReleasePlanning/Freezes|Feature and Module Freeze]]: new system-wide functionality and modules are chosen now.',
                'the-freeze': 'The Freeze: [[ReleasePlanning/Freezes|UI Freeze]]: No UI changes may be made without approval from the [[https://mail.gnome.org/mailman/listinfo/release-team|release-team]]; [[ReleasePlanning/Freezes|Feature Freeze]]: new functionality is implemented now; [[ReleasePlanning/Freezes|API/ABI Freeze]] for $unstable.x: Developer APIs should be frozen at this point; String Change Announcement Period: All string changes must be announced to [[https://mail.gnome.org/mailman/listinfo/gnome-i18n|gnome-i18n@]].',
                'string': '[[ReleasePlanning/Freezes|String Freeze]]: no string changes may be made without approval from the i18n team ([[https://mail.gnome.org/mailman/listinfo/gnome-i18n|gnome-i18n@]]).',
                'hard-code': '[[ReleasePlanning/Freezes|Hard Code Freeze]]: no source code changes can be made without approval from the [[https://mail.gnome.org/mailman/listinfo/release-team|release-team]]. Translation and documentation can continue.',
                'hard-code-end': 'Hard Code Freeze ends, but other freezes remain in effect for the stable branch.',
             },
            'description_template': {
                'string-announcement': 'String Change Announcement Period',
                'ui-announcement': 'UI Change Announcement Period',
                'api': """No API or ABI changes should be made in the platform libraries. For instance, no new functions, no changed function signatures or struct fields.

This provides a stable development platform for the rest of the schedule.

There should usually be a "Slushy" API/ABI Freeze before the Hard API/ABI Freeze, to encourage developers to think about API problems while they have a chance to correct them.

API freeze is not required for non-platform libraries, but is recommended.""",
                'feature': """Desktop and platform release module additions are finalised, major feature additions are listed. No new modules or features will be accepted for this release period. "Feature" should be interpreted as "Functionality" or "Ability". Bug fixes of existing features are not affected.

This allows developers to concentrate on refining the new features instead of adding yet more functionality.""",
                'ui': """No major UI changes may be made without confirmation from the release team. Small fixes do not require permission.""",
                'string': """No string changes may be made without confirmation from the i18n team.

From this point, developers can concentrate on stability and bugfixing. Translators can work without worrying that the original English strings will change, and documentation writers can take accurate screenshots. For explanation of the string freeze, and to see which kind of changes are not covered by freeze rules, check https://wiki.gnome.org/TranslationProject/HandlingStringFreezes. """,
                'hard-code': """This is a late freeze to avoids sudden last-minute accidents which could risk the stability that should have been reached at this point. No source code changes are allowed without approval from the release team, but translation and documentation should continue. Simple build fixes are, of course, allowed without asking. """,
                'hard-code-end': """Hard Code Freeze ends, but other freezes remain in effect for the stable branch."""
            },
        },
        "task": {
            "prio": 4,
            "automail": True,
            "summary_template": {
                'api-doc': 'New APIs must be fully documented',
                'release-notes-start': 'Writing of release notes begins',
                'translation-deadline': 'Soft translation deadline'
            },
            "wiki_template": {
                'api-doc': '[[https://wiki.gnome.org/ReleasePlanning/ModuleRequirements/Platform#head-2a21facd40d5bf2d73f088cd355aa98b6a2458df|New APIs must be fully documented]]',
                'release-notes-start': '[[https://wiki.gnome.org/ReleaseNotes|Writing of release notes begins]]',
                'translation-deadline': 'Soft translation deadline: translations committed after this point may be too late to be included; maintainers should not release until after this day.'
            },
            'description_template': {
                'api-doc': 'New APIs must be fully documented',
                'release-notes-start': 'Writing of release notes begins',
                'translation-deadline': 'Soft translation deadline'
            }
        },
        "conference": {
            "prio": 5,
            "summary_template": '$detail conference',
            "wiki_template": '$detail conference',
        },
        "hackfest": {
            "prio": 6,
            "summary_template": '$detail hackfest',
            "wiki_template": '$detail hackfest',
        },
        "eol": {
            "summary_template": 'End of life for $oldstable',
            "wiki_template": 'End of life for GNOME $oldstable. This will be the final update to the $oldstable runtime.',
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
        self.wiki_template = None
        self.description_template = None
        self.summary_template = None

        for name, value in self.categories[category].iteritems():
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
    def wiki_text(self):
        text = self.make_text(self.wiki_template)

        if text is None:
            return `self`
        else:
            return text

    @property
    def summary(self):
        text = self.make_text(self.summary_template)

        if text is None:
            return `self`
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

    def __cmp__ (self, other):
        return cmp(self.date, other.date) or cmp(self.prio, other.prio)

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

def parse_file (filename=DEFAULT_SCHEDULE, cls=GnomeReleaseEvent):
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
            print "Error: line '%s' is not parsable" % line[0:-1]
            return None

        info = [item.strip() for item in line.split(':')]

        if len(info) == 2:
            if info[0].lower() == 'yearweek':
                if start:
                    print "Error: more than one start date specified"
                    return None

                year = int(info[1][:4])
                week = int(info[1][-2:])
                if year < 2007 or year > 2030:
                    print "Error: %s is not a valid year for the start date" % year
                    return None
                if week > 54:
                    print "Error: %s is not a valid week for the start date" % week
                    return None
                start = find_date(year, week)
            else:
                definitions[info[0].lower()] = info[1]
            continue
        else:
            if not start or 'unstable' not in definitions or 'stable' not in definitions:
                print "Error: Need yearweek, stable and unstable definitions before line '%s'" % line[0:-1]
                return None

            fixedDate = False

            if info[0].isdigit():
                week = int(info[0])
                if week < -10 or week > 53:
                    print "Error: %s is not a valid week for an event" % week
                    return None
                date = start + datetime.timedelta(week * 7) - datetime.timedelta(2)
            else:
                date = datetime.date(*(time.strptime(info[0], '%Y-%m-%d')[0:3]))
                fixedDate = True
            category = info[1].lower()
            event = info[2]
            if category not in cls.categories:
                print "Error: %s is not a valid category for an event" % category
                return None

            # Expand event info
            version = None
            assignee = None
            if (category == 'release' or category == 'tarball') and '.' in event:
                if ' ' in event:
                    i = event.split(' ', 1)
                    event = i[0]
                    if i[1].strip():
                        assignee = i[1].strip()

                i = event.split('.', 1)
                if not '.' in i[1]:
                    event = i[0]
                    i[0] = definitions.get(i[0], definitions['unstable'])
                    version = '.'.join(i)
            if (category == 'release' or category == 'tarball') and version is None:
                print "Error: line '%s' is not parsable" % line[0:-1]
                return None

            if event == 'translation-deadline' and not fixedDate:
                date = date + datetime.timedelta(4)

            if category == 'release' and event == 'newstable':
                rel_event = cls(date, week, 'tarball', event, version, assignee)
                events.append (rel_event)

            if category == 'release' and not fixedDate:
                date = date + datetime.timedelta(4)

            rel_event = cls(date, week, category, event, version, assignee)
            events.append (rel_event)
            continue

    file.close ()

    if not start:
        print "Error: empty data file"
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
        print yw, dcalc, d, "" if d == dcalc else "WRONG"

        d += adv
