#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
import argparse



class EchoClient(LineReceiver):
    end = "Bye-bye!"

    def connectionMade(self):
        self.sendLine("Hello, world!")
        self.sendLine("What a fine day it is.")
        self.sendLine(self.end)


    def lineReceived(self, line):
        print("receive:", line)
        if line == self.end:
            self.transport.loseConnection()



class EchoClientFactory(ClientFactory):
    protocol = EchoClient

    def __init__(self):
        self.done = Deferred()


    def clientConnectionFailed(self, connector, reason):
        print('connection failed:', reason.getErrorMessage())
        self.done.errback(reason)


    def clientConnectionLost(self, connector, reason):
        print('connection lost:', reason.getErrorMessage())
        self.done.callback(None)



def main(reactor):
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--host', type=str, nargs='?', default="127.0.0.1")
    parser.add_argument('--port', type=int, nargs='?', default=50000)
    args = parser.parse_args()
    factory = EchoClientFactory()
    reactor.connectTCP(args.host, args.port, factory)
    return factory.done



if __name__ == '__main__':
    task.react(main)
