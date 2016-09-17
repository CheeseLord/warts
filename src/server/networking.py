import logging

from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver

from src.shared.encode import decodePosition, encodePosition
from src.shared.gamestate import GameState
from src.shared.logconfig import newLogger
from src.shared.message import buildMessage

log = newLogger(__name__)


def runServer(port):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(NetworkConnectionFactory())
    reactor.run()


class NetworkConnectionFactory(protocol.Factory):
    def __init__(self, *args, **kwargs):
        # Parent class has no init so we cannot call it
        self.connections = ConnectionManager()
        self.gamestate   = GameState()

    def buildProtocol(self, addr):
        # Oddly, addr isn't actually used here, except for logging.
        newConnection = self.connections.newConnection(self.connections,
                                                       self.gamestate)
        return newConnection


class ConnectionManager:
    def __init__(self):
        # Mapping from player indices to connection objects.
        self.connections = {}

        # TODO: Don't let the ID grow forever.
        self.nextId   = 0

    def newConnection(self, *args):
        connection = NetworkConnection(self.nextId, *args)
        self.connections[self.nextId] = connection
        self.nextId += 1
        return connection

    def removeConnection(self, connection):
        if connection.playerId in self.connections:
            del self.connections[connection.playerId]
            log.info(
                "{} connections remain".format(len(self.connections))
            )
            self.broadcastMessage("delete_obelisk", [connection.playerId])
        else:
            log.warning("Failed to remove connection.")

    def broadcastMessage(self, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self._broadcastString(message)

    def sendMessage(self, playerId, *args, **kwargs):
        message = buildMessage(*args, **kwargs)
        self._sendString(playerId, message)

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
    def __init__(self, playerId, connections, gamestate):
        self.playerId = playerId
        self.connections = connections
        self.gamestate = gamestate

        self.gamestate.addPlayer(self.playerId, (0, 0))

    def connectionMade(self):
        peer = self.transport.getPeer()

        myId = self.playerId
        myX, myY = self.gamestate.getPos(myId)

        # TODO: Create a common method for doing all these prefixed logs?
        log.info(
            "[{ip}:{port}] <new connection with id {playerId}>".format(
                ip       = peer.host,
                port     = peer.port,
                playerId = myId,
            )
        )

        self.sendMessage("your_id_is", [myId])
        self.connections.broadcastMessage("new_obelisk", [myId, myX, myY])
        for otherConn in self.connections:
            otherId = otherConn.playerId
            if otherId == myId:
                # We already broadcast this one to everyone, including ourself.
                continue
            (otherX, otherY) = self.gamestate.getPos(otherId)
            self.sendMessage("new_obelisk", [otherId, otherX, otherY])

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        log.info(
            "[{ip}:{port}] <connection {playerId} lost: {reason}>".format(
                ip       = peer.host,
                port     = peer.port,
                playerId = self.playerId,
                reason   = reason.getErrorMessage(),
            )
        )
        self.connections.removeConnection(self)
        self.gamestate.removePlayer(self.playerId)

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
            self.gamestate.movePlayerBy(self.playerId,
                                        RELATIVE_MOVES[command])

        else:
            newPos = decodePosition(command)
            if newPos is not None:
                self.gamestate.movePlayerTo(self.playerId, newPos)

        # TODO: Maybe only broadcast the new position if we handled a valid
        # command? Else the position isn't changed....
        myId = self.playerId
        myX, myY = self.gamestate.getPos(self.playerId)
        self.connections.broadcastMessage("set_pos", [myId, myX, myY])
