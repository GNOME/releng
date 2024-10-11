# Getting started

* Create a new .schedule file using last year's corresponding spring or fall schedule as a template
* The .1 stable release is included in both the previous release schedule and the new schedule, so be sure that the release date is the same in both schedules
* Bump version number for NEWSTABLE_RELEASE in releng/tools/schedule/libschedule.py

# Creating and upload the iCalendar file

* Run ./ical.py > n.ics (replace n with the version you are working on)
* Copy ics file to Infrastructure/static-web/calendars and git commit/push it ([example](https://gitlab.gnome.org/Infrastructure/static-web/-/commit/a887c9e44b36dfa6c96db093356f3222bef7d977))

# Update release.gnome.org

* Add last release to past-release.json
* Run ./rgo-json.py > calendar.json
* Copy calendar.json to Teams/Websites/release.gnome.org/_data and open a merge request ([example](https://gitlab.gnome.org/Teams/Websites/release.gnome.org/-/commit/3e0912d27b234ed64cb13ae875d1bfb34ac85054))

# Final steps

* git add, commit, and push your changes in this repo
* Announce the new schedule on Discourse using the announcement tag ([example](https://discourse.gnome.org/t/gnome-44-release-schedule-available/11386))!

# Warning

* The code in this repo is immediately deployed to OpenShift after you push your changes. Anything you change could break Discourse release reminders. Be careful!
