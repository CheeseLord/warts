from twisted.internet import task
from twisted.internet.defer import Deferred

from src.shared.dummy import sharedFunctionality

from src.client.networking import setupNetworking
from src.client.stdio      import setupStdio

def main(args):
    print "Hi, I'm a client!"
    sharedFunctionality()

    # TODO: Where do we put this call, which starts the Twisted event loop?
    task.react(twistedMain, (args,))


def twistedMain(reactor, args):
    # Fire this deferred's callback to exit cleanly.
    # TODO: Actually use this deferred. The call to task.react which kicks off
    # the event loop will log any failures from this Deferred, so we may be
    # able to use it for reporting errors.
    done = Deferred()

    setupNetworking(reactor, done, args.host, args.port)
    setupStdio(reactor)

    return done

