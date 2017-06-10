import logging

from src.shared import messages
from src.shared.game_state import GameState
from src.shared.ident import UnitId, unitToPlayer, getUnitSubId
from src.shared.logconfig import newLogger
from src.shared.unit_set import UnitSet
from src.shared.message_infrastructure import deserializeMessage, \
    unhandledInternalMessage, InvalidMessageError
from src.client import messages as cmessages

# Constants
GRAPHICS_SCALE = 3

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

        # FIXME [#62]: Get the size from the server! Magic numbers very bad!!
        self.gameState = GameState((10, 5))
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
            self.handleUserInput(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Input '{}' ignored; client not initialized yet." \
                .format(message))

    def handleUserInput(self, message):
        assert not message.endswith('\n')

        if message == "dump":
            log.info("Dumping all unit info...")
            for uid in sorted(self.gameState.positions):
                pos = self.gameState.positions[uid]
                isSelected = (uid in self.unitSelection)
                log.info("    {sel:1} {player:>2}: {subId:>3} @ {x:>4}, {y:>4}"
                         .format(sel    = "*" if isSelected else "",
                                 player = unitToPlayer(uid),
                                 subId  = getUnitSubId(uid),
                                 x      = pos[0],
                                 y      = pos[1]))
            log.info("End unit dump.")
        else:
            self.network.backendMessage(message)

    def networkMessage(self, messageStr):
        if self.allReady:
            try:
                message = deserializeMessage(messageStr)
                self.tryToHandleNetworkMessage(message)
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

    def tryToHandleNetworkMessage(self, message):
        if isinstance(message, messages.YourIdIs):
            if self.myId >= 0:
                raise RuntimeError("ID already set; can't change it now.")
            self.myId = message.playerId
            log.info("Your id is {id}.".format(id=self.myId))

            self.unitSelection = UnitSet([])
        elif isinstance(message, messages.NewObelisk):
            uid = message.unitId
            pos = message.pos
            if uid in self.gameState.positions:
                invalidMessageArgument(message, log, sender="server",
                    reason="uid {} already in use".format(uid))
                return
            self.gameState.positions[uid] = pos
        elif isinstance(message, messages.DeleteObelisk):
            uid = message.unitId
            if uid not in self.gameState.positions:
                invalidMessageArgument(message, log, sender="server",
                    reason="No such uid: {}".format(uid))
                return
            if uid in self.unitSelection:
                self.removeFromSelection(uid)
            del self.gameState.positions[uid]
        elif isinstance(message, messages.SetPos):
            uid = message.unitId
            pos = message.pos
            if uid not in self.gameState.positions:
                invalidMessageArgument(message, log, sender="server",
                    reason="No such uid: {}".format(uid))
                return
            self.gameState.positions[uid] = pos
        elif isinstance(message, messages.GroundInfo):
            # Note: this isn't used in any way right now. I think it's right,
            # but it's definitely possible we transposed something, or worse.
            x, y        = message.pos
            terrainType = message.terrainType
            self.gameState.groundTypes[x][y] = terrainType
        else:
            # It's okay if we aren't able to handle a message from the
            # server; maybe the GraphicsInterface will handle it.
            pass

    def graphicsMessage(self, messageStr):
        message = deserializeMessage(messageStr)
        if isinstance(message, cmessages.Click):
            # TODO: Have Click indicate "left" or "right", rather than just a
            # numerical button.
            # TODO: GraphicsInterface should probably translate Click.pos to a
            # uPos before passing it to the backend.
            if message.button == 1:
                # Left mouse button
                gPos = message.pos
                uPos = graphicsToUnit(gPos)
                chosenUnit = self.getUnitAt(uPos)
                self.clearSelection()
                if chosenUnit is not None:
                    self.addToSelection(chosenUnit)
            elif message.button == 3:
                # Right mouse button
                newMsg = messages.OrderMove(self.unitSelection,
                                            graphicsToUnit(message.pos))
                self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.ShiftLClick):
            gPos = message.pos
            uPos = graphicsToUnit(gPos)
            chosenUnit = self.getUnitAt(uPos)
            if chosenUnit is not None:
                self.addToSelection(chosenUnit)
        elif isinstance(message, cmessages.ControlLClick):
            gPos = message.pos
            uPos = graphicsToUnit(gPos)
            chosenUnit = self.getUnitAt(uPos)
            if chosenUnit is not None and chosenUnit in self.unitSelection:
                self.removeFromSelection(chosenUnit)
        elif isinstance(message, cmessages.ShiftRClick):
            newMsg = messages.OrderNew(graphicsToUnit(message.pos))
            self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.ControlRClick):
            gPos = message.pos
            uPos = graphicsToUnit(gPos)
            chosenUnit = self.getUnitAt(uPos)
            if chosenUnit is not None:
                if chosenUnit in self.unitSelection:
                    self.removeFromSelection(chosenUnit)
                newMsg = messages.OrderDel(UnitSet([chosenUnit]))
                self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.DragBox):
            ux1, uy1 = graphicsToUnit(message.corner1)
            ux2, uy2 = graphicsToUnit(message.corner2)
            xMin = min(ux1, ux2)
            xMax = max(ux1, ux2)
            yMin = min(uy1, uy2)
            yMax = max(uy1, uy2)
            self.clearSelection()
            for (uid, uPos) in self.gameState.positions.iteritems():
                ux, uy = uPos
                # TODO: Add a tolerance based on the size of the unit.
                if xMin <= ux <= xMax and yMin <= uy <= yMax:
                    self.addToSelection(uid)
        elif isinstance(message, cmessages.RequestCenter):
            if not self.unitSelection:
                # FIXME: Move to center of world.
                return
            totalX, totalY = 0, 0
            for unitId in self.unitSelection:
                unitX, unitY = self.gameState.positions[unitId]
                totalX += unitX
                totalY += unitY
            centroid = (totalX // len(self.unitSelection),
                        totalY // len(self.unitSelection))
            # FIXME: Write this.
        elif isinstance(message, cmessages.RequestQuit):
            for component in self.allComponents:
                component.cleanup()
            self.done.callback(None)
        else:
            unhandledInternalMessage(message, log)

    def getUnitAt(self, targetUPos):
        targetX, targetY = targetUPos

        # TODO[#3]: Make this a real constant somewhere. Or take into account
        # the size of the unit? This could get ugly.
        MAX_DISTANCE = 30**2

        nearest = None
        # TODO: Compute the diameter of the world in unit coordinates when we
        # first load the map, have the server send that to the client, save
        # that+1 as UPOS_INFINITY or some such, and use that here instead of a
        # float.
        nearestDistance = float('inf')
        for (uid, uPos) in self.gameState.positions.iteritems():
            if unitToPlayer(uid) != self.myId:
                continue

            x, y = uPos
            distance = (x - targetX)**2 + (y - targetY)**2
            if distance < nearestDistance and distance < MAX_DISTANCE:
                nearest         = uid
                nearestDistance = distance

        return nearest

    def addToSelection(self, unitId):
        self.unitSelection.add(unitId)
        msg = cmessages.MarkUnitSelected(unitId, True)
        self.graphicsInterface.backendMessage(msg.serialize())

    def removeFromSelection(self, unitId):
        self.unitSelection.remove(unitId)
        msg = cmessages.MarkUnitSelected(unitId, False)
        self.graphicsInterface.backendMessage(msg.serialize())

    def clearSelection(self):
        for unitId in self.unitSelection:
            msg = cmessages.MarkUnitSelected(unitId, False)
            self.graphicsInterface.backendMessage(msg.serialize())
        self.unitSelection = UnitSet()

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

