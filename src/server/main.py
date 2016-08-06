from src.shared.dummy import sharedFunctionality
from src.server.networking import runServer

def main(args):
    print "Hi, I'm a server!"
    sharedFunctionality()
    runServer(args.port)
