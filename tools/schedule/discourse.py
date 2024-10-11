#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import datetime
import io
from libschedule import *

# Flip this to True to print to console instead of actually posting to Discourse.
# Make sure to leave this False when pushing, because changes to the tools/schedule code
# are immediately deployed by OpenShift.
test_mode = False

# Notify for events scheduled on this date.
# Change this for testing the script. Example:
# date_to_notify_for = datetime.datetime(2022, 2, 22).date()
date_to_notify_for = datetime.date.today() + datetime.timedelta(3)

FOOTER = """\n\nFor more information about the schedule for GNOME $newstable,
please see the [release calendar](https://release.gnome.org/calendar/).

Thanks,
GNOME Release Team
([source](https://gitlab.gnome.org/GNOME/releng/-/blob/master/tools/schedule/discourse.py))"""


def create_discourse_post(content, title, category_id, tags):
    from pydiscourse import DiscourseClient

    api_username = os.getenv('DISCOURSE_API_USERNAME')
    api_key = os.getenv('DISCOURSE_API_KEY')

    client = DiscourseClient(
        'https://discourse.gnome.org',
        api_username=api_username,
        api_key=api_key
    )
    topic = client.create_post(
        content,
        title=title,
        category_id=category_id,
        tags=tags
    )

    return topic


def build_subject(events):
    summaries = []
    for event in events:
        summaries.append(event.summary if not event.assignee else f'{event.summary} (responsible: {event.assignee})')
    return ', '.join([summary for summary in summaries])


events = ([event for event in parse_file() if event.automail and event.date == date_to_notify_for])
if events:
    cat_task = set(('release', 'tarball', 'develtarball', 'newstabletarball'))
    tasks = [event for event in events if event.category in cat_task]
    notes = [event for event in events if event.category not in cat_task]
    subject = ''
    if (tasks and not notes) or (notes and not tasks):
        subject = build_subject(events)
    else:
        # Show tasks only, even if we have notes
        subject = f'{build_subject(tasks)} (and more)'

    contents = io.StringIO()
    contents.write("Hello all,\n\n")
    if len(events) > 1:
        contents.write("We would like to inform you about the following:\n* %s\n\n" % "\n* ".join([event.summary for event in events]))
    contents.write("\n\n".join([event.description for event in events]))
    contents.write(string.Template(FOOTER).safe_substitute(events[0]))

    if test_mode:
        print(f'{subject}')
        print(f'\n{contents.getvalue()}')
    else:
        # 6 is the ID of the Desktop category on GNOME Discourse
        # https://discourse.gnome.org/c/desktop/6
        create_discourse_post(contents.getvalue(), subject, 6, ['announcement', 'release-team'])
else:
    print('no events')
