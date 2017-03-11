import logging

from src.shared import messages
from src.shared.ident import UnitId
from src.shared.logconfig import newLogger
from src.shared.unit_set import UnitSet
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

        # FIXME[#16]: Make sure an empty UnitSet doesn't serialize to the empty
        # string before trying to issue orders to it.
        self.unitSelection = UnitSet()

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

        # Request obelisks.
        msg = messages.OrderNew((10, 0))
        self.network.backendMessage(msg.serialize())
        msg = messages.OrderNew((0, 10))
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

                    # FIXME[#16]: This might be a nonexistent id. We shouldn't
                    # issue orders to it unless that unit id actually exists.
                    firstId = UnitId(self.myId, 0)
                    self.unitSelection = UnitSet([firstId])
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
            # TODO: Have Click indicate "left" or "right", rather than just a
            # numerical button.
            if message.button == 1:
                # Left mouse button
                newMsg = messages.RequestUnitAt(message.pos)
                self.graphicsInterface.backendMessage(newMsg.serialize())
            elif message.button == 3:
                # Right mouse button
                newMsg = messages.OrderMove(self.unitSelection,
                                            graphicsToUnit(message.pos))
                self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, messages.RequestQuit):
            for component in self.allComponents:
                component.cleanup()
            self.done.callback(None)
        elif isinstance(message, messages.SelectUnits):
            self.unitSelection = message.unitSet
        else:
            unhandledInternalMessage(message, log)

# TODO: Shouldn't these be in the GraphicsInterface if they're going to be
# with a single component?
def unitToGraphics(unitCoords):
    """Convert unit (xu,yu) integers tuples to graphics (xg,yg) float tuples
    """
    return tuple(float(x)/GRAPHICS_SCALE for x in unitCoords)

def graphicsToUnit(graphicsCoords):
    """Convert graphics (xg,yg) float tuples to unit (xu,yu) integers tuples
    """
    return tuple(int(round(x*GRAPHICS_SCALE)) for x in graphicsCoords)

