# jhbuild - a build script for GNOME 1.x and 2.x
# Copyright (C) 2001-2002  James Henstridge
#
#   moduleinfo.py: rules for building various GNOME modules.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from module import MetaModule, Tarball, FcPackage, ModuleSet


# Developer Platform
devel = ModuleSet()
devel.addmod('GConf', dependencies=['ORBit2', 'libxml2', 'gtk+'])
devel.addmod('ORBit2', dependencies=['linc', 'libIDL', 'glib'])
devel.addmod('at-spi', dependencies=['libbonobo', 'gail', 'atk', 'gtk+'])
devel.addmod('atk', dependencies=['glib'])
devel.addmod('audiofile')
devel.addmod('bonobo-activation', dependencies=['intltool', 'ORBit2', 'libxml2'])
devel.addmod('esound')
devel.addmod('gail', dependencies=['gtk+', 'atk', 'libgnomecanvas'])
devel.addmod('glib', dependencies=['gtk-doc'])
devel.addmod('gnome-mime-data')
devel.addmod('gnome-vfs', dependencies=['libbonobo', 'GConf', 'gnome-mime-data'])
devel.addmod('gtk+', dependencies=['pango', 'atk'])
devel.addmod('gtk-doc', dependencies=['libxslt'])
devel.addmod('intltool')
devel.addmod('libIDL', dependencies=['glib'])
devel.addmod('libart_lgpl')
devel.addmod('libbonobo', dependencies=['ORBit2', 'bonobo-activation'])
devel.addmod('libbonoboui', dependencies=['libgnome', 'libbonobo', 'libgnomecanvas', 'libglade'])
devel.addmod('libglade', dependencies=['gtk+', 'libxml2'])
devel.addmod('libgnome', dependencies=['libxml2', 'libxslt', 'libbonobo', 'gnome-vfs', 'GConf'])
devel.addmod('libgnomecanvas', dependencies=['gtk+', 'libart_lgpl', 'libglade'])
devel.addmod('libgnomeui', dependencies=['libbonoboui', 'libglade'])
devel.addmod('libxml2')
devel.addmod('libxslt')
devel.addmod('linc', dependencies=['glib'])
devel.addmod('pango', dependencies=['glib'])
devel.addmod('pkgconfig')

# Desktop
desktop = ModuleSet(devel)
desktop.addmod('acme')
desktop.addmod('bug-buddy', dependencies=['libgnomeui'])
desktop.addmod('gnome-control-center', dependencies=['gnome-vfs', 'libglade', 'libgnomeui', 'esound', 'gnome-desktop'])
desktop.addmod('eel', dependencies=['librsvg', 'libgnomeui', 'gail'])
desktop.addmod('eog', dependencies=['libgnomeui', 'librsvg'])
desktop.addmod('file-roller', dependencies=['scrollkeeper', 'nautilus'])
desktop.addmod('gconf-editor', dependencies=['GConf', 'gtk+'])
desktop.addmod('gdm', dependencies=['librsvg', 'libgnomeui', 'libgnomecanvas', 'libglade', 'scrollkeeper', 'libxml2'])
desktop.addmod('gedit', dependencies=['scrollkeeper', 'libgnomeui', 'libgnomeprintui'])
desktop.addmod('ggv', dependencies=['scrollkeeper', 'libgnomeui'])
desktop.addmod('gtk-engines', dependencies=['gtk+'])
desktop.addmod('gnome-applets', dependencies=['scrollkeeper', 'gnome-panel','libgtop', 'gail'])
desktop.addmod('gnome-desktop', dependencies=['libgnomeui', 'startup-notification'])
desktop.addmod('gnome-games', dependencies=['scrollkeeper', 'libgnomeui'])
desktop.addmod('gnome-icon-theme')
desktop.addmod('gnome-media', dependencies=['scrollkeeper', 'libgnomeui', 'esound', 'gail'])
desktop.addmod('gnome-panel', dependencies=['libgnomeui', 'gnome-desktop', 'libwnck'])
desktop.addmod('gnome-session', dependencies=['libgnomeui'])
desktop.addmod('gnome-system-monitor', dependencies=['libgnomeui', 'libwnck', 'libgtop'])
desktop.addmod('gnome-terminal', dependencies=['libglade', 'libgnomeui', 'vte'])
desktop.addmod('gconf-user-docs', dependencies=['scrollkeeper'])
desktop.addmod('gnome-utils', dependencies=['libgnomeui', 'gnome-panel'])
desktop.addmod('gstreamer', dependencies=['glib', 'libxml2'])
desktop.addmod('libgail-gnome', dependencies=['at-spi', 'libgnomeui'])
desktop.addmod('libgnomeprint', dependencies=['libart_lgpl', 'glib', 'pango'])
desktop.addmod('libgnomeprintui', dependencies=['libgnomeprint', 'gtk+', 'libgnomecanvas'])
desktop.addmod('libgtkhtml', dependencies=['gtk+', 'libxml2', 'gail'])
desktop.addmod('libgtop', dependencies=['glib'])
desktop.addmod('libwnck', dependencies=['gtk+'])
desktop.addmod('metacity', dependencies=['gtk+', 'GConf', 'intltool', 'libglade', 'startup-notification'])
desktop.addmod('nautilus', dependencies=['scrollkeeper', 'esound', 'eel', 'librsvg', 'libgnomeui', 'gnome-desktop', 'startup-notification'])
desktop.addmod('nautilus-media', dependencies=['gstreamer', 'nautilus'])
desktop.addmod('vte', dependencies=['gtk+'])
desktop.addmod('yelp', dependencies=['scrollkeeper', 'libgnomeui', 'libgtkhtml', 'gnome-vfs'])
desktop.addmod('scrollkeeper', dependencies=['libxml2', 'libxslt', 'intltool'])

# Unknown
desktop.addmod('gnome-themes')
desktop.addmod('librsvg')
desktop.addmod('nautilus-gtkhtml', dependencies=['nautilus', 'libgtkhtml'])
desktop.addmod('startup-notification')

gnome22 = ModuleSet(desktop)
