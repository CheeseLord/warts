from twisted.internet import task

from src.shared.dummy import sharedFunctionality

from src.client.networking import setupNetworking

def main(args):
    print "Hi, I'm a client!"
    sharedFunctionality()

    # TODO: Where do we put this call, which starts the Twisted event loop?
    task.react(setupNetworking, (args.host, args.port))

