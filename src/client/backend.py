import logging

from src.shared import messages
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    unhandledInternalMessage

log = newLogger(__name__)


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
    def stdioReady(self, stdioComponent):
        assert self.stdio is None
        self.stdio = stdioComponent
        assert self.stdio is not None
        self.checkIfAllReady()

    # Red 11, standing by.
    def networkReady(self, networkComponent):
        assert self.network is None
        self.network = networkComponent
        assert self.network is not None
        self.checkIfAllReady()

    # Red 5, standing by.
    def graphicsReady(self, graphicsComponent):
        assert self.graphics is None
        self.graphics = graphicsComponent
        assert self.graphics is not None
        self.checkIfAllReady()

    def checkIfAllReady(self):
        for component in self.allComponents:
            if component is None:
                # Not ready
                return
        self.allComponentsReady()

    def allComponentsReady(self):
        # I'm keeping this method around, even though all it does is set a
        # flag, because it seems like we might want to put some final
        # initialization code in here.
        # ... or change the implementation somehow so that we don't have to
        # constantly check self.allReady for the entire lifetime of the client.
        self.allReady = True


    ########################################################################
    # Incoming messages

    def stdioMessage(self, message):
        if self.allReady:
            self.network.backendMessage(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Input '{}' ignored; client not initialized yet." \
                .format(message))

    def networkMessage(self, message):
        if self.allReady:
            self.graphics.backendMessage(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Server message '{}' ignored; client not " \
                "initialized yet.".format(message))

    def graphicsMessage(self, messageStr):
        message = deserializeMessage(messageStr)
        if isinstance(message, messages.Click):
            newMsg = messages.MoveTo(tuple(int(round(x)) for x in message.pos))
            self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, messages.RequestQuit):
            for component in self.allComponents:
                component.cleanup()
            self.done.callback(None)
        else:
            unhandledInternalMessage(message, log)

