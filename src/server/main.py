from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared import config
from src.server.game_state_manager import GameStateManager
from src.server.networking import runServer, ConnectionManager

def main(args):
    connections = ConnectionManager()
    gameStateManager = GameStateManager(connections)
    connections.setGameStateHandler(gameStateManager)

    loop = LoopingCall(gameStateManager.applyOrders)
    deferred = loop.start(config.TICK_LENGTH)
    deferred.addErrback(twistedLog.err)

    runServer(args.port, connections)
