DOCBOOK_STYLESHEET ?= toccustom.xsl
DOCBOOK_STYLESHEER ?= http://docbook.sourceforge.net/release/xsl/current/html/chunk.xsl


docbook_sources = release-notes.xml rna11y.xml rnapplets.xml \
                  rncontrolcenter.xml rndesktop.xml rndocs.xml \
                  rnutilities.xml rni18n.xml \
                  rninstallation.xml rnplatform.xml rnstandards.xml \
                  rnthanks.xml rnthemes.xml rntoc.xml rnwhy.xml rnwm.xml

html: html/index.html

html/index.html: $(docbook_sources)
	-rm -rf html
	mkdir html
	cp release.css html/
	xsltproc -o html/ --xinclude --catalogs $(DOCBOOK_STYLESHEET) $<


validate: $(docbook_sources)
	xmllint --xinclude --valid --noout --noent --catalogs $<

rsync_args = -vz --rsh ssh 
#rsync_args = -vz --rsh ssh --delete --delete-after

upload_path = murrayc.com/temp/release
upload-test-html: html/index.html
	rsync $(rsync_args) figures/*.png $$USER@murrayc.com:$(upload_path)/figures/
	rsync $(rsync_args) -r html/ $$USER@murrayc.com:$(upload_path)/html/

