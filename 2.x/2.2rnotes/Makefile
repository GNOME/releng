DOCBOOK_STYLESHEET ?= http://docbook.sourceforge.net/release/xsl/current/html/chunk.xsl

docbook_sources = release-notes.xml  rnfileroller.xml rngnomeutilities.xml \
                  rndesktop.xml rngnomeapplets.xml rnmultimediakeys.xml

html: html/index.html

html/index.html: $(docbook_sources)
	-rm -rf html
	xsltproc -o html/ --xinclude --catalogs $(DOCBOOK_STYLESHEET) $<


validate: release-notes.xml
	xmllint --xinclude --valid --noout --catalogs $<
