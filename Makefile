.PHONY: all docs warts clean simplify activate test

VIRTUALENV = venv
BUILDFILES = build-resources

all: warts

warts: Makefile $(BUILDFILES)/requirements.txt
	virtualenv -ppython2.7 $(VIRTUALENV)
	bash -c 'source $(VIRTUALENV)/bin/activate; pip install -r $(BUILDFILES)/requirements.txt'
# Need this so that you can import some panda3d modules.
	cp $(BUILDFILES)/panda3d.pth $(VIRTUALENV)/lib/python2.7/site-packages/

simplify:
	find src -name '*.pyc' -exec echo removing '{}' ';' \
	                       -exec rm -f '{}' ';'

clean: simplify
	rm -r $(VIRTUALENV)

test: 
	tox -e py27
