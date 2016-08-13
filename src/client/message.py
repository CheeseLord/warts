class MessageHub:
    def __init__(self):
        self.stdio   = None
        self.network = None

    @property
    def allComponents(self):
        return (self.stdio, self.network)

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
        for component in self.allComponents:
            component.onAllReady()

