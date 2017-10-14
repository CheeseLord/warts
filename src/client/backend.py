from src.shared import messages
from src.shared.game_state import GameState
from src.shared.geometry import Coord
from src.shared.ident import unitToPlayer, getUnitSubId
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    badIMessageCommand, illFormedEMessage, InvalidMessageError, \
    badEMessageCommand, badEMessageArgument
from src.shared.unit_set import UnitSet
from src.client import messages as cmessages

# Constants
GRAPHICS_SCALE = 3
# Max squared distance between mouse click and unit for it to register as
# clicking that unit.
MAX_CLICK_DISTANCE = 30**2

# Logging
log = newLogger(__name__)


class Backend(object):
    def __init__(self, done):
        # Done is a Twisted Deferred object whose callback can be fired to
        # close down the client cleanly (in theory...).
        self.done = done

        self.stdio    = None
        self.network  = None
        self.graphicsInterface = None

        self.allReady = False

        self.myId = -1

        self.gameState     = None
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
        # TODO[#3]: Magic numbers bad.
        msg = messages.OrderNew(0, Coord.fromUnit((10, 0)))
        self.network.backendMessage(msg.serialize())
        msg = messages.OrderNew(1, Coord.fromUnit((0, 10)))
        self.network.backendMessage(msg.serialize())


    ########################################################################
    # Incoming messages

    def stdioMessage(self, message):
        if self.allReady:
            self.handleUserInput(message)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Input %r ignored; client not initialized yet.",
                        message)

    def handleUserInput(self, message):
        assert not message.endswith('\n')

        if message == "dump":
            log.info("Dumping all unit info...")
            for uid in sorted(self.gameState.positions):
                pos = self.gameState.positions[uid]
                isSelected = (uid in self.unitSelection)
                # TODO: Factor this out (maybe into gamestate?)
                # "    {sel:1} {player:>2}: {subId:>3} @ {x:>4}, {y:>4}"
                ux, uy = pos.unit
                log.info("    %1s %2s: %3s @ %4s, %4s",
                         "*" if isSelected else "", unitToPlayer(uid),
                         getUnitSubId(uid), ux, uy)
            log.info("End unit dump.")
        else:
            self.network.backendMessage(message)

    def networkMessage(self, messageStr):
        if self.allReady:
            try:
                message = deserializeMessage(messageStr)
                if self.tryToHandleNetworkMessage(message):
                    # Many backend messages are currently also forwarded to the
                    # graphics interface.
                    self.graphicsInterface.backendMessage(messageStr)
                else:
                    # In fact, so many of them are that we used to just forward
                    # all of them. We don't anymore, but it's still uncommon
                    # enough that we *don't* forward a message that let's put a
                    # log.debug in here, so we can more easily catch if we've
                    # forgotten to forward a message.
                    log.debug("Intentionally not forwarding message to "
                              "graphics interface: %s", message)
            except InvalidMessageError as error:
                illFormedEMessage(error, log)
        else:
            # TODO: Buffer messages until ready? Don't just drop them....
            log.warning("Server message %r ignored; client not initialized " \
                        "yet.", messageStr)

    def tryToHandleNetworkMessage(self, message):
        """
        Attempt to handle a message received from the server.
        Return a boolean indicating whether that message should also be
        forwarded to the graphics interface. If true, it also implies that the
        message is valid, since invalid external messages shouldn't make it any
        farther than the backend.
        """

        forwardToGraphicsInterface = False
        if isinstance(message, messages.YourIdIs):
            if self.myId >= 0:
                raise RuntimeError("ID already set; can't change it now.")
            self.myId = message.playerId
            log.info("Your id is %s.", self.myId)

            self.unitSelection = UnitSet([])
            # TODO: Does the graphics interface really need to know our id?
            # Seems like probably not.
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.NewObelisk):
            uid = message.unitId
            pos = message.pos
            if uid in self.gameState.positions:
                badEMessageArgument(message, log,
                                    reason="uid {} already in use".format(uid))
                return False
            self.gameState.positions[uid] = pos
            # TODO: So the backend needs to keep track of where all the units
            # are because it manages the main logic. And the graphics does also
            # need to know that information because it has to actually draw
            # them. But is this really the best solution? It seems to me that
            # if we're forwarding to the graphics interface all server messages
            # related to unit positions, that probably indicates a
            # poorly-understood division of responsibility between client
            # backend and graphics interface.
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.DeleteObelisk):
            uid = message.unitId
            if uid not in self.gameState.positions:
                badEMessageArgument(message, log,
                                    reason="No such uid: {}".format(uid))
                return False
            if uid in self.unitSelection:
                self.removeFromSelection(uid)
            del self.gameState.positions[uid]
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.SetPos):
            uid = message.unitId
            pos = message.pos
            if uid not in self.gameState.positions:
                badEMessageArgument(message, log,
                                    reason="No such uid: {}".format(uid))
                return False
            self.gameState.positions[uid] = pos
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.ResourceAmt):
            self.gameState.resources[self.myId] = message.amount
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.ResourceLoc):
            self.gameState.resourcePools.append(message.pos)
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.GroundInfo):
            # Note: this isn't used in any way right now. I think it's right,
            # but it's definitely possible we transposed something, or worse.
            cx, cy      = message.pos.chunk
            terrainType = message.terrainType
            self.gameState.groundTypes[cx][cy] = terrainType
            forwardToGraphicsInterface = True
        elif isinstance(message, messages.MapSize):
            if self.gameState is not None:
                log.warn("Got multiple map_size messages.")
            self.gameState = GameState(message.size)
        else:
            badEMessageCommand(message, log)

        return forwardToGraphicsInterface

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
                wPos = graphicsToWorld(gPos)
                chosenUnit = self.getUnitAt(wPos)
                self.clearSelection()
                if chosenUnit is not None:
                    self.addToSelection(chosenUnit)
            elif message.button == 3:
                # Right mouse button
                newMsg = messages.OrderMove(self.unitSelection,
                                            graphicsToWorld(message.pos))
                self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.ShiftLClick):
            gPos = message.pos
            wPos = graphicsToWorld(gPos)
            chosenUnit = self.getUnitAt(wPos)
            if chosenUnit is not None:
                self.addToSelection(chosenUnit)
        elif isinstance(message, cmessages.ControlLClick):
            gPos = message.pos
            wPos = graphicsToWorld(gPos)
            chosenUnit = self.getUnitAt(wPos)
            if chosenUnit is not None and chosenUnit in self.unitSelection:
                self.removeFromSelection(chosenUnit)
        elif isinstance(message, cmessages.ShiftRClick):
            newMsg = messages.OrderNew(1, graphicsToWorld(message.pos))
            self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.ControlRClick):
            gPos = message.pos
            wPos = graphicsToWorld(gPos)
            chosenUnit = self.getUnitAt(wPos)
            if chosenUnit is not None:
                if chosenUnit in self.unitSelection:
                    self.removeFromSelection(chosenUnit)
                newMsg = messages.OrderDel(UnitSet([chosenUnit]))
                self.network.backendMessage(newMsg.serialize())
        elif isinstance(message, cmessages.DragBox):
            ux1, uy1 = graphicsToWorld(message.corner1).unit
            ux2, uy2 = graphicsToWorld(message.corner2).unit
            xMin = min(ux1, ux2)
            xMax = max(ux1, ux2)
            yMin = min(uy1, uy2)
            yMax = max(uy1, uy2)
            self.clearSelection()
            for (uid, wPos) in self.gameState.positions.iteritems():
                ux, uy = wPos.unit
                # TODO: Add a tolerance based on the size of the unit.
                if unitToPlayer(uid) == self.myId:
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
            log.debug("Center requested; it's %s", centroid)
            # FIXME: Write this.
        elif isinstance(message, cmessages.RequestQuit):
            for component in self.allComponents:
                component.cleanup()
            self.done.callback(None)
        else:
            badIMessageCommand(message, log)

    def getUnitAt(self, targetWPos):
        targetX, targetY = targetWPos.unit

        nearest = None
        # TODO: Compute the diameter of the world in unit coordinates when we
        # first load the map, have the server send that to the client, save
        # that+1 as UPOS_INFINITY or some such, and use that here instead of a
        # float.
        nearestDistance = float('inf')
        for (uid, wPos) in self.gameState.positions.iteritems():
            if unitToPlayer(uid) != self.myId:
                continue

            ux, uy = wPos.unit
            distance = (ux - targetX)**2 + (uy - targetY)**2
            if distance < nearestDistance and distance < MAX_CLICK_DISTANCE:
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
def worldToGraphics(wPos):
    return tuple(float(x) / GRAPHICS_SCALE for x in wPos.unit)

def graphicsToWorld(gPos):
    return Coord.fromUnit(int(round(x * GRAPHICS_SCALE)) for x in gPos)

