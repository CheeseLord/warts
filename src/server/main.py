from twisted.internet.task import LoopingCall
from twisted.python import log as twistedLog

from src.server.command_handler import CommandHandler
from src.server.networking import runServer, ConnectionManager

def main(args):
    connections = ConnectionManager()
    commandHandler = CommandHandler(connections)
    connections.setCommandHandler(commandHandler)

    # For now, apply orders very infrequently so we can clearly see the lag.
    loop = LoopingCall(commandHandler.applyOrders)
    deferred = loop.start(1.0)
    deferred.addErrback(twistedLog.err)

    runServer(args.port, connections)
