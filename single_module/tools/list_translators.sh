#!/bin/bash

# usage: tranlators.sh LAST_RELEASE_TAG

cvs diff -r $1 po/ChangeLog | \
  (awk  '/\+.*[a-z][a-zA-Z@]*\.po/ { print gensub ("[:,]", "\n", "g", $3); }' | \
    while read file; do
  if [ -z "$file" ]; then continue; fi
  echo $(grep "Last-Translator" po/$file | sed -e 's/"Last-Translator:  *\(.*\)  *<.*/\1/') "(${file%%.po})"
done) | sort | uniq
