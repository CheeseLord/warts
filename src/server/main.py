from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared import config
from src.server.game_state_manager import GameStateManager
from src.server.networking import runServer, ConnectionManager
from src.server.stdio import setupStdio

def unhandledError(reason):
    twistedLog.err(reason, "Aborting due to unhandled error.")
    reactor.stop()

def main(args):
    connections = ConnectionManager()
    gameStateManager = GameStateManager(connections)
    connections.setGameStateHandler(gameStateManager)
    setupStdio(gameStateManager)

    loop = LoopingCall(gameStateManager.tick)
    deferred = loop.start(config.TICK_LENGTH)
    deferred.addErrback(unhandledError)

    runServer(args.port, connections)

