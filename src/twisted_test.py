from twisted.internet import protocol, reactor, endpoints


class Echo(protocol.Protocol):
    def dataReceived(self, data):
        peer = self.transport.getPeer()
        print "[{ip}:{port}] '{msg}'".format(ip=peer.host, port=peer.port,
                                             msg=data)
        self.transport.write(data)
        self.transport.loseConnection()


class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()


def runTwistedTest():
    endpoints.serverFromString(reactor, 'tcp:50000').listen(EchoFactory())
    reactor.run()
