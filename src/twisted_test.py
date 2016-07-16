from twisted.internet import protocol, reactor, endpoints


class Echo(protocol.Protocol):
    def dataReceived(self, data):
        print data
        self.transport.write(data)
        self.transport.loseConnection()


class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()


def runTwistedTest():
    endpoints.serverFromString(reactor, 'tcp:50000').listen(EchoFactory())
    reactor.run()
