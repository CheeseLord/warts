from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver


class Echo(Int16StringReceiver):
    def __init__(self, position):
        self.position = position

    def stringReceived(self, data):
        peer = self.transport.getPeer()

        self.updatePosition(data)
        print "[{ip}:{port}] '{msg}'".format(ip=peer.host, port=peer.port,
                                             msg=data)
        self.sendString(data)
        self.sendString('Player position is now {0}'.format(self.position))
        # self.transport.loseConnection()

    def updatePosition(self, data):
        command = data.lower().strip()

        oldX, oldY = self.position
        updateX, updateY = {
            'n':       [    0,     1],
            'north':   [    0,     1],
            's':       [    0,    -1],
            'south':   [    0,    -1],
            'e':       [    1,     0],
            'east':    [    1,     0],
            'west':    [   -1,     0],
            'start9':  [-oldX, -oldY],
        }.get(command, [    0,     0])
        
        self.position[0] += updateX
        self.position[1] += updateY

class EchoFactory(protocol.Factory):
    def __init__(self, *args, **kwargs):
        # TODO: Use a real object with real methods here.
        self.position = [0, 0]

    def buildProtocol(self, addr):
        return Echo(self.position)


def runEchoServer():
    endpoints.serverFromString(reactor, 'tcp:50000').listen(EchoFactory())
    reactor.run()
