from collections import deque

from src.shared.game_state import GameState
from src.shared.game_state_change import ResourceChange
from src.shared.geometry import Distance, Coord, Rect, isRectCollision
from src.shared.ident import unitToPlayer
from src.shared.logconfig import newLogger
from src.shared import messages
from src.shared.unit_orders import UnitOrders, Order, DelUnitOrder, \
    MoveUnitOrder
from src.shared.utils import thisShouldNeverHappen

log = newLogger(__name__)

class GameStateManager(object):
    def __init__(self, backend, connections):
        super(GameStateManager, self).__init__()

        self.backend           = backend
        self.connectionManager = connections

        self.backend.setGameStateManager(self)

        self.gameState = getDefaultGameState()
        self.unitOrders = UnitOrders()
        self.pendingChanges = deque()

        # TODO[#10]: Why is this in GameStateManager?
        # I was gonna just make this a global, but pylint doesn't like globals.
        # Fortunately, this is definitely less terrible and hacky.
        self.elapsedTicks = 0

    def removePlayer(self, playerId):
        for unitId in self.gameState.getAllUnitsForPlayer(playerId):
            self.unitOrders.giveOrders(unitId, [DelUnitOrder()])

    # Why is this in GameStateManager?
    # Wrong question. *This* function's purpose is "update the game state
    # because a tick has elapsed", which is pretty much the one thing here that
    # definitely does belong in the GameStateManager. The right question is:
    # "Where is the top-level function that resolves a tick, or for that matter
    # is there even such a function above GameStateManager.tick?" To which the
    # answer is: "Currently, no; server.main just sets up a LoopingCall of
    # gameStateManager.tick. But there's very little that needs to be done on
    # a tick boundary that isn't updating game state, so it's not really clear
    # there needs to be a function above GameStateManager.tick."
    def tick(self):
        # FIXME: Shouldn't really go in tick(); I just put it here so we could
        # test handling of ResourceAmt in client.
        self.resolveResourceGathering()

        self.applyOrders()
        self.applyPendingChanges()
        self.broadcastChanges()

        self.pendingChanges.clear()
        self.elapsedTicks += 1

    def checkOverlapUnitAndResource(self, uid, pool):
        # Pool Rectangle
        pLeft, pBottom = pool.unit
        pRight, pTop = (pool  + Distance.fromCBU(build=(1, 1))).unit
        # Get back into the build square
        pTop, pRight = pTop - 1, pRight - 1

        # Unit rectangle
        uX, uY = self.gameState.getPos(uid).unit
        uWidth, uHeight = self.gameState.getSize(uid).unit
        uTop = uY + uHeight // 2
        uBottom = uY - uHeight // 2
        uRight = uX + uWidth // 2
        uLeft = uX - uWidth // 2

        return ((uBottom < pTop and uTop  > pBottom) and
                (uLeft < pRight and uRight  > pLeft))

    def resolveResourceGathering(self):
        if self.elapsedTicks % 5 == 0:
            for uid in self.gameState.getAllUnits():
                for pool in self.gameState.resourcePools:
                    unitRect = self.gameState.getRect(uid)
                    if isRectCollision(unitRect, pool):
                        playerId = unitToPlayer(uid)
                        self.scheduleChange(ResourceChange(playerId, 1))
                        break

    def scheduleChange(self, change):
        self.pendingChanges.append(change)

    def applyPendingChanges(self):
        # TODO: Figure out a way to ensure that these are commutative (or else
        # resolve them simultaneously). As is, this solution might give a
        # subtle advantage to lower-numbered players, depending on what we put
        # in GameStateChanges.
        for change in self.pendingChanges:
            change.apply(self.gameState)

    def broadcastChanges(self):
        for change in self.pendingChanges:
            # FIXME: Hack to send a ResourceAmt for ResourceChanges. Really we
            # should just send a more general GameStateUpdate message, but that
            # doesn't exist yet.
            if isinstance(change, ResourceChange):
                newResources = self.gameState.resources[change.playerId]
                msg = messages.ResourceAmt(newResources)
                self.connectionManager.sendMessage(change.playerId, msg,
                                                   dropOnFailure=True)
            else:
                thisShouldNeverHappen()

    def applyOrders(self):
        # Create any pending units.
        for playerId, unitType, pos in self.unitOrders.getPendingNewUnits():
            unitId = self.gameState.addUnit(playerId, unitType, pos)
            # Should have no effect, but just to make sure we have the right
            # position...
            pos = self.gameState.getPos(unitId)

            msg = messages.NewObelisk(unitId, pos)
            self.connectionManager.broadcastMessage(msg)

        self.unitOrders.clearPendingNewUnits()

        # Resolve orders to any existing units.
        for unitId in self.unitOrders.getAllUnitsWithOrders():
            assert self.gameState.isUnitIdValid(unitId)
            self.applyOrdersForUnit(unitId)

    def applyOrdersForUnit(self, unitId):
        # TODO: Refactor this?
        done = False
        while not done and self.unitOrders.hasNextOrder(unitId):
            order = self.unitOrders.getNextOrder(unitId)

            # Remove unit.
            if isinstance(order, DelUnitOrder):
                # If a client manages to connect then disconnect within a
                # single tick, then it's possible the only order we'll ever
                # execute for their obelisk is the "remove" order, without
                # having first created it. In that case, we can't remove the
                # obelisk, because it doesn't exist: gameState.removePlayer
                # would crash if we tried and the clients would be confused if
                # we sent them a DeleteObelisk message for an unused id.
                #
                # FIXME: This is the wrong solution to that. We shouldn't allow
                # that order to be created in the first place.
                if self.gameState.isUnitIdValid(unitId):
                    self.gameState.removeUnit(unitId)
                    self.unitOrders.clearOrders(unitId)
                    msg = messages.DeleteObelisk(unitId)
                    self.connectionManager.broadcastMessage(msg)
                done = True

            # Move player.
            elif isinstance(order, MoveUnitOrder):
                dest = order.dest
                pos  = self.gameState.getPos(unitId)

                # Don't try to move to the current position.
                if dest != pos:
                    assert dest is not None

                    self.gameState.moveUnitToward(unitId, dest)
                    pos = self.gameState.getPos(unitId)
                    # TODO: Maybe only broadcast the new position if we handled
                    # a valid command? Else the position isn't changed....
                    msg = messages.SetPos(unitId, pos)
                    self.connectionManager.broadcastMessage(msg)

                    # TODO[#13]: Don't set done if the unit can move farther in
                    # this tick.
                    done = True

                else:
                    self.unitOrders.removeNextOrder(unitId)

            elif isinstance(order, Order):
                raise TypeError("Unrecognized sublass of Order")
            else:
                raise TypeError("Found non-Order object among orders")

# TODO[#10]: Why is this in GameStateManager?
def getDefaultGameState():
    # TODO [#3]: Magic numbers bad.
    gameState = GameState((10, 5))

    # Some impassable squares, to better exercise the pathfinding.
    gameState.groundTypes[5][3] = 1
    gameState.groundTypes[1][1] = 1
    gameState.groundTypes[1][2] = 1
    gameState.groundTypes[1][3] = 1
    gameState.groundTypes[2][3] = 1
    gameState.groundTypes[3][2] = 1

    # Resource pools.
    gameState.resourcePools.extend([
        Rect(Coord.fromCBU(chunk=(2, 2), build=(1, 4)),
             Distance.fromCBU(build=(1, 1))),
        Rect(Coord.fromCBU(chunk=(2, 2), build=(2, 4)),
             Distance.fromCBU(build=(1, 1))),
    ])

    return gameState

