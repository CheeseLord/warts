import logging

from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.encode import decodePosition, encodePosition

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def runServer(port):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(ChatFactory())
    reactor.run()


class ChatFactory(protocol.Factory):
    def __init__(self, *args, **kwargs):
        self.connections = []

        # TODO: Do this sanely.
        self.playerPosition = [0, 0]

    def buildProtocol(self, addr):
        newConnection = Chat(self, self.playerPosition)
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


class Chat(Int16StringReceiver):
    def __init__(self, factory, playerPosition):
        self.factory = factory

        self.playerPosition = playerPosition

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
        self.broadcastString(data)
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
            dx, dy = RELATIVE_MOVES[command]
            self.playerPosition[0] += dx
            self.playerPosition[1] += dy

        else:
            newPos = decodePosition(command)
            if newPos is not None:
                self.playerPosition[0] = newPos[0]
                self.playerPosition[1] = newPos[1]

        # TODO: Maybe only broadcast the new position if we handled a valid
        # command? Else the position isn't changed....
        self.broadcastString(encodePosition(self.playerPosition))
