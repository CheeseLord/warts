from src.parsing_utils import parseFloatTuple

from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver


def runEchoServer(port):
    serverString = "tcp:{}".format(port)
    server = endpoints.serverFromString(reactor, serverString)
    server.listen(EchoFactory())
    reactor.run()


class EchoFactory(protocol.Factory):
    def __init__(self, *args, **kwargs):
        # TODO: Use a real object with real methods here.
        self.position = [0, 0]
        self.connections = []

    def buildProtocol(self, addr):
        newConnection = Echo(self, self.position)
        self.connections.append(newConnection)
        return newConnection

    def removeConnection(self, connection):
        foundOne = False
        for i in range(len(self.connections)):
            if self.connections[i] is connection:
                foundOne = True
                del self.connections[i]
                break

        if not foundOne:
            print "Warning: failed to remove connection."

    def broadcastString(self, data):
        for connection in self.connections:
            connection.sendString(data)


class Echo(Int16StringReceiver):
    STEP_SIZE = 1.0
    RELATIVE_MOVES = {
        'n':       ( 0.0,        STEP_SIZE),
        'north':   ( 0.0,        STEP_SIZE),
      # 'up':      ( 0.0,        STEP_SIZE),
        's':       ( 0.0,       -STEP_SIZE),
        'south':   ( 0.0,       -STEP_SIZE),
      # 'down':    ( 0.0,       -STEP_SIZE),
        'e':       ( STEP_SIZE,        0.0),
        'east':    ( STEP_SIZE,        0.0),
      # 'right':   ( STEP_SIZE,        0.0),
        'w':       (-STEP_SIZE,        0.0),
        'west':    (-STEP_SIZE,        0.0),
      # 'left':    (-STEP_SIZE,        0.0),
    }

    def __init__(self, factory, position):
        self.factory = factory
        self.position = position

    def connectionMade(self):
        peer = self.transport.getPeer()
        print "[{ip}:{port}] <new connection>".format(
            ip=peer.host, port=peer.port)
        print "    {} connections in total.".format(
            len(self.factory.connections))

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        print "[{ip}:{port}] <connection lost: {reason}>".format(
            ip=peer.host, port=peer.port, reason=reason.getErrorMessage())
        self.factory.removeConnection(self)
        print "    {} connections remain.".format(
            len(self.factory.connections))

    def stringReceived(self, data):
        peer = self.transport.getPeer()

        self.updatePosition(data)
        print "[{ip}:{port}] '{msg}'".format(ip=peer.host, port=peer.port,
                                             msg=data)
        # self.sendString(data)
        # self.sendString('Player position is now {0}'.format(self.position))
        x, y = self.position
        self.broadcastString("{x} {y}".format(x=x, y=y))

    def updatePosition(self, data):
        command = data.lower().strip()

        if command == 'start9':
            self.position[0] = 0.0
            self.position[1] = 0.0

        elif command in self.RELATIVE_MOVES:
            updateX, updateY = self.RELATIVE_MOVES[command]
            self.position[0] += updateX
            self.position[1] += updateY

        else:
            updates = parseFloatTuple(command, 2)
            if updates:
                self.position[0] = updates[0]
                self.position[1] = updates[1]


    def broadcastString(self, data):
        self.factory.broadcastString(data)

