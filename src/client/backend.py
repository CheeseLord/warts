import logging

from src.shared import messages
from src.shared.ident import playerToUnit
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    unhandledInternalMessage, InvalidMessageError

# Constants
GRAPHICS_SCALE=3

# Logging
log = newLogger(__name__)


class Backend:
    def __init__(self, done):
        # Done is a Twisted Deferred object whose callback can be fired to
        # close down the client cleanly (in theory...).
        self.done = done

        self.stdio    = None
        self.network  = None
        self.graphicsInterface = None

        self.allReady = False

        self.myId = -1

    @property
    def allComponents(self):
        return (self.stdio, self.network, self.graphicsInterface)


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
    def graphicsInterfaceReady(self, graphicsInterface):
        assert self.graphicsInterface is None
        self.graphicsInterface = graphicsInterface
        assert self.graphicsInterface is not None
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

        # Request an obelisk.
        msg = messages.OrderNew((0, 0))
        self.network.backendMessage(msg.serialize())


    ########################################################################
    # Incoming messages

    def stdioMessage(self, message):
        if self.allReady:
            self.network.backendMessage(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Input '{}' ignored; client not initialized yet." \
                .format(message))

    def networkMessage(self, messageStr):
        if self.allReady:
            try:
                message = deserializeMessage(messageStr)
                if isinstance(message, messages.YourIdIs):
                    if self.myId >= 0:
                        raise RuntimeError("ID already set; can't change it "
                                           "now.")
                    self.myId = message.playerId
                    log.info("Your id is {id}.".format(id=self.myId))
            except InvalidMessageError as error:
                illFormedMessage(error, log, sender="server")

            # Regardless of whether we were able to handle it, forward the
            # message on to the graphicsInterface (which -- at least for now --
            # also handles the YourIdIs message).
            self.graphicsInterface.backendMessage(messageStr)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Server message '{}' ignored; client not " \
                "initialized yet.".format(messageStr))

    def graphicsMessage(self, messageStr):
        message = deserializeMessage(messageStr)
        if isinstance(message, messages.Click):
            unitId = playerToUnit(self.myId)
            newMsg = messages.OrderMove(unitId, graphicsToUnit(message.pos))
            self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, messages.RequestQuit):
            for component in self.allComponents:
                component.cleanup()
            self.done.callback(None)
        else:
            unhandledInternalMessage(message, log)

def unitToGraphics(unitCoords):
    """Convert unit (xu,yu) integers tuples to graphics (xg,yg) float tuples
    """
    return tuple(float(x)/GRAPHICS_SCALE for x in unitCoords)

def graphicsToUnit(graphicsCoords):
    """Convert graphics (xg,yg) float tuples to unit (xu,yu) integers tuples
    """
    return tuple(int(round(x*GRAPHICS_SCALE)) for x in graphicsCoords)
