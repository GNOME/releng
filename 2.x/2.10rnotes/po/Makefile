# Translation management using xml2po

.PHONY : all XMLFILES update generate stats clean

all: generate stats

XMLFILES:
	@for i in $(wildcard ../*.xml); do \
		if ! grep $$i XMLFILES >/dev/null; then \
			echo Warning: File $$i is missing from XMLFILES.; \
		fi; \
	done

release-notes.pot: $(shell cat XMLFILES)
	xml2po -o release-notes.pot `cat XMLFILES`

%.po: release-notes.pot
	@echo -n "Updating translation: $@... "; \
	(xml2po -u $@ `cat XMLFILES` >/dev/null 2>&1 && echo "ok") || echo "ERROR"

xml-%: %.po
	if [ -f $< ]; then \
		mkdir -p $@ && \
		for i in `cat XMLFILES`; do \
			basename=`basename $$i`; \
			xml2po -o $@/$$basename -p $< $$i; \
		done; \
	fi

update: $(wildcard *.po)

generate: $(patsubst %.po,xml-%,$(wildcard *.po))

clean:
	rm -rf *.pot xml-*/*.xml # we don't want to delete translated screenshots

stats: $(wildcard *.po)
	@echo "==================================="; \
	echo "       Translation statistics      "; \
	echo "==================================="; \
	for i in $(wildcard *.po); do \
		echo -n "$$i: "; \
		LC_ALL=C msgfmt -o /dev/null -cv $$i; \
	done
