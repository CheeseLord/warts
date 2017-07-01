.PHONY: all docs warts clean simplify activate test

# To use a Python binary other than the one in your PATH, run
#     make 'PYTHON=/path/to/alternate/python2.7'
PYTHON ?= python2.7

VIRTUALENV = ./venv
BUILDFILES = build-resources

all: warts

warts: Makefile $(BUILDFILES)/requirements.txt
	virtualenv "-p$(PYTHON)" $(VIRTUALENV)
	bash -c 'source $(VIRTUALENV)/bin/activate; pip install -r $(BUILDFILES)/requirements.txt'
# Need this so that you can import some panda3d modules.
	cp $(BUILDFILES)/panda3d.pth $(VIRTUALENV)/lib/python2.7/site-packages/

test:
	$(VIRTUALENV)/bin/tox -e py27

lint:
	$(VIRTUALENV)/bin/pylint --rcfile=src/.pylintrc src

simplify:
	rm -rf tests/__pycache__
	find src tests -name '*.pyc' -exec echo removing '{}' ';' \
	                             -exec rm -f '{}' ';'

clean: simplify
	rm -rf $(VIRTUALENV)
	rm -rf .tox .cache
