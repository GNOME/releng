DOCBOOK_STYLESHEET ?= toccustom.xsl

docbook_sources = release-notes.xml rnfileroller.xml rni18n.xml rnmultimedia.xml rnterminal.xml rnwhy.xml \
                  rndesktop.xml rnfonts.xml rnmultihead.xml rnpanel.xml rnthemes.xml rnwm.xml \
                  rndocs.xml rngnomeutilities.xml rnmultimediakeys.xml rnstandards.xml rntoc.xml

html: html/index.html

html/index.html: $(docbook_sources)
	-rm -rf html
	mkdir html
	cp release.css html/
	xsltproc -o html/ --xinclude --catalogs $(DOCBOOK_STYLESHEET) $<


validate: release-notes.xml
	xmllint --xinclude --valid --noout --noent --catalogs $<

rsync_args = -vz --rsh ssh 
#rsync_args = -vz --rsh ssh --delete --delete-after

upload_path = murrayc.com/temp/release
upload-test-html: html/index.html
	rsync $(rsync_args) figures/*.png $$USER@murrayc.com:$(upload_path)/figures/
	rsync $(rsync_args) -r html/ $$USER@murrayc.com:$(upload_path)/html/

