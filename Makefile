.PHONY: all docs warts clean activate

VIRTUALENV = venv
BUILDFILES = build-resources

all: warts

warts: Makefile
	virtualenv -ppython2.7 $(VIRTUALENV)
	bash -c 'source $(VIRTUALENV)/bin/activate; pip install -r $(BUILDFILES)/requirements.txt'
# Need this so that you can import some panda3d modules.
	cp $(BUILDFILES)/panda3d.pth $(VIRTUALENV)/lib/python2.7/site-packages/

clean:
	rm -r $(VIRTUALENV)
