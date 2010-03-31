#!/usr/bin/env python

from libschedule import *
import itertools

events = parse_file ("3.0.schedule")

print "||<:> '''Week''' ||<:> '''Date''' || '''Task''' || '''Notes''' ||"

cat_task = set(('release', 'tarball'))
by_month = lambda val: val.date.month
by_week = lambda val: val.rel_week
by_date = lambda val: val.date.day

for month, events_month in itertools.groupby(events, by_month):
    events = list(events_month)

    month_str = events[0].date.strftime ("%B")
    print "||<-4 rowbgcolor=\"#dddddd\"> '''%s''' ||" % month_str

    for week, events_week in itertools.groupby(events, by_week):
        events = list(events_week)
        rel_week_str = events[0].rel_week

        dates = list([(key, list(items)) for key, items in itertools.groupby(events, by_date)])

        print "||<|%d ^ : #9db8d2> '''%d''' " % (len (dates), rel_week_str),
        for date, items in dates:
            date_str = items[0].date.strftime("%b %d")
            print "||<^ : #c5d2c8> %s" % date_str,


            task_items = [item for item in items if item.category in cat_task]
            note_items = [item for item in items if item.category not in cat_task]

            print "|| ", "<<BR>>".join([i.wiki_text() for i in task_items]),
            if len(note_items):
                print "||<:#e0b6af> ", "<<BR>>".join([i.wiki_text() for i in note_items]),
            else:
                print "|| ",

            print "||"


