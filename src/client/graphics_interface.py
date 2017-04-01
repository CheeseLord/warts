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

        self.nextGid  = 0
        # Mapping from unit ids to graphics ids.
        self.uidToGid = {}

    # Red A5, standing by.
    def graphicsReady(self, graphicsComponent):
        assert self.graphics is None
        self.graphics = graphicsComponent
        assert self.graphics is not None
        self.ready = True
        self.backend.graphicsInterfaceReady(self)

    # TODO: Split this function up; it's gotten too big.
    def backendMessage(self, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.YourIdIs):
                if self.myId >= 0:
                    raise RuntimeError("ID already set; can't change it now.")
                self.myId          = message.playerId
            elif isinstance(message, messages.NewObelisk):
                uid  = message.unitId
                uPos = message.pos

                gid  = self.getNextGid()
                gPos = unitToGraphics(uPos)

                if uid in self.uidToGid:
                    invalidMessageArgument(message, log, sender="server",
                        reason="uid {} already corresponds to gid {}"
                            .format(uid, gid))
                    # This is probably a bug on our end, so maybe we shouldn't
                    # drop the message. Instead, it would make sense to just
                    # assign that uid a new gid and add it to the graphics.
                    # But that would probably leave the old gid orphaned, with
                    # no way to ever remove it. So for now, drop the message.
                    return
                self.uidToGid[uid] = gid

                # TODO: Long-term, we need to just get rid of this logic
                # entirely. Need a real way of distinguishing my units from
                # other players' units.
                if unitToPlayer(uid) == self.myId:
                    isExample = True
                    modelPath = "models/panda-model"
                else:
                    isExample = False
                    modelPath = "other-obelisk.egg"

                # TODO[#3]: Magic numbers bad
                goalUSize = (10, 10)

                # TODO: Organize all the coordinate conversion functions. Make
                # sure we have functions to convert both positions and sizes.
                # Actually use one of those functions here.
                goalGSize = tuple(float(x)/GRAPHICS_SCALE for x in goalUSize)

                gMessage = messages.AddEntity(gid, gPos, isExample, goalGSize,
                                              modelPath)
                self.graphics.interfaceMessage(gMessage.serialize())
            elif isinstance(message, messages.GroundInfo):
                cPos        = message.pos
                terrainType = message.terrainType

                if terrainType == 0:
                    modelName = "green-ground.egg"
                elif terrainType == 1:
                    modelName = "red-ground.egg"
                else:
                    invalidMessageArgument(message, log, sender="server",
                        reason="Invalid terrain type")
                    return

                gid  = self.getNextGid()

                gPos1 = unitToGraphics(chunkToUnit(cPos))
                gPos2 = unitToGraphics(chunkToUnit((coord + 1
                                                    for coord in cPos)))

                # Figure out where we want the tile.
                goalCenterX = 0.5 * (gPos2[0] + gPos1[0])
                goalCenterY = 0.5 * (gPos2[1] + gPos1[1])
                goalWidthX  =    abs(gPos2[0] - gPos1[0])
                goalWidthY  =    abs(gPos2[1] - gPos1[1])

                gPos      = (goalCenterX, goalCenterY)
                goalGSize = (goalWidthX,  goalWidthY)

                gMessage = messages.AddEntity(gid, gPos, False, goalGSize,
                                              modelName)
                self.graphics.interfaceMessage(gMessage.serialize())
            elif isinstance(message, messages.DeleteObelisk):
                uid = message.unitId

                if uid not in self.uidToGid:
                    invalidMessageArgument(message, log, sender="server",
                        reason="No graphical entity for uid {}".format(uid))
                    return
                gid = self.uidToGid.pop(uid)

                gMessage = messages.RemoveEntity(gid)
                self.graphics.interfaceMessage(gMessage.serialize())
            elif isinstance(message, messages.SetPos):
                uid  = message.unitId
                uPos = message.pos

                if uid not in self.uidToGid:
                    invalidMessageArgument(message, log, sender="server",
                        reason="No graphical entity for uid {}".format(uid))
                    return
                gid = self.uidToGid[uid]

                gPos = unitToGraphics(uPos)

                gMessage = messages.MoveEntity(gid, gPos)
                self.graphics.interfaceMessage(gMessage.serialize())
            elif isinstance(message, messages.MarkUnitSelected):
                # FIXME[#40]: See below. This is not from the server.
                # On the bright side, that means we don't need to sanitize the
                # uid.
                uid = message.unitId
                gid = self.uidToGid[uid]
                msg = messages.MarkEntitySelected(gid, message.isSelected)
                self.graphics.interfaceMessage(msg.serialize())
            else:
                # TODO[#40]: This is going to bite us later. It hardcodes two
                # different assumptions, both of which are probably going to be
                # invalidated at some point.
                #   1. Every backend -> clientInterface message originates from
                #      the server.
                #   2. Every message that the backend forwards from the server
                #      to the graphicsInterface is something that the
                #      graphicsInterface will be able to handle.
                unhandledMessageCommand(message, log, sender="server")
        except InvalidMessageError as error:
            illFormedMessage(error, log, sender="server")

    def graphicsMessage(self, messageStr):
        # TODO: Actually handle things here, and abstract them a little better
        # before sending them to the backend.
        self.backend.graphicsMessage(messageStr)

    def cleanup(self):
        self.graphics.cleanup()

    def getNextGid(self):
        gid = self.nextGid
        self.nextGid += 1
        return gid

