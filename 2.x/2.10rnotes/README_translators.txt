EVERYONE:
 Always use latest xml2po HEAD CVS for working on release notes
 translations: I'm sorry for any iconvenience this may cause you.

The maintainer should do this:

in the po directory:
1. Generate a POT file for translation
   "make release-notes.pot"
2. Update all translations in PO files and print the stats out
   "make stats"
3. Merge all translations back (sr.po -> xml-sr/*.xml)
   "make generate" or "make" (this will print the stats out as well)
4. Periodically "run XMLFILES" to see if there's a missing file you 
   might need to add there (I didn't do $(wildcard ../*.xml) on
   purpose, since you might need to exclude some files).


Translators should do this:
1. check-out entire releng/2.x/2.10rnotes/ module
2. cd releng/2.x/2.10rnotes/po
2a. if starting, eg. for German (de)
    "make release-notes.pot && cp release-notes.pot de.po"
2b. if continuing your translation, sync it first
    "make de.po"
3. update de.po with your favourite PO editor
4. test translation:
   "make xml-de"
   then look at xml-de/*.xml files with Yelp
5. add translated screenshots inside xml-de/figures/ - See README_screenshots.txt
6. update po/ChangeLog
7. commit de.po and xml-de/figures/*.png
   DO NOT COMMIT xml-de/*.xml files, which can be easily regenerated.
