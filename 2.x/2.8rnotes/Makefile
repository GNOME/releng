VERSION = 2.8
ROOTDOC = release-notes.xml

docbook_sources = release-notes.xml rnapplets.xml rnapplications.xml rnthemes.xml \
                  rncontrolcenter.xml rndesktop.xml rndocs.xml rnsysadmin.xml \
                  rni18n.xml \
                  rninstallation.xml rnplatform.xml rnstandards.xml \
                  rntoc.xml rnwhy.xml

html: html/index.html

html/index.html: $(docbook_sources)
	-rm -rf html
	mkdir html
	-xsltproc --xinclude -o html/ \
		--param yelp_max_chunk_depth 1 \
		--stringparam admon.graphics.path ./images/ \
		--stringparam http_root http://www.gnome.org \
		--stringparam http_prefix /start/$(VERSION)/notes/ \
		../style/db2html.xsl $(ROOTDOC)
	cp -R ../style/images figures html/
	for i in html/*.html; do \
		perl -p -i -e 's,<p class="section"></p>,<p class="section">Sections</p>,g' $$i; \
	done

clean:
	-rm -rf html

validate: $(docbook_sources)
	xmllint --xinclude --valid --noout --noent --catalogs $<

rsync_args = -vz --rsh ssh 
#rsync_args = -vz --rsh ssh --delete --delete-after

upload_path = murrayc.com/temp/release
upload-test-html: html/index.html
	rsync $(rsync_args) figures/*.png $$USER@murrayc.com:$(upload_path)/html/figures/
	rsync $(rsync_args) -r html/ $$USER@murrayc.com:$(upload_path)/html/

.PHONY: clean
