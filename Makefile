.PHONY: all docs warts clean activate

VIRTUALENV = venv

all: warts

warts:
	virtualenv -ppython2.7 $(VIRTUALENV)
	bash -c 'source ./$(VIRTUALENV)/bin/activate; pip install -r requirements.txt'

clean:
	rm -r $(VIRTUALENV)
