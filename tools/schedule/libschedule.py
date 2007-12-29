#!/usr/bin/env python

import datetime
import re

class GnomeReleaseEvent:
    def __init__ (self, date, week, category, detail):
        self.date = date
        self.rel_week = week
        self.category = category
        self.category_index = ["release", "freeze", "modules", "misc"].index (category)
        self.detail = detail

    def __str__(self):
        return "<%s: %s %s %s>" % (self.__class__, self.date, self.category, self.detail)

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
    yearweek_re = re.compile ("^YearWeek:(\d{4})(\d{2})$")
    item_re = re.compile ("^(-?\d{1,2}):([^:]*):([^:]*)$")

    file = open (filename, 'r')
    lines = file.readlines ()
    file.close ()

    events = []
    start = None

    for line in lines:
        # ignore comments & empty lines
        if line[0] == "#" or len (line) == 1:
            continue

        match = yearweek_re.match (line)
        if match:
            if start:
                print "Error: more than one start date specified"
                return None
            year = int (match.group (1))
            week = int (match.group (2))
            if year < 2007 or year > 2015:
                print "Error: %s is not a valid year for the start date" % year
                return None
            if week > 54:
                print "Error: %s is not a valid week for the start date" % week
                return None
            start = find_date (year, week)
            continue

        match = item_re.match (line[0:-1])
        if match:
            if not start:
                print "Error: no start date specified before line '%s'" % line[0:-1]
                return None
            week = int (match.group (1))
            category = match.group (2)
            event = match.group (3)
            if week < -10 or week > 40:
                print "Error: %s is not a valid week for an event" % week
                return None
            if category not in ["release", "freeze", "modules", "misc"]:
                print "Error: %s is not a valid category for an event" % category
                return None
            date = start + datetime.timedelta (week * 7)
            rel_event = GnomeReleaseEvent (date, week, category, event)
            events.append (rel_event)
            continue

        print "Error: line '%s' is not parsable" % line[0:-1]
        return None

    if not start:
        print "Error: empty data file"
        return None

    events.sort()

    return events
