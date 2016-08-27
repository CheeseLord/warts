import os

from twisted.internet import stdio as twistedStdio
from twisted.protocols.basic import LineReceiver

def setupStdio(messageHub):
    twistedStdio.StandardIO(StdioHandler(messageHub))

class StdioHandler(LineReceiver):
    # The default delimiter for a LineReceiver is '\r\n', which doesn't work
    # with Python's stdin (at least on *nix, probably on Windows as well) which
    # uses either '\n' or os.linesep instead.
    # TODO: I'm actually not sure which separator Python uses on Windows, so
    # this might not work on Windows. We should test it and -- if necessary --
    # change this to '\n'.
    delimiter = os.linesep

    def __init__(self, messageHub):
        # For some reason calling LineReceiver.__init__ doesn't work??

        self.hub = messageHub
        self.hub.stdioReady(self)

    def cleanup(self):
        pass

    def lineReceived(self, line):
        self.hub.stdioMessage(line)

    def backendMessage(self, message):
        # TODO: Eww... mixing log, print, *and* stdio.sendLine?
        self.sendLine("[receive] {}".format(message))

