#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function

import os

from twisted.internet import task, stdio, reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver, LineReceiver



class EchoClient(Int16StringReceiver):
    end = "Bye-bye!"

    def connectionMade(self):
        self.sendString("Hello, world!\n")
        self.sendString("What a fine day it is.\n")
        self.sendString(self.end + "\n")


    def stringReceived(self, line):
        print("receive:", line[:-1])
        # if line == self.end:
        #     self.transport.loseConnection()



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


class StdioHandler(LineReceiver):
    delimiter = os.linesep

    def connectionMade(self):
        self.sendLine("Connected, yay!")

    def lineReceived(self, line):
        self.sendLine("You typed: '{}'".format(line))


def runEchoClientHelper(reactor, host, port):
    factory = EchoClientFactory()
    reactor.connectTCP(host, port, factory)
    stdio.StandardIO(StdioHandler())
    return factory.done

def runEchoClient(host, port):
    task.react(runEchoClientHelper, (host, port))

