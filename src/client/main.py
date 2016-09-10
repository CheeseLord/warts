import logging

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared.logconfig import newLogger

from src.client.backend    import Backend
from src.client.networking import setupNetworking
from src.client.stdio      import setupStdio
from src.client.graphics   import WartsApp, DESIRED_FPS

log = newLogger(__name__)


def main(args):
    # TODO: Where do we put this call, which starts the Twisted event loop?
    task.react(twistedMain, (args,))


def twistedMain(reactor, args):
    # Fire this deferred's callback to exit cleanly.
    # Note: The call to task.react which kicks off the event loop will log any
    # failures from this Deferred, so we may also be able to use it for
    # reporting errors.
    done = Deferred()

    backend = Backend(done)
    setupStdio(backend)
    setupNetworking(reactor, backend, args.host, args.port)
    setupGraphics(reactor, backend)

    return done

def setupGraphics(reactor, backend):
    app = WartsApp(backend)

    def onGraphicsException(failure):
        # TODO: Change to logging
        print
        print "Shutting down client due to unhandled exception in graphics " \
            "code:"
        print
        # Supposedly I think we ought to be able to call
        # failure.printTraceback() here, but for some reason that doesn't print
        # anything.
        twistedLog.err(failure)
        reactor.stop()

    foo = LoopingCall(app.taskMgr.step).start(1.0 / DESIRED_FPS)
    foo.addErrback(onGraphicsException)

