#!/usr/bin/env python3

from libschedule import *
import itertools
import calendar

def wiki_cal_week(events, week, m):
    cells = []
    for day in week:
        f1 = '<#c5d2c8>' if day.month == m else ''
        f2 = str(day.day) if day not in events else '[[#d%s|%s|title="%s"]]' % (day.isoformat(), str(day.day), '; '.join((event.summary for event in events[day])))
        cells.append('%s%s' % (f1, f2))
    return cells

def wiki_cal_month(events, y, m):
    calmonth = cal.monthdatescalendar(y, m)
    if len(calmonth) < 6:
        next_month = cal.monthdatescalendar(y + 1, 1) if m == 12 else \
                     cal.monthdatescalendar(y, m + 1)

        calmonth.append(next_month[0] if calmonth[-1][-1].month == m else next_month[1])
    if len(calmonth) < 6:
        before_month = cal.monthdatescalendar(y - 1, 12) if m == 1 else \
                       cal.monthdatescalendar(y, m -  1)

        calmonth.insert(0, before_month[-1])

    yield ('<-7: rowbgcolor="#dddddd"> %s' % calmonth[2][0].strftime('%B'),)
    for week in calmonth:
        #yield [''.join(('<#c5d2c8>' if d.month == m else '', str(d.day) if d not in events else '[[#d%s|%s]]' % (d.isoformat(), str(d.day))))  for d in week]
        yield wiki_cal_week(events, week, m)

def splitter(l, n):
    i = 0
    chunk = l[:n]
    while chunk:
        yield chunk
        i += n
        chunk = l[i:i+n]

events = parse_file()

cat_task = set(('release', 'tarball', 'develtarball', 'newstabletarball'))
by_month = lambda val: val.date.month
by_week = lambda val: val.isoweek
by_date = lambda val: val.date

cal = calendar.Calendar()

months = sorted(set([(event.date.year, event.date.month) for event in events]))
day_events = dict((k, list(val)) for k, val in itertools.groupby(events, by_date))

for smonths in splitter(months, 4):
    cals = []
    for month in smonths:
        c  = wiki_cal_month(day_events, *month)
        cals.append(c)

    for r in zip(*cals):
        print('||%s||' % '||'.join(("||".join(cells) for cells in r)))

print("")
print("||<:> '''Date''' || '''Task''' || '''Notes''' ||")
year = None
for month, events_month in itertools.groupby(events, by_month):
    events = list(events_month)

    month_str = events[0].date.strftime ("%B")
    if year is None:
        year = events[0].date.year
    elif year != events[0].date.year:
        year = events[0].date.year
        print("||<-4 rowbgcolor=\"#dddddd\"> '''%d''' ||" % year)
    print("||<-4 rowbgcolor=\"#dddddd\"> '''%s''' ||" % month_str)

    for _, events_week in itertools.groupby(events, by_week):
        events = list(events_week)
        dates = list([(key, list(items)) for key, items in itertools.groupby(events, by_date)])

        for date, items in dates:
            date_str = items[0].date.strftime("%a %d")
            print("||<^ : #c5d2c8> %s %s" % (date_str, '<<Anchor(d%s)>>' % items[0].date.isoformat()), end=' ')

            task_items = [item for item in items if item.category in cat_task]
            note_items = [item for item in items if item.category not in cat_task]

            print("|| ", "<<BR>><<BR>>".join([i.wiki_text for i in task_items]), end=' ')
            if len(note_items):
                print("||<:#e0b6af> ", "<<BR>>".join([i.wiki_text for i in note_items]), end=' ')
            else:
                print("|| ", end=' ')

            print("||")


