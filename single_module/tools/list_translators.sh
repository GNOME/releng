#!/bin/bash

# usage: tranlators.sh LAST_RELEASE_TAG
#
# Note: must be run from the module's toplevel
# directory.

cvs diff -r $1 po/ChangeLog | \
  (awk  '/\+.*([a-z][a-zA-Z@]*\.po)/ { print gensub (":", " ", "g", $3); }' | \
    while read file; do
  echo $(grep "Last-Translator" po/$file | sed -e 's/"Last-Translator:  *\(.*\)  *<.*/\1/') "(${file%%.po})"
done) | sort | uniq
