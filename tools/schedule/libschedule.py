#!/usr/bin/env python

import datetime
import re
import string

class GnomeReleaseEvent:
    def __init__ (self, date, week, category, detail, version=None):
        self.date = date
        self.rel_week = week
        self.category = category
        self.category_index = ["release", "tarball", "freeze", "modules", "misc"].index (category)
        self.detail = detail
        self.version = version
        self.wiki_predefined_text = {
                'tarball': 'GNOME $version $detail tarballs due',
                'modules': {
                    'proposals-start': 'Start of [wiki:ReleasePlanning/ModuleProposing new (app) modules proposal] period',
                    'proposals-end': 'End of [wiki:ReleasePlanning/ModuleProposing new (app) modules proposal] period',
                    'discussion': 'Module inclusion discussion heats up.',
                    'decision': '[http://mail.gnome.org/mailman/listinfo/release-team Release Team] meets about new module decisions for 2.22 with community input up to this point.'
                },
                'release': 'GNOME $version $detail release',
                'freeze': {
                    'string-announcement': 'String Change Announcement Period: All string changes must be announced to both [http://mail.gnome.org/mailman/listinfo/gnome-i18n gnome-i18n@] and [http://mail.gnome.org/mailman/listinfo/gnome-doc-list gnome-doc-list@].',
                    'ui-announcement': 'UI Change Announcement Period: All user interface changes must be announced to [http://mail.gnome.org/mailman/listinfo/gnome-doc-list gnome-doc-list@].',
                    'api': '[wiki:ReleasePlanning/Freezes API/ABI Freeze] for 2.21.x: developer APIs should be frozen at this point.',
                    'feature': '[wiki:ReleasePlanning/Freezes Feature and Module Freeze]: new modules and functionality are chosen now.',
                    'ui': '[wiki:ReleasePlanning/Freezes UI Freeze]: No UI changes may be made without approval from the [http://mail.gnome.org/mailman/listinfo/release-team release-team] and notification to the GDP ([http://mail.gnome.org/mailman/listinfo/gnome-doc-list gnome-doc-list@])',
                    'string': '[wiki:ReleasePlanning/Freezes String Freeze]: no string changes may be made without confirmation from the l10n team ([http://mail.gnome.org/mailman/listinfo/gnome-i18n gnome-i18n@]) and notification to both the release team and the GDP ([http://mail.gnome.org/mailman/listinfo/gnome-doc-list gnome-doc-list@]).',
                    'hard-code': '[wiki:ReleasePlanning/Freezes Hard Code Freeze]: no source code changes can be made without approval from the [http://mail.gnome.org/mailman/listinfo/release-team release-team]. Translation and documentation can continue.',
                    'hard-code-end': 'Hard Code Freeze ends, but other freezes remain in effect for the stable branch.'
                },
                'misc': {
                    'api-doc': '[http://live.gnome.org/ReleasePlanning/ModuleRequirements/Platform#head-2a21facd40d5bf2d73f088cd355aa98b6a2458df New APIs must be fully documented]',
                    'release-notes-start': '[http://live.gnome.org/ReleaseNotes Writing of release notes begins]'
                }
        }

    def __getitem__(self, item):
        """Allows the GnomeReleaseEvent class to be used in a string.Template"""
        return getattr(self, item)

    def __repr__(self):
        v = self.version
        if v is None:
            v = ''
        else:
            v = ' ' + v
        return "<%s: %s %s %s%s>" % (self.__class__, self.date, self.category, self.detail, v)

    def wiki_text(self):
        text = None

        predef = self.wiki_predefined_text.get(self.category, None)
        if type(predef) == dict:
            text = predef.get(self.detail)
        elif type(predef) == str:
            text = predef

        if text is not None and '$' in text:
            text = string.Template(text).safe_substitute(self)

        if text is None:
            return `self`
        else:
            return text

    def __cmp__ (self, other):
        if self.date < other.date:
            return -1
        if self.date > other.date:
            return 1
        return - (self.category_index - other.category_index)

def find_date (year, week):
    guessed = datetime.date (year, week / 4, 1)
    (iso_y, iso_w, iso_d) = guessed.isocalendar ()
    found = guessed - datetime.timedelta ((iso_d - 1) + (iso_w - week) * 7)
    return found

def parse_file (filename):
    file = open (filename, 'r')
    lines = file.readlines ()
    file.close ()

    events = []
    definitions = {}
    start = None

    for line in lines:
        # ignore comments & empty lines
        if line[0] == "#" or len (line) == 1:
            continue

        if not ':' in line:
            print "Error: line '%s' is not parsable" % line[0:-1]
            return None

        info = [item.lower().strip() for item in line.split(':')]

        if len(info) == 2:
            if info[0] == 'yearweek':
                if start:
                    print "Error: more than one start date specified"
                    return None

                year = int(info[1][:4])
                week = int(info[1][-2:])
                if year < 2007 or year > 2015:
                    print "Error: %s is not a valid year for the start date" % year
                    return None
                if week > 54:
                    print "Error: %s is not a valid week for the start date" % week
                    return None
                start = find_date (year, week)
            else:
                definitions[info[0]] = info[1]
            continue
        elif len(info) == 3:
            if not start or 'unstable' not in definitions or 'stable' not in definitions:
                print "Error: Need yearweek, stable and unstable definitions before line '%s'" % line[0:-1]
                return None

            week = int(info[0])
            category = info[1]
            event = info[2]
            if week < -10 or week > 40:
                print "Error: %s is not a valid week for an event" % week
                return None
            if category not in ["release", "freeze", "modules", "misc"]:
                print "Error: %s is not a valid category for an event" % category
                return None
            date = start + datetime.timedelta (week * 7)

            # Expand event info
            version = None
            if category == 'release' and '.' in event:
                i = event.split('.', 1)
                if not '.' in i[1]:
                    event = i[0]
                    i[0] = definitions.get(i[0], definitions['unstable'])
                    version = '.'.join(i)
            if category == 'release' and version is None:
                print "Error: line '%s' is not parsable" % line[0:-1]
                return None

            if category == 'release':
                rel_event = GnomeReleaseEvent (date, week, 'tarball', event, version)
                events.append (rel_event)
                date = date + datetime.timedelta(2)

            rel_event = GnomeReleaseEvent (date, week, category, event, version)
            events.append (rel_event)
            continue


    if not start:
        print "Error: empty data file"
        return None

    events.sort()

    return events
