import logging
from src.shared.message import buildMessage

from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.encode import decodePosition, encodePosition

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def runServer(port):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(NetworkConnectionFactory())
    reactor.run()


class NetworkConnectionFactory(protocol.Factory):
    def __init__(self, *args, **kwargs):
        self.connections = ConnectionManager()

        # TODO: Create GameState object.
        self.playerPositions = {}

    def buildProtocol(self, addr):
        # Oddly, addr isn't actually used here, except for logging.
        newConnection = self.connections.newConnection(self.connections,
                                                       self.playerPositions)
        # TODO: Can this log be moved into NetworkConnection?
        log.info("New Connection from {}".format(addr))
        return newConnection


class ConnectionManager:
    def __init__(self):
        # Mapping from player indices to connection objects.
        self.connections = {}

        # TODO: Don't let the index grow forever.
        self.nextIndex   = 0

    def newConnection(self, *args):
        connection = NetworkConnection(self.nextIndex, *args)
        self.connections[self.nextIndex] = connection
        self.nextIndex += 1
        return connection

    def removeConnection(self, connection):
        if connection.playerIndex in self.connections:
            del self.connections[connection.playerIndex]
            log.info(
                "{} connections remain".format(len(self.connections))
            )
            self.broadcastMessage("delete_obelisk", [connection.playerIndex])
        else:
            log.warning("Failed to remove connection.")

    def broadcastMessage(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self._broadcastString(message)

    def sendMessage(self, index, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self._sendString(index, message)

    # Low-level string sending methods; don't call these directly.
    def _broadcastString(self, data):
        for connection in self:
            connection.sendString(data)

    def _sendString(self, index, data):
        self.connections[index].sendString(data)

    def __iter__(self):
        # Iterate over all connections, in ascending order by index.
        for index in sorted(self.connections.keys()):
            yield self.connections[index]


class NetworkConnection(Int16StringReceiver):
    def __init__(self, playerIndex, connections, playerPositions):
        self.playerIndex = playerIndex
        self.connections = connections
        self.playerPositions = playerPositions

        self.playerPositions[self.playerIndex] = (0, 0)

    def connectionMade(self):
        # TODO: This line has no effect...
        # peer = self.transport.getPeer()

        myId = self.playerIndex
        myX, myY = self.playerPositions[self.playerIndex]

        self.sendMessage("your_id_is", [myId])
        self.connections.broadcastMessage("new_obelisk", [myId, myX, myY])
        for otherId, (otherX, otherY) in self.playerPositions.items():
            if otherId == myId:
                # We already broadcast this one to everyone, including ourself.
                continue
            self.sendMessage("new_obelisk", [otherId, otherX, otherY])

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        log.info(
            "[{ip}:{port}] <connection lost: {reason}>".format(
                ip=peer.host,
                port=peer.port,
                reason=reason.getErrorMessage()
            )
        )
        self.connections.removeConnection(self)
        del self.playerPositions[self.playerIndex]

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        log.info("[{ip}:{port}] {msg!r}".format(
            ip=peer.host,
            port=peer.port,
            msg=data)
        )

        self.updatePosition(data)

    def sendMessage(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self.sendString(message)

    def updatePosition(self, data):
        command = data.strip().lower()

        STEP_SIZE = 1.0
        RELATIVE_MOVES = {
            'n': [ 0.0,        STEP_SIZE],
            's': [ 0.0,       -STEP_SIZE],
            'e': [ STEP_SIZE,        0.0],
            'w': [-STEP_SIZE,        0.0],
        }

        if command in RELATIVE_MOVES:
            x, y = self.playerPositions[self.playerIndex]
            dx, dy = RELATIVE_MOVES[command]
            self.playerPositions[self.playerIndex] = (x + dx, y + dy)

        else:
            newPos = decodePosition(command)
            if newPos is not None:
                self.playerPositions[self.playerIndex] = newPos

        # TODO: Maybe only broadcast the new position if we handled a valid
        # command? Else the position isn't changed....
        myId = self.playerIndex
        myX, myY = self.playerPositions[self.playerIndex]
        self.connections.broadcastMessage("set_pos", [myId, myX, myY])
