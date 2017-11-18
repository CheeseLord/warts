from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared.logconfig import newLogger

from src.client.graphics_interface import GraphicsInterface
from src.client.backend     import Backend
from src.client.networking  import setupNetworking
from src.client.stdio       import setupStdio
from src.client.graphics    import WartsApp    as OldWartsApp, \
                                   DESIRED_FPS as OLD_DESIRED_FPS
from src.client.newgraphics import WartsApp    as NewWartsApp, \
                                   DESIRED_FPS as NEW_DESIRED_FPS

log = newLogger(__name__)


def main(args):
    if args.new_graphics:
        log.info("Using new graphics.")

    # TODO: Where do we put this call, which starts the Twisted event loop?
    task.react(twistedMain, (args,))


def twistedMain(reactor, args):
    # Fire this deferred's callback to exit cleanly.
    # Note: The call to task.react which kicks off the event loop will log any
    # failures from this Deferred, so we may also be able to use it for
    # reporting errors.
    done = Deferred()

    backend = Backend(done)
    graphicsInterface = GraphicsInterface(backend)
    setupStdio(backend)
    setupNetworking(reactor, backend, args.host, args.port)
    # TODO: Create gamestate here, pass it to both backend and (new) graphics.
    setupGraphics(reactor, graphicsInterface, backend.gameState,
                  args.new_graphics)

    return done

def setupGraphics(reactor, graphicsInterface, gameState, isNew):
    # Pylint doesn't like this, but I don't see a better way.
    # pylint:disable=redefined-variable-type
    if isNew:
        app = NewWartsApp(graphicsInterface, gameState)
    else:
        app = OldWartsApp(graphicsInterface)

    def onGraphicsException(failure):
        log.error("Shutting down client due to unhandled exception "
                  "in graphics code:")
        # TODO: Get traceback into regular log.
        # Supposedly I think we ought to be able to call
        # failure.printTraceback() here, but for some reason that doesn't print
        # anything.
        twistedLog.err(failure)
        reactor.stop()

    loop = LoopingCall(app.taskMgr.step)
    if isNew:
        deferred = loop.start(1.0 / NEW_DESIRED_FPS)
    else:
        deferred = loop.start(1.0 / OLD_DESIRED_FPS)
    deferred.addErrback(onGraphicsException)

