import os

from twisted.internet import stdio as twistedStdio
from twisted.protocols.basic import LineReceiver

def setupStdio(reactor):
    twistedStdio.StandardIO(StdioHandler())

class StdioHandler(LineReceiver):
    # The default delimiter for a LineReceiver is '\r\n', which doesn't work
    # with Python's stdin (at least on *nix, probably on Windows as well) which
    # uses either '\n' or os.linesep instead.
    # TODO: I'm actually not sure which separator Python uses on Windows, so
    # this might not work on Windows. We should test it and -- if necessary --
    # change this to '\n'.
    delimiter = os.linesep

    def lineReceived(self, line):
        print line

