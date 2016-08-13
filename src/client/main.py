from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

from src.shared.dummy import sharedFunctionality

from src.client.message    import MessageHub
from src.client.networking import setupNetworking
from src.client.stdio      import setupStdio
from src.client.graphics   import WartsApp, DESIRED_FPS


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

    hub = MessageHub()
    setupStdio(hub)
    setupNetworking(reactor, hub, args.host, args.port)
    setupGraphics()

    return done

def setupGraphics():
    app = WartsApp()

    LoopingCall(app.taskMgr.step).start(1.0 / DESIRED_FPS)

