import argparse
import sys

from src.shared.logconfig import enableDebugLogging
from src.server.main import main as serverMain
from src.client.main import main as clientMain

HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = "16097"


def main():
    args = parseArguments()

    handleSharedArguments(args)

    if args.command == "server":
        print "Running WaRTS server..."
        serverMain(args)

    elif args.command == "client":
        print "Connecting to WaRTS server..."
        clientMain(args)

    else:
        # This should be impossible, because argparse should prevent it.
        print "Internal error: unrecognized command '{}'".format(args.command)


def handleSharedArguments(args):
    if args.log_debug:
        enableDebugLogging()

def parseArguments():
    parser = WartsParser()

    parser.add_argument('--log-debug', action="store_true",
                        help="Enable debug-level logging")

    subparsers = parser.add_subparsers(title="commands")

    # Server command
    serverParser = subparsers.add_parser("server", help="Run a WaRTS server")
    serverParser.set_defaults(command="server")
    serverParser.add_argument('--port', type=int, nargs='?',
                              default=PORT_DEFAULT,
                              help="server port [Default: %(default)s]")
    serverParser.add_argument('--log-debug', action="store_true",
                              help="Enable debug-level logging")

    # Server command
    clientParser = subparsers.add_parser("client",
                                         help="connect to a WaRTS server")
    clientParser.set_defaults(command="client")
    clientParser.add_argument('--host', type=str, nargs='?',
                              default=HOST_DEFAULT,
                              help="server hostname [Default: %(default)s]")
    clientParser.add_argument('--port', type=int, nargs='?',
                              default=PORT_DEFAULT,
                              help="server port [Default: %(default)s]")
    clientParser.add_argument('--log-debug', action="store_true",
                              help="Enable debug-level logging")

    return parser.parse_args()


class WartsParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: {message}\n".format(message=message))
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

