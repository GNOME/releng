#!/usr/bin/env python

from libschedule import *

events = parse_file ("2.22.schedule")
#for i in events:
#    print "date: %s, cat: %s, %s" % (str (i.date), i.category, i.event)

current_month = None
current_month_str = None
current_rel_week = None

stacked_events = []

print "||<:> '''Week''' ||<:> '''Date''' || '''Task''' || '''Notes''' ||"

for event in events:
    if event.date.month != current_month:
        current_month = event.date.month
        current_month_str = event.date.strftime ("%B")
        print "||<-4 rowbgcolor=\"#dddddd\"> '''%s''' ||" % current_month_str

    if current_rel_week == None:
        current_rel_week = event.rel_week
        stacked_events.append (event)
        continue

    if event.rel_week == current_rel_week:
        stacked_events.append (event)
        continue

    # print events for the previous relative week
    if len (stacked_events) == 1:
        print "||<: #9db8d2> '''%d''' " % (current_rel_week)
    else:
        print "||<|%d : #9db8d2> '''%d''' " % (len (stacked_events), current_rel_week)

    print "||<: #c5d2c8> October 15"


    # now continue with the new event
    current_rel_week = event.rel_week
    stacked_events = []
    stacked_events.append (event)
