from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared import config
from src.server.backend import Backend
from src.server.client_interfacer import ClientInterfacer
from src.server.game_state_manager import GameStateManager
from src.server.networking import startServer, ConnectionManager
from src.server.stdio import setupStdio

def unhandledError(reason):
    twistedLog.err(reason, "Aborting due to unhandled error.")
    reactor.stop()

def main(args):
    connections = ConnectionManager()
    startServer(args.port, connections)

    # TODO: have a deferred for errors raised by the backend, like we do in the
    # client? Except I'm not sure if that deferred is actually doing anything.
    backend = Backend()
    gameStateManager = GameStateManager(backend, connections)
    clientInterfacer = ClientInterfacer(backend, gameStateManager, connections)
    setupStdio(backend)

    # TODO: Ugh.
    connections.setGameStateManager(gameStateManager)
    connections.setClientInterfacer(clientInterfacer)

    loop = LoopingCall(backend.tick)
    deferred = loop.start(config.TICK_LENGTH)
    deferred.addErrback(unhandledError)

    reactor.run()

