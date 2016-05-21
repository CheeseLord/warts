.PHONY: all docs warts clean activate

VIRTUALENV = venv

all: warts

warts:
	virtualenv -ppython2.7 $(VIRTUALENV)
	./$(VIRTUALENV)/bin/pip install -r requirements.txt

clean:
	rm -r $(VIRTUALENV)
