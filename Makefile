.PHONY: all docs warts clean activate

VIRTUALENV = venv

all: warts

warts: Makefile
	virtualenv -ppython2.7 $(VIRTUALENV)
	bash -c 'source ./$(VIRTUALENV)/bin/activate; pip install -r requirements.txt'
	cp ./build-resources/panda3d.pth $(VIRTUALENV)/lib/python2.7/site-packages/

clean:
	rm -r $(VIRTUALENV)
