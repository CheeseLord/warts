from twisted.internet import protocol, reactor, endpoints
from twisted.protocols.basic import Int16StringReceiver


class Echo(Int16StringReceiver):
    def stringReceived(self, data):
        peer = self.transport.getPeer()
        print "[{ip}:{port}] '{msg}'".format(ip=peer.host, port=peer.port,
                                             msg=data)
        self.sendString(data)
        self.transport.loseConnection()


class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()


def runEchoServer():
    endpoints.serverFromString(reactor, 'tcp:50000').listen(EchoFactory())
    reactor.run()
