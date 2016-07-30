import os

from twisted.internet import task, stdio, reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver, LineReceiver
from twisted.python import log

from twisted.internet.task import LoopingCall

import panda_test
from src.parsing_utils import parseFloatTuple


DESIRED_FPS = 60


def runEchoClient(host, port):
    task.react(runEchoClientHelper, (host, port))


def runEchoClientHelper(reactor, host, port):
    onClientConnect = Deferred()

    # Setup callbacks for when we finish connecting to the server.
    stdio.StandardIO(StdioHandler(onClientConnect))
    onClientConnect.addCallback(startPanda)

    # Setup the EchoClientFactory to connect to the server and create an
    # EchoClient.
    factory = EchoClientFactory(onClientConnect)
    reactor.connectTCP(host, port, factory)

    # Setup an errback in case any of the callbacks we set above fail.
    # This needs to be done after all the callbacks; if you add callbacks after
    # you've added an errback, it looks like that errback doesn't actually get
    # called to handle errors in those later callbacks.
    onClientConnect.addErrback(log.err)

    return factory.done


def startPanda(client):
    app = panda_test.WartsApp(client)
    client.setApp(app)

    LoopingCall(taskMgr.step).start(1.0 / DESIRED_FPS)

    return client


class StdioHandler(LineReceiver):
    delimiter = os.linesep

    def __init__(self, onClientConnect):
        onClientConnect.addCallback(self.connectedToServer)

        self.client = None

    def connectedToServer(self, client):
        self.client = client
        print "Successfully connected to server; you may now type messages."
        return client

    def connectionMade(self):
        self.sendLine("Stdio handler created, yay!")

    def lineReceived(self, line):
        if self.client is not None:
            self.client.sendString(line)
            self.sendLine("[send]    {}".format(line))
        else:
            self.sendLine("[warning] message '{}' ignored; not connected to " \
                          "server.".format(line))


class EchoClientFactory(ClientFactory):
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
        client = EchoClient(self.onClientConnect)
        client.factory = self
        return client


class EchoClient(Int16StringReceiver):
    def __init__(self, onClientConnect):
        # Apparently Int16StringReceiver doesn't have an __init__.
        # Int16StringReceiver.__init__(self)

        self.onClientConnect = onClientConnect
        self.app = None

    def setApp(self, app):
        self.app = app

    def connectionMade(self):
        self.onClientConnect.callback(self)
        # self.sendString("Hello, world!")

    def stringReceived(self, line):
        # TODO: Probably this should go through the StdioHandler rather than
        # calling print directly....
        position = parseFloatTuple(line, 2)
        if position:
            self.app.setTestModelPos(position[0], position[1])
        print "[receive]", line
