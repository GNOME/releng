#!/usr/bin/env python3

import datetime
from libschedule import *
import smtplib
from email.mime.text import MIMEText
import io
import textwrap
import email.utils

# Flip this to True to print to console instead of sending email.
test_mode = False

# Notify for events scheduled on this date.
# Example: date_to_notify_for = datetime.datetime(2022, 2, 22).date()
date_to_notify_for = datetime.date.today() + datetime.timedelta(3)

recipient = 'desktop@discourse.gnome.org'

cat_task = set(('release', 'tarball', 'develtarball'))

FOOTER = """\n\n\nFor more information about the schedule for GNOME $newstable,
please see:
   https://wiki.gnome.org/Schedule

Thanks,
--
Automatically generated email. Source at:
https://gitlab.gnome.org/GNOME/releng/-/blob/master/tools/schedule/automail.py"""

def build_subject(events):
    summaries = []
    for event in events:
        summaries.append(event.summary if not event.assignee else f'{event.summary} (responsible: {event.assignee})')
    return ', '.join([summary for summary in summaries])

def mail_events(events):
    subject = ""
    tasks = [event for event in events if event.category in cat_task]
    notes = [event for event in events if event.category not in cat_task]
    if (tasks and not notes) or (notes and not tasks):
        subject = build_subject(events)
    else:
        # Show tasks only, even if we have notes
        subject = f'{build_subject(tasks)} (and more)'

    contents = io.StringIO()
    contents.write("Hello all,\n\n")
    if len(events) > 1:
        contents.write("We would like to inform you about the following:\n* %s\n\n\n" % "\n* ".join([event.summary for event in events]))
    contents.write("\n\n\n".join([textwrap.fill(event.description) for event in events]))
    contents.write(string.Template(FOOTER).safe_substitute(events[0]))

    if test_mode:
        print(f'Subject: {subject}')
        print('From: GNOME Release Team <releng@gnome.org>')
        print(f'Date: {email.utils.formatdate()}')
        print(f'To: {recipient}')
        print(f'\n{contents.getvalue()}')
    else:
        s = smtplib.SMTP()
        s.connect(host='smtp-int.gnome.org')
        contents.seek(0)
        mime = MIMEText(contents.read())
        mime['Subject'] = subject
        mime['From'] = 'GNOME Release Team <releng@gnome.org>'
        mime['Date'] = email.utils.formatdate()
        mime['To'] = recipient
        s.sendmail('noreply@gnome.org', [recipient], mime.as_string())

events = ([event for event in parse_file() if event.automail and event.date == date_to_notify_for])
if events:
    mail_events(events)
