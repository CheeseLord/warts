from src.shared.encode import encodePosition, decodePosition

class MessageHub:
    def __init__(self, done):
        # Done is a Twisted Deferred object whose callback can be fired to
        # close down the client cleanly (in theory...).
        self.done = done

        self.stdio    = None
        self.network  = None
        self.graphics = None

        self.allReady = False

    @property
    def allComponents(self):
        return (self.stdio, self.network, self.graphics)


    ########################################################################
    # Initialization

    # All wings, report in.

    # Red 2, standing by.
    def onStdioReady(self, stdioComponent):
        assert self.stdio is None
        self.stdio = stdioComponent
        assert self.stdio is not None
        self.checkIfAllReady()

    # Red 11, standing by.
    def onNetworkReady(self, networkComponent):
        assert self.network is None
        self.network = networkComponent
        assert self.network is not None
        self.checkIfAllReady()

    # Red 5, standing by.
    def onGraphicsReady(self, graphicsComponent):
        assert self.graphics is None
        self.graphics = graphicsComponent
        assert self.graphics is not None
        self.checkIfAllReady()

    def checkIfAllReady(self):
        for component in self.allComponents:
            if component is None:
                # Not ready
                return
        # All ready
        self.signalAllReady()

    def signalAllReady(self):
        self.allReady = True
        for component in self.allComponents:
            component.onAllReady()


    ########################################################################
    # Incoming messages

    def recvStdio(self, message):
        if self.allReady:
            self.sendNetwork(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            print "Warning: input '{}' ignored; client not initialized yet." \
                .format(message)

    def recvNetwork(self, message):
        if self.allReady:
            self.sendStdio(message)
            newPos = decodePosition(message)
            if newPos is not None:
                self.setGraphicsPos(newPos)
            else:
                print "Warning: failed to parse position {!r}".format(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            print "Warning: server message '{}' ignored; client not " \
                "initialized yet.".format(message)

    def onClick(self, x, y):
        self.setGraphicsPos((x, y))
        self.sendNetwork(encodePosition((x, y)))

    def quitClient(self):
        for component in self.allComponents:
            component.onClientQuit()
        self.done.callback(None)


    ########################################################################
    # Outgoing messages

    # TODO: These are all trivial wrapper functions, which are probably going
    # to cost us w/r/t efficiency. And I think they make the code harder to
    # follow as well. We really need to reorganize this part of the code.

    def sendStdio(self, message):
        # TODO: These checks are redundant.
        if self.allReady:
            self.stdio.messageFromNetwork(message)

    def sendNetwork(self, message):
        if self.allReady:
            self.network.messageFromStdio(message)

    def setGraphicsPos(self, newPos):
        x, y = newPos
        self.graphics.setPlayerPos(x, y)

