from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.logconfig import newLogger
from src.shared import messages

log = newLogger(__name__)


def startServer(port, connections):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(NetworkConnectionFactory(connections))


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
        self.clientInterfacer = None

    # These next two methods must be called immediately after __init__, before
    # any other methods.
    def setGameStateManager(self, gameStateManager):
        self.gameStateManager = gameStateManager

    def setClientInterfacer(self, clientInterfacer):
        self.clientInterfacer = clientInterfacer

    def newConnection(self):
        connection = NetworkConnection(self.nextId, self.clientInterfacer,
                                       self)
        self.connections[self.nextId] = connection
        self.nextId += 1
        return connection

    def removeConnection(self, connection):
        if connection.playerId in self.connections:
            del self.connections[connection.playerId]
            self.gameStateManager.removePlayer(connection.playerId)
        else:
            log.warning("Failed to remove connection.")

    def reportRemainingConnections(self):
        log.info("%s connections remain.", len(self.connections))

    def broadcastMessage(self, message):
        for connection in self:
            connection.sendMessage(message)

    def sendMessage(self, playerId, message, dropOnFailure=False):
        if dropOnFailure and playerId not in self.connections:
            return
        self.connections[playerId].sendMessage(message)

    def __iter__(self):
        # Iterate over all connections, in ascending order by ID.
        for playerId in sorted(self.connections.keys()):
            yield self.connections[playerId]


class NetworkConnection(Int16StringReceiver):
    def __init__(self, playerId, clientInterfacer, connections):
        self.playerId = playerId
        self.connections = connections
        self.clientInterfacer = clientInterfacer

    def connectionMade(self):
        peer = self.transport.getPeer()

        self.handshake()
        self.clientInterfacer.handshake(self.playerId)

        # TODO: Create a common method for doing all these prefixed logs?
        log.info("[%s:%s] <new connection with id %s>",
                 peer.host, peer.port, self.playerId)

    def handshake(self):
        self.sendMessage(messages.YourIdIs(self.playerId))

    def connectionLost(self, reason=protocol.connectionDone):
        peer = self.transport.getPeer()
        self.connections.removeConnection(self)

        log.info("[%s:%s] <connection %s lost: %s>",
                 peer.host, peer.port, self.playerId, reason.getErrorMessage())

        self.connections.reportRemainingConnections()

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        self.clientInterfacer.stringReceived(self.playerId, data)

        log.info("[%s:%s] %r", peer.host, peer.port, data)

    def sendMessage(self, message):
        self.sendString(message.serialize())
