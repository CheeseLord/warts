import math

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

    def buildProtocol(self, addr):
        return Echo(self.position)


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

        if command == 'start9':
            self.position[0] = 0.0
            self.position[1] = 0.0

        elif command in self.RELATIVE_MOVES:
            updateX, updateY = self.RELATIVE_MOVES[command]
            self.position[0] += updateX
            self.position[1] += updateY

        else:
            try:
                updateX, updateY = map(float, command.split())
            except:
                # FIXME: Don't just do except: pass
                pass
            else:
                if isfinite(updateX) and isfinite(updateY):
                    self.position[0] = updateX
                    self.position[1] = updateY

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)
