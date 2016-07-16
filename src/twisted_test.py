import argparse
import sys

from test_echoserver import runEchoServer
from test_echoclient import runEchoClient

def isServer(args):
    return args.command == "server"


def runTwistedTest():
    args = parseArguments()

    if isServer(args):
        print "Running echo server..."
        runEchoServer()
    else:
        print "Connecting to server..."
        runEchoClient(args.host, args.port)


def parseArguments():
    parser = argparse.ArgumentParser()

    # Positional arguements
    # Are we the server or the client?
    parser.add_argument('command', choices=["server", "client"])

    # Server parameters, if we're the client.
    parser.add_argument('--host', type=str, nargs='?', default="127.0.0.1")
    parser.add_argument('--port', type=int, nargs='?', default=50000)

    return parser.parse_args()
