import logging

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def setupNetworking(reactor, backend, host, port):
    factory = NetworkConnectionFactory(backend)
    reactor.connectTCP(host, port, factory)


class NetworkConnectionFactory(ClientFactory):
    def __init__(self, backend):
        self.backend = backend
        self.alreadyConnected = False

    def clientConnectionFailed(self, connector, reason):
        log.error("Failed to connect to server: {}" . \
            format(reason.getErrorMessage()))

    def clientConnectionLost(self, connector, reason):
        log.info("Disconnected from server: {}" . \
            format(reason.getErrorMessage()))

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
        log.info("Connected to server.")

        self.backend.networkReady(self)

    def stringReceived(self, message):
        log.info("[receive] {}".format(message))
        self.backend.networkMessage(message)

    def backendMessage(self, message):
        log.info("[send]    {}".format(message))
        self.sendString(message)

