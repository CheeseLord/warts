from src.shared import config
from src.shared import messages
from src.shared.geometry import chunkToUnit
from src.shared.ident import unitToPlayer
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

        # TODO: Move this out of here as well. Only the backend should care
        # about this.
        self.myId = -1

        self.nextGid = 0

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
                if self.myId >= 0:
                    raise RuntimeError("ID already set; can't change it now.")
                if self.graphics.myId >= 0:
                    raise RuntimeError("ID already set; can't change it now.")
                self.myId          = message.playerId
                self.graphics.myId = message.playerId
            elif isinstance(message, messages.NewObelisk):
                uid  = message.unitId
                uPos = message.pos

                gid  = self.getNextGid()
                gPos = unitToGraphics(uPos)

                # TODO: Long-term, we need to just get rid of this logic
                # entirely. Need a real way of distinguishing my units from
                # other players' units.
                if unitToPlayer(uid) == self.myId:
                    isExample = True
                    modelPath = "models/panda-model"
                else:
                    isExample = False
                    modelPath = "other-obelisk.egg"

                gMessage = messages.AddEntity(gid, gPos, isExample, modelPath)
                self.graphics.interfaceMessage(gMessage.serialize())

                # TODO: Remove this.
                self.graphics.addObelisk(message.unitId, message.pos)
            elif isinstance(message, messages.DeleteObelisk):
                self.graphics.removeObelisk(message.unitId)
            elif isinstance(message, messages.SetPos):
                self.graphics.moveObelisk(message.unitId, message.pos)
            elif isinstance(message, messages.GroundInfo):
                self.graphics.addGround(message.pos, message.terrainType)
            elif isinstance(message, messages.RequestUnitAt):
                unitSet = self.graphics.unitAt(message.pos)
                self.backend.graphicsMessage(
                    messages.SelectUnits(unitSet).serialize())
            else:
                unhandledMessageCommand(message, log, sender="server")
        except InvalidMessageError as error:
            illFormedMessage(error, log, sender="server")

    def graphicsMessage(self, messageStr):
        self.backend.graphicsMessage(messageStr)

    def cleanup(self):
        self.graphics.cleanup()

    def getNextGid(self):
        gid = self.nextGid
        self.nextGid += 1
        return gid

