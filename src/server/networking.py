from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

import logging

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
        log.info("[{ip}:{port}] '{msg}'".format(
            ip=peer.host,
            port=peer.port,
            msg=data)
        )

        self.updatePosition(data)

    def broadcastString(self, data):
        self.factory.broadcastString(data)

    def updatePosition(self, data):
        processed = data.strip().lower()

        step = {
            'n': [ 0,  1],
            's': [ 0, -1],
            'e': [ 1,  0],
            'w': [-1,  0],
        }.get(processed, [0, 0])

        self.playerPosition[0] += step[0]
        self.playerPosition[1] += step[1]

        self.broadcastString('Player position is now {}'
                             .format(self.playerPosition))
