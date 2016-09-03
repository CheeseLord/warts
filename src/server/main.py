from src.server.networking import runServer

def main(args):
    print "Hi, I'm a server!"
    runServer(args.port)
