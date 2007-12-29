#!/usr/bin/env python

import datetime
import re

class GnomeReleaseEvent:
    def __init__ (self, date, week, category, detail, version=None):
        self.date = date
        self.rel_week = week
        self.category = category
        self.category_index = ["release", "freeze", "modules", "misc"].index (category)
        self.detail = detail
        self.version = version

    def __str__(self):
        v = self.version
        if v is None:
            v = ''
        else:
            v = ' ' + v
        return "<%s: %s %s %s%s>" % (self.__class__, self.date, self.category, self.detail, v)

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

            rel_event = GnomeReleaseEvent (date, week, category, event, version)
            events.append (rel_event)
            continue


    if not start:
        print "Error: empty data file"
        return None

    events.sort()

    return events
