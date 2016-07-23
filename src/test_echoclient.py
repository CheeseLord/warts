import os

from twisted.internet import task, stdio, reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver, LineReceiver


theClient = None


class EchoClient(Int16StringReceiver):
    def __init__(self, onClientConnect):
        # Apparently Int16StringReceiver doesn't have an __init__.
        # Int16StringReceiver.__init__(self)

        self.onClientConnect = onClientConnect

    def connectionMade(self):
        self.onClientConnect.callback(self)
        # self.sendString("Hello, world!")

    def stringReceived(self, line):
        # TODO: Probably this should go through the StdioHandler rather than
        # calling print directly....
        print "[receive]", line



class EchoClientFactory(ClientFactory):
    protocol = EchoClient

    def __init__(self, onClientConnect):
        self.done = Deferred()
        self.onClientConnect = onClientConnect

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason.getErrorMessage()
        self.done.errback(reason)

    def clientConnectionLost(self, connector, reason):
        print "connection lost:", reason.getErrorMessage()
        self.done.callback(None)

    def buildProtocol(self, addr):
        # TODO Add more logic to prevent this from happening twice??
        return self.protocol(self.onClientConnect)


class StdioHandler(LineReceiver):
    delimiter = os.linesep

    def __init__(self, onClientConnect):
        onClientConnect.addCallback(self.connectedToServer)
        # TODO: Should maybe have an errback as well?

        self.client = None

    def connectedToServer(self, client):
        self.client = client
        print "Successfully connected to server; you may now type messages."

    def connectionMade(self):
        self.sendLine("Stdio handler created, yay!")

    def lineReceived(self, line):
        if self.client is not None:
            self.client.sendString(line)
            self.sendLine("[send]    {}".format(line))
        else:
            self.sendLine("[warning] message '{}' ignored; not connected to " \
                          "server.".format(line))

def runEchoClientHelper(reactor, host, port):
    onClientConnect = Deferred()

    stdio.StandardIO(StdioHandler(onClientConnect))
    factory = EchoClientFactory(onClientConnect)
    reactor.connectTCP(host, port, factory)
    return factory.done

def runEchoClient(host, port):
    task.react(runEchoClientHelper, (host, port))

