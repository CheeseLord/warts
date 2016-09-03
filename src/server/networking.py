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
        # Mapping from player indices to connection objects.
        self.connections = {}
        # self.connections = []

        # TODO: Don't let the index grow forever.
        self.playerIndex = 0
        self.playerPositions = {}

    def buildProtocol(self, addr):
        newConnection = NetworkConnection(self, self.playerIndex,
                                          self.playerPositions)
        self.connections[self.playerIndex] = newConnection
        self.playerIndex += 1
        log.info("New Connection from {}".format(addr))
        return newConnection

    def removeConnection(self, connection):
        if connection.playerIndex in self.connections:
            del self.connections[connection.playerIndex]
        else:
            log.warning("Failed to remove connection.")

    def sendString(self, index, data):
        self.connections[index].sendString(data)

    def broadcastString(self, data):
        for connection in self.connections.values():
            connection.sendString(data)


class NetworkConnection(Int16StringReceiver):
    def __init__(self, factory, playerIndex, playerPositions):
        self.factory = factory

        self.playerIndex = playerIndex
        self.playerPositions = playerPositions
        self.playerPositions[self.playerIndex] = (0, 0)

    def connectionMade(self):
        # TODO: This line has no effect...
        peer = self.transport.getPeer()

        myId = self.playerIndex
        myX, myY = self.playerPositions[self.playerIndex]

        self.sendCommand("your_id_is", [myId])
        self.broadcastCommand("new_obelisk", [myId, myX, myY])
        for otherId, (otherX, otherY) in self.playerPositions.items():
            if otherId == myId:
                continue
            self.sendCommand("new_obelisk", [otherId, otherX, otherY])

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        log.info(
            "[{ip}:{port}] <connection lost: {reason}>".format(
                ip=peer.host,
                port=peer.port,
                reason=reason.getErrorMessage()
            )
        )
        self.factory.removeConnection(self)
        log.info(
            "{} connections remain".format(len(self.factory.connections))
        )
        self.broadcastCommand("delete_obelisk", [self.playerIndex])

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        # self.factory.broadcastString(data)
        log.info("[{ip}:{port}] {msg!r}".format(
            ip=peer.host,
            port=peer.port,
            msg=data)
        )

        self.updatePosition(data)

    def sendCommand(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self.sendString(message)

    def broadcastCommand(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self.factory.broadcastString(message)

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
        self.broadcastCommand("set_pos", [myId, myX, myY])
