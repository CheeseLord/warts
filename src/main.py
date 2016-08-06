import argparse
import sys

from server.main import main as serverMain
from client.main import main as clientMain

HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = "50000"


def main():
    args = parseArguments()

    if args.command == "server":
        print "Running WaRTS server..."
        serverMain(args)

    elif args.command == "client":
        print "Connecting to WaRTS server..."
        clientMain(args)

    else:
        # This should be impossible, because argparse should prevent it.
        print "Internal error: unrecognized command '{}'".format(args.command)


def parseArguments():
    parser = WartsParser()
    subparsers = parser.add_subparsers(title="commands",
        metavar="List of commands")

    # Server command
    server_parser = subparsers.add_parser("server", help="Run a WaRTS server")
    server_parser.set_defaults(command="server")
    server_parser.add_argument(
        '--port', type=int, nargs='?', default=PORT_DEFAULT,
        help="server port [Default: %(default)s]")

    # Server command
    client_parser = subparsers.add_parser("client",
        help="connect to a WaRTS server")
    client_parser.set_defaults(command="client")
    client_parser.add_argument(
        '--host', type=str, nargs='?', default=HOST_DEFAULT,
        help="server hostname [Default: %(default)s]")
    client_parser.add_argument(
        '--port', type=int, nargs='?', default=PORT_DEFAULT,
        help="server port [Default: %(default)s]")

    return parser.parse_args()


class WartsParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: {message}\n".format(message=message))
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

