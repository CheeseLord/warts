from src.shared import config
from src.shared import messages
from src.shared.geometry import chunkToUnit
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, invalidMessageArgument, \
    InvalidMessageError
from src.client.backend import unitToGraphics, GRAPHICS_SCALE

log = newLogger(__name__)

class GraphicsInterface(object):
    def __init__(self, backend):
        self.ready = False
        self.graphics = None
        self.backend = backend

    # Red A5, standing by.
    def graphicsReady(self, graphicsComponent):
        assert self.graphics is None
        self.graphics = graphicsComponent
        assert self.graphics is not None
        self.ready = True
        self.backend.graphicsInterfaceReady(self)

    def backendMessage(self, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.YourIdIs):
                if self.graphics.myId >= 0:
                    raise RuntimeError("ID already set; can't change it now.")
                self.graphics.myId = message.playerId
            elif isinstance(message, messages.NewObelisk):
                self.graphics.addObelisk(message.unitId, message.pos)
            elif isinstance(message, messages.DeleteObelisk):
                self.graphics.removeObelisk(message.unitId)
            elif isinstance(message, messages.SetPos):
                self.graphics.moveObelisk(message.unitId, message.pos)
            elif isinstance(message, messages.GroundInfo):
                self.graphics.addGround(message.pos, message.terrainType)
            else:
                unhandledMessageCommand(message, log, sender="server")
        except InvalidMessageError as error:
            illFormedMessage(error, log, sender="server")

    def graphicsMessage(self, messageStr):
        self.backend.graphicsMessage(messageStr)

    def cleanup(self):
        self.graphics.cleanup()
