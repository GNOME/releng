#!/usr/bin/env python3

import datetime
from libschedule import *
import smtplib
from email.mime.text import MIMEText
import io
import textwrap
import email.utils

cat_task = set(('release', 'tarball'))

FOOTER = """\n\n\nFor more information about the schedule for GNOME $newstable,
please see:
   https://wiki.gnome.org/Schedule

Thanks,
--
Automatically generated email. Source at:
https://gitlab.gnome.org/GNOME/releng/-/blob/master/tools/schedule/automail.py"""

def mail_events(events):
    if not events: return # sanity check

    mail = 'desktop@discourse.gnome.org'

    subject = ""
    tasks = [event for event in events if event.category in cat_task]
    notes = [event for event in events if event.category not in cat_task]
    if (tasks and not notes) or (notes and not tasks):
        subject = ', '.join([event.summary for event in events])
    else:
        # Show tasks only, even if we have notes
        subject = "%s (and more)" % ', '.join([task.summary for task in tasks])

    assignees = set(event.assignee for event in events if event.assignee)
    if assignees:
        subject += ' (responsible: %s)' % ', '.join(assignees)

    contents = io.StringIO()
    contents.write("Hello all,\n\n")
    if len(events) > 1:
        contents.write("We would like to inform you about the following:\n* %s\n\n\n" % "\n* ".join([event.summary for event in events]))

    contents.write("\n\n\n".join([textwrap.fill(event.description) for event in events]))

    contents.write(string.Template(FOOTER).safe_substitute(events[0]))

    s = smtplib.SMTP()
    s.connect(host='smtp-int.gnome.org')
    contents.seek(0)
    mime = MIMEText(contents.read())
    mime['Subject'] = subject
    mime['From'] = 'GNOME Release Team <releng@gnome.org>'
    mime['Date'] = email.utils.formatdate()
    mime['To'] = mail
    s.sendmail('noreply@gnome.org', [mail], mime.as_string())



events = parse_file()
today = datetime.date.today()
date_to_notify_for = today + datetime.timedelta (3)

events_to_email = [event for event in events if event.automail and event.date == date_to_notify_for]

if events_to_email:
    mail_events(events_to_email)

# For testing purposes
#dates = set()
#for event in events:
#    dates.add(event.date)
#
#for date in dates:
#    events_to_email = [event for event in events if event.date == date]
#    mail_events(events_to_email)


