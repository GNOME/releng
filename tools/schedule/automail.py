#!/usr/bin/env python

import datetime
from libschedule import *
import smtplib
from email.MIMEText import MIMEText
import StringIO
import textwrap

cat_task = set(('release', 'tarball'))

FOOTER = """\n\n\nFor more information about $unstable, the full schedule, the official
module lists and the proposed module lists, please see our colorful $unstable
page:
   http://www.gnome.org/start/unstable

For a quick overview of the GNOME schedule, please see:
   http://live.gnome.org/Schedule

Thanks,"""

def mail_events(events):
    if not len(events): return # sanity check

#    mail = 'release-team@gnome.org'
    mail = 'fcrozat@mandriva.com'
#    mail = 'fcrozat@gmail.com'

#    mail = 'devel-announce-list@gnome.org'

    subject = ""
    tasks = [event for event in events if event.category in cat_task]
    notes = [event for event in events if event.category not in cat_task]
    if (len(tasks) and not len(notes)) or (len(notes) and not len(tasks)):
        subject = ', '.join([event.summary() for event in events])
    else:
        # Show tasks only, even if we have notes
        subject = "%s (and more)" % ', '.join([task.summary() for task in tasks])


    contents = StringIO.StringIO()
    contents.write("Hello all,\n\n")
    if len(events) > 1:
        contents.write("We would like to inform you about the following:\n* %s\n\n\n" % "\n* ".join([event.summary() for event in events]))

    contents.write("\n\n\n".join([textwrap.fill(event.description()) for event in events]))

    contents.write(string.Template(FOOTER).safe_substitute(events[0]))

    s = smtplib.SMTP()
    s.connect()
    contents.seek(0)
    mime = MIMEText(contents.read())
    mime['Subject'] = subject
    mime['From'] = 'Release Team <release-team@gnome.org>'
    mime['To'] = mail
    s.sendmail('accounts@gnome.org', [mail], mime.as_string())



events = parse_file ("2.24.schedule")
today = datetime.date.today()
today_plus3 = today + datetime.timedelta (3)

events_to_email = []
for event in events:
    if event.date == today_plus3:
        events_to_email.append(event)

if len(events_to_email):
    mail_events(events_to_email)

# For testing purposes
#dates = set()
#for event in events:
#    dates.add(event.date)
#
#for date in dates:
#    events_to_email = [event for event in events if event.date == date]
#    mail_events(events_to_email)


