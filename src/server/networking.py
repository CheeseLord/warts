import logging

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
        self.connections = []

        # TODO: Don't let the index grow forever.
        self.playerIndex = 0
        self.playerPositions = {}

    def buildProtocol(self, addr):
        newConnection = NetworkConnection(self, self.playerIndex,
                                          self.playerPositions)
        self.playerIndex += 1
        self.connections.append(newConnection)
        log.info("New Connection from {}".format(addr))
        return newConnection

    def removeConnection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)
        else:
            log.warning("Failed to remove connection.")

    def broadcastString(self, data):
        for connection in self.connections:
            connection.sendString(data)


class NetworkConnection(Int16StringReceiver):
    def __init__(self, factory, playerIndex, playerPositions):
        self.factory = factory

        self.playerIndex = playerIndex
        self.playerPositions = playerPositions
        self.playerPositions[self.playerIndex] = (0, 0)

        self.broadcastString('your_id_is {id}'.format(id=self.playerIndex))

    def connectionMade(self):
        peer = self.transport.getPeer()

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

    def stringReceived(self, data):
        peer = self.transport.getPeer()
        # self.broadcastString(data)
        log.info("[{ip}:{port}] {msg!r}".format(
            ip=peer.host,
            port=peer.port,
            msg=data)
        )

        self.updatePosition(data)

    def broadcastString(self, data):
        self.factory.broadcastString(data)

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
        self.broadcastString(encodePosition(
            self.playerPositions[self.playerIndex]))
