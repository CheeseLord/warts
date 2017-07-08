from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.logconfig import newLogger
from src.shared import messages

log = newLogger(__name__)


def runServer(port, connections):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(NetworkConnectionFactory(connections))
    reactor.run()


class NetworkConnectionFactory(protocol.Factory):
    def __init__(self, connections):
        # Parent class has no init so we cannot call it
        self.connections = connections

    def buildProtocol(self, addr):
        # Oddly, addr isn't actually used here, except for logging.
        newConnection = self.connections.newConnection()
        return newConnection


class ConnectionManager(object):
    def __init__(self):
        # Mapping from player indices to connection objects.
        self.connections = {}
        # TODO: Don't let the ID grow forever.
        self.nextId      = 0

        self.gameStateManager = None

    # Must be called immediately after __init__, before any other methods.
    def setGameStateHandler(self, gameStateManager):
        self.gameStateManager = gameStateManager

    def newConnection(self, *args):
        connection = NetworkConnection(self.nextId, self.gameStateManager,
                                       self)
        self.connections[self.nextId] = connection
        self.nextId += 1
        return connection

    def removeConnection(self, connection):
        if connection.playerId in self.connections:
            del self.connections[connection.playerId]
            self.gameStateManager.removeConnection(connection.playerId)
        else:
            log.warning("Failed to remove connection.")

    def reportRemainingConnections(self):
        log.info("%s connections remain.", len(self.connections))

    def broadcastMessage(self, message):
        for connection in self:
            connection.sendMessage(message)

    def sendMessage(self, playerId, message):
        self.connections[playerId].sendMessage(message)

    def __iter__(self):
        # Iterate over all connections, in ascending order by ID.
        for playerId in sorted(self.connections.keys()):
            yield self.connections[playerId]


class NetworkConnection(Int16StringReceiver):
    def __init__(self, playerId, gameStateManager, connections):
        self.playerId = playerId
        self.connections = connections
        self.gameStateManager = gameStateManager

    def connectionMade(self):
        peer = self.transport.getPeer()

        self.handshake()
        self.gameStateManager.handshake(self.playerId)

        # TODO: Create a common method for doing all these prefixed logs?
        log.info("[%s:%s] <new connection with id %s>",
                 peer.host, peer.port, self.playerId)

    def handshake(self):
        self.sendMessage(messages.YourIdIs(self.playerId))

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        self.connections.removeConnection(self)

        log.info("[%s:%s] <connection %s lost: %s>",
                 peer.host, peer.port, self.playerId, reason.getErrorMessage())

        self.connections.reportRemainingConnections()

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        self.gameStateManager.stringReceived(self.playerId, data)

        log.info("[%s:%s] %r", peer.host, peer.port, data)

    def sendMessage(self, message):
        self.sendString(message.serialize())
