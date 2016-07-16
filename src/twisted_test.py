import argparse
import sys

from test_echoserver import runEchoServer
from test_echoclient import runEchoClient

def runTwistedTest():
    args = parseArguments()

    if args.isServer:
        print "Running echo server..."
        runEchoServer()
    else:
        print "Connecting to server..."
        runEchoClient(args.host, args.port)


def parseArguments():
    parser = argparse.ArgumentParser()

    # Are we the server or the client?
    parser.add_argument('--server', dest='isServer', action='store_true',
                        default=False)
    parser.add_argument('--client', dest='isServer', action='store_false')

    # Server parameters, if we're the client.
    parser.add_argument('--host', type=str, nargs='?', default="127.0.0.1")
    parser.add_argument('--port', type=int, nargs='?', default=50000)

    return parser.parse_args()
