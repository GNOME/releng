#!/usr/bin/env python3

import sys
from libschedule import *
import itertools
import vobject
import dateutil.tz

events = parse_file()

cal = vobject.iCalendar()

cal.add('calscale').value = 'GREGORIAN'

now = datetime.datetime.utcnow()
utc = vobject.icalendar.utc

for event in events:
    vevent = cal.add('vevent')

    vevent.add('class').value= 'PUBLIC'
    vevent.add('transp').value = 'OPAQUE'
    vevent.add('sequence').value = '1'
    vevent.add('created').value = now
    vevent.add('last-modified').value = now

    summary = vevent.add('summary')
    summary.value = event.summary

    desc = vevent.add('description')
    desc.value = event.description

    start = vevent.add('dtstart')
    start.value = datetime.datetime(event.date.year, event.date.month, event.date.day)

    stop = vevent.add('dtend')
    stop.value = start.value + datetime.timedelta(days=1)

    dtstamp = vevent.add('dtstamp')
    dtstamp.value = now

print(cal.serialize())

