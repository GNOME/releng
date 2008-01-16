all:
	@echo "Use make install or make uninstall"

scripts = maintainer.py announcer.py

install: $(scripts) 
	/usr/bin/install -t $(HOME)/bin maintainer.py
	/usr/bin/install -t $(HOME)/bin announcer.py
	
uninstall: $(scripts)
	/bin/rm -f $(HOME)/bin/maintainer.py
	/bin/rm -f $(HOME)/bin/announcer.py
