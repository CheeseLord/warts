from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver


def setupNetworking(reactor, backend, host, port):
    factory = NetworkConnectionFactory(backend)
    reactor.connectTCP(host, port, factory)


class NetworkConnectionFactory(ClientFactory):
    def __init__(self, backend):
        self.backend = backend
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
        serverConnection = NetworkConnection(self.backend, self, serverAddress)
        return serverConnection


class NetworkConnection(Int16StringReceiver):
    def __init__(self, backend, factory, serverAddress):
        # For some reason calling Int16StringReceiver.__init__ doesn't work??

        self.backend = backend
        self.factory = factory
        self.address = serverAddress

    def cleanup(self):
        self.transport.loseConnection()

    def connectionMade(self):
        print "Connected to server."

        self.sendString("Hello, server!")

        self.backend.networkReady(self)

    def stringReceived(self, message):
        self.backend.networkMessage(message)

    def backendMessage(self, message):
        # TODO: Eww... mixing log, print, *and* stdio.sendLine?
        print "[send]    {}".format(message)
        self.sendString(message)

