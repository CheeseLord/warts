class MessageHub:
    def __init__(self):
        self.stdio   = None
        self.network = None

        self.allReady = False

    @property
    def allComponents(self):
        return (self.stdio, self.network)


    ########################################################################
    # Initialization

    def onStdioReady(self, stdioComponent):
        assert self.stdio is None
        self.stdio = stdioComponent
        assert self.stdio is not None
        self.checkIfAllReady()

    def onNetworkReady(self, networkComponent):
        assert self.network is None
        self.network = networkComponent
        assert self.network is not None
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
            print "Warning: input '{}' ignored; client not initialized yet." \
                .format(message)

    def recvNetwork(self, message):
        if self.allReady:
            self.sendStdio(message)
        else:
            print "Warning: server message '{}' ignored; client not " \
                "initialized yet.".format(message)


    ########################################################################
    # Outgoing messages

    def sendStdio(self, message):
        # TODO: These checks are redundant.
        if self.allReady:
            self.stdio.messageFromNetwork(message)

    def sendNetwork(self, message):
        if self.allReady:
            self.network.messageFromStdio(message)

