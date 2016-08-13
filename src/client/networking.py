from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver


def setupNetworking(reactor, hub, host, port):
    factory = FactoryForConnectionsToServer(hub)
    reactor.connectTCP(host, port, factory)


class FactoryForConnectionsToServer(ClientFactory):
    def __init__(self, messageHub):
        self.hub = messageHub
        self.alreadyConnected = False

    def clientConnectionFailed(self, connector, reason):
        print "Failed to connect to server: {}" . \
            format(reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        print "Disconnected from server: {}" . \
            format(reason.getErrorMessage())

    def buildProtocol(self, serverAddress):
        assert not self.alreadyConnected
        self.alreadyConnected = True
        serverConnection = ConnectionToServer(self.hub, self, serverAddress)
        return serverConnection


class ConnectionToServer(Int16StringReceiver):
    def __init__(self, messageHub, factory, serverAddress):
        # For some reason calling Int16StringReceiver.__init__ doesn't work??

        self.hub     = messageHub
        self.factory = factory
        self.address = serverAddress

    def onAllReady(self):
        pass

    def onClientQuit(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print "Connected to server."

        self.sendString("Hello, server!")

        self.hub.onNetworkReady(self)

    def stringReceived(self, message):
        self.hub.recvNetwork(message)

    def messageFromStdio(self, message):
        # TODO: Eww... mixing log, print, *and* stdio.sendLine?
        print "[send]    {}".format(message)
        self.sendString(message)

