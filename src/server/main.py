from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.shared import config
from src.server.command_handler import CommandHandler
from src.server.networking import runServer, ConnectionManager

def main(args):
    connections = ConnectionManager()
    commandHandler = CommandHandler(connections)
    connections.setCommandHandler(commandHandler)

    loop = LoopingCall(commandHandler.applyOrders)
    deferred = loop.start(config.TICK_LENGTH)
    deferred.addErrback(twistedLog.err)

    runServer(args.port, connections)
