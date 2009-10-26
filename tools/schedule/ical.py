#!/usr/bin/env python

import sys
from libschedule import *
import itertools
import vobject
import dateutil.tz

events = parse_file ("2.30.schedule")

cal = vobject.iCalendar()

cal.add('calscale').value = 'GREGORIAN'

now = datetime.datetime.utcnow()
utc = vobject.icalendar.utc

# Evolution seems to need specific timezones otherwise the 
# alarms aren't set. However, haven't figured out how to create those
# so that Evolution works.

#mytz = dateutil.tz.tzoffset('FOO', 1)
mytz = utc
for event in events:
    vevent = cal.add('vevent')

    vevent.add('class').value= 'PUBLIC'
    vevent.add('transp').value = 'OPAQUE'
    vevent.add('sequence').value = '1'
    vevent.add('created').value = now
    vevent.add('last-modified').value = now

    summary = vevent.add('summary')
    summary.value = event.summary()

    desc = vevent.add('description')
    desc.value = event.description()

    start = vevent.add('dtstart')
    start.value = datetime.datetime(event.date.year, event.date.month, event.date.day, 23, 00, tzinfo = mytz)
#    start.tzid_param = 'UTC' # Needed for Evolution

    stop = vevent.add('dtend')
    stop.value = datetime.datetime(event.date.year, event.date.month, event.date.day, 23, 59, 59, tzinfo = mytz)
#    stop.tzid_param = 'UTC' # Needed for Evolution

    dtstamp = vevent.add('dtstamp')
    dtstamp.value = now

    valarm = vevent.add('valarm')
    x = valarm.add('action')
    x.value = 'DISPLAY'
    x = valarm.add('description')
    x.value = summary.value
    x = valarm.add('trigger')

#    x.related_param = 'START'
#    x.value_param = 'DURATION'
#    x.related_param = 'DATE-TIME'
#    x.value_param = 'DURATION'
    if event.category == 'release':
        x.value = start.value + datetime.timedelta(hours=-1)
    else:
        x.value = start.value + datetime.timedelta(days=-3)

print cal.serialize()

