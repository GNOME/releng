DOCBOOK_STYLESHEET ?= http://docbook.sourceforge.net/release/xsl/current/html/chunk.xsl

docbook_sources = release-notes.xml  rnfileroller.xml rngnomeutilities.xml \
                  rndesktop.xml rnpanel.xml rnterminal.xml \
                  rnmultihead.xml rnmultimedia.xml rnmultimediakeys.xml rnthemes.xml

html: html/index.html

html/index.html: $(docbook_sources)
	-rm -rf html
	xsltproc -o html/ --xinclude --catalogs $(DOCBOOK_STYLESHEET) $<


validate: release-notes.xml
	xmllint --xinclude --valid --noout --catalogs $<

rsync_args = -vz --rsh ssh 
#rsync_args = -vz --rsh ssh --delete --delete-after

upload_path = murrayc.com/temp/release
upload-test-html: html/index.html
	rsync $(rsync_args) figures/*.png $$USER@murrayc.com:$(upload_path)/figures/
	rsync $(rsync_args) -r html/ $$USER@murrayc.com:$(upload_path)/html/

