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

    def buildProtocol(self, addr):
        newConnection = Chat(self)
        self.connections.append(newConnection)
        log.info("New Connection from {}".format(addr))
        return newConnection

    def removeConnection(self, connection):
        try:
            self.connections.remove(connection)
        except:
            log.warning("Failed to remove connection.")

    def broadcastString(self, data):
        for connection in self.connections:
            connection.sendString(data)


class Chat(Int16StringReceiver):
    def __init__(self, factory):
        self.factory = factory

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

    def broadcastString(self, data):
        self.factory.broadcastString(data)
