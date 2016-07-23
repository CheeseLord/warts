#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function

import os

from twisted.internet import task, stdio, reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int16StringReceiver, LineReceiver


theClient = None


class EchoClient(Int16StringReceiver):
    def __init__(self):
        # Apparently Int16StringReceiver doesn't have an __init__.
        # Int16StringReceiver.__init__(self)

        # FIXME FIXME FIXME: This is a terrible hack, which doesn't even quite
        # work. If you type something before we've finished connecting, then
        # the stdio handler will try to send it using theClient even though
        # theClient isn't actually initialized yet, so you'll get:
        #     AttributeError: 'NoneType' object has no attribute 'sendString'
        # Really I think we should be setting up a deferred that waits to
        # create the stdio handler until the client object is already created,
        # so that the stdio handler can safely reference the client object from
        # the start. But I'm not really sure how to do that, so for now we get
        # this hack instead.
        global theClient
        theClient = self

    def connectionMade(self):
        pass
        # self.sendString("Hello, world!")

    def stringReceived(self, line):
        # TODO: Probably this should go through the StdioHandler rather than
        # calling print directly....
        print("[receive]", line)



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
        self.sendLine("Stdio handler created, yay!")

    def lineReceived(self, line):
        theClient.sendString(line)
        self.sendLine("[send]    {}".format(line))


def runEchoClientHelper(reactor, host, port):
    factory = EchoClientFactory()
    reactor.connectTCP(host, port, factory)
    stdio.StandardIO(StdioHandler())
    return factory.done

def runEchoClient(host, port):
    task.react(runEchoClientHelper, (host, port))

