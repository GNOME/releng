#!/usr/bin/env python

import datetime
from libschedule import *

def mail_tarballs_due (event):
    print "TARBALLS DUE"

def mail_tarballs_reminder (event):
    print "TARBALLS DUE (reminder)"

def mail_freeze (event):
    print "freeze"

def mail_modules (event):
    print "modules"

def mail_api_doc (event):
    print "api doc"

events = parse_file ("2.22.schedule")
today = datetime.date.today ()
today = datetime.date (2008, 3, 10)
today_plus3 = today + datetime.timedelta (3)

for event in events:
    print event
    if event.date == today_plus3 and event.category == "release":
        mail_tarballs_due (event)

    if event.date == today:
        if event.category == "release" and event.detail == "newstable.0":
            mail_tarballs_reminder (event)
        if event.category == "freeze" and event.detail != "hard-code-end":
            mail_freeze (event)
        if event.category == "modules":
            mail_modules (event)
        if event.category == "misc" and event.detail == "api-doc":
            mail_api_doc (event)
