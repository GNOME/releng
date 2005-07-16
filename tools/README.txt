Some of these scripts are installed on our "widget" server. There is no particular guarantee that these copies in cvs are in sync. But when making changes please do try to store an updated copy here in cvs.

install-module:
  Installed on the "widget" server. Used to release a tarball on the ftp server.

release_set_scripts/release:
  Takes a versions file and creates a new directory of symlinks for a whole GNOME release set
  release on the ftp server.
 Currently installed as /home/jdub/bin/release.

release_set_scripts/release-suites
release_set_scripts/release-news
release_set_scripts/release-diff

versions:
  Example versions file for use with release-suites. For instance, release-suites 2.11.5 versions

