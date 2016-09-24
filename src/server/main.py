from src.server.command_handler import CommandHandler
from src.server.networking import runServer, ConnectionManager

def main(args):
    connections = ConnectionManager()
    commandHandler = CommandHandler(connections)
    connections.setCommandHandler(commandHandler)

    runServer(args.port, connections)
