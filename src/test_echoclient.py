#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver
import argparse



class EchoClient(Int16StringReceiver):
    end = "Bye-bye!"

    def connectionMade(self):
        self.sendString("Hello, world!\n")
        self.sendString("What a fine day it is.\n")
        self.sendString("\n")


    def stringReceived(self, line):
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


def runEchoClientHelper(reactor, host, port):
    factory = EchoClientFactory()
    reactor.connectTCP(host, port, factory)
    return factory.done

def runEchoClient(host, port):
    task.react(runEchoClientHelper, (host, port))

