from src.shared.encode import encodePosition, decodePosition

class Backend:
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

    def stdioMessage(self, message):
        if self.allReady:
            self.network.backendMessage(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            print "Warning: input '{}' ignored; client not initialized yet." \
                .format(message)

    def networkMessage(self, message):
        if self.allReady:
            self.stdio.backendMessage(message)
            newPos = decodePosition(message)
            if newPos is not None:
                x, y = newPos
                self.graphics.backendMessage(x, y)
            else:
                print "Warning: failed to parse position {!r}".format(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            print "Warning: server message '{}' ignored; client not " \
                "initialized yet.".format(message)

    # FIXME: Change to use strings.
    def graphicsMessage(self, x, y):
        self.graphics.backendMessage(x, y)
        self.network.backendMessage(encodePosition((x, y)))

    # FIXME: Should be a graphicsMessage
    def quitClient(self):
        for component in self.allComponents:
            component.onClientQuit()
        self.done.callback(None)

