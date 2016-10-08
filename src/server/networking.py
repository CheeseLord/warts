from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import buildMessage

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


class ConnectionManager:
    def __init__(self):
        # Mapping from player indices to connection objects.
        self.connections = {}
        # TODO: Don't let the ID grow forever.
        self.nextId      = 0

        self.commandHandler = None

    # Must be called immediately after __init__, before any other methods.
    def setCommandHandler(self, commandHandler):
        self.commandHandler = commandHandler

    def newConnection(self, *args):
        connection = NetworkConnection(self.nextId, self.commandHandler, self)
        self.connections[self.nextId] = connection
        self.nextId += 1
        return connection

    def removeConnection(self, connection):
        if connection.playerId in self.connections:
            del self.connections[connection.playerId]
            self.commandHandler.removeConnection(connection.playerId)
            log.info("{} connections remain.".format(len(self.connections)))
        else:
            log.warning("Failed to remove connection.")

    def broadcastMessage(self, message):
        self._broadcastString(message.serialize())

    def sendMessage(self, playerId, message):
        self._sendString(playerId, message.serialize())

    # Low-level string sending methods; don't call these directly.
    def _broadcastString(self, data):
        for connection in self:
            connection.sendString(data)

    def _sendString(self, playerId, data):
        self.connections[playerId].sendString(data)

    def __iter__(self):
        # Iterate over all connections, in ascending order by ID.
        for playerId in sorted(self.connections.keys()):
            yield self.connections[playerId]


class NetworkConnection(Int16StringReceiver):
    def __init__(self, playerId, commandHandler, connections):
        self.playerId = playerId
        self.connections = connections
        self.commandHandler = commandHandler

    def connectionMade(self):
        peer = self.transport.getPeer()
        self.commandHandler.createConnection(self.playerId)

        # TODO: Create a common method for doing all these prefixed logs?
        log.info(
            "[{ip}:{port}] <new connection with id {playerId}>".format(
                ip       = peer.host,
                port     = peer.port,
                playerId = self.playerId,
            )
        )

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        self.connections.removeConnection(self)

        log.info(
            "[{ip}:{port}] <connection {playerId} lost: {reason}>".format(
                ip       = peer.host,
                port     = peer.port,
                playerId = self.playerId,
                reason   = reason.getErrorMessage(),
            )
        )

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        self.commandHandler.stringReceived(self.playerId, data)

        log.info("[{ip}:{port}] {msg!r}".format(
            ip=peer.host,
            port=peer.port,
            msg=data)
        )

    def sendMessage(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self.sendString(message)
