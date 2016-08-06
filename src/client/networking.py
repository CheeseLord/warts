from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver


def setupNetworking(reactor, done, host, port):
    factory = FactoryForConnectionsToServer()
    reactor.connectTCP(host, port, factory)


class FactoryForConnectionsToServer(ClientFactory):
    def clientConnectionFailed(self, connector, reason):
        print "Failed to connect to server: {}" . \
            format(reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        print "Disconnected from server: {}" . \
            format(reason.getErrorMessage())

    def buildProtocol(self, serverAddress):
        # TODO: If this is called twice, give an error.
        serverConnection = ConnectionToServer(self, serverAddress)
        return serverConnection


class ConnectionToServer(Int16StringReceiver):
    def __init__(self, factory, serverAddress):
        # For some reason calling Int16StringReceiver.__init__ doesn't work??

        self.factory = factory
        self.address = serverAddress

    def connectionMade(self):
        print "Connected to server."

        self.sendString("Hello, server!")

    def stringReceived(self, message):
        print "[receive] {}".format(message)

