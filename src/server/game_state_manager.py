from collections import defaultdict

from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import findPath
from src.shared.ident import unitToPlayer, getUnitSubId
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    badEMessageArgument, illFormedEMessage, badEMessageCommand, \
    InvalidMessageError
from src.shared import messages
from src.shared.unit_orders import UnitOrders, Order, DelUnitOrder, \
    MoveUnitOrder

log = newLogger(__name__)

# TODO[#10]: Why is this in GameStateManager?
MAXIMUM_MESSAGES_PER_TICK = 10


class GameStateManager(object):
    def __init__(self, connectionManager):
        super(GameStateManager, self).__init__()

        self.gameState = getDefaultGameState()
        self.unitOrders = UnitOrders()
        self.connectionManager = connectionManager

        # TODO[#10]: Why is this in GameStateManager?
        self.messageCounts = defaultdict(int)

        # TODO[#10]: Why is this in GameStateManager?
        self.stdio = None

    # TODO[#10]: Why is this in GameStateManager?
    def stdioReady(self, stdioComponent):
        assert self.stdio is None
        self.stdio = stdioComponent
        assert self.stdio is not None

    # TODO[#10]: Why is this in GameStateManager?
    def stdioMessage(self, message):
        # TODO[#48]: Use a real message here.
        if message == "dump":
            log.info("Dumping all unit info...")
            for uid in sorted(self.gameState.positions.keys()):
                pos = self.gameState.positions[uid]
                # TODO: Factor this out (maybe into gamestate?)
                # "    {player:>2}: {subId:>3} @ {x:>4}, {y:>4}"
                log.info("    %2s: %3s @ %4s, %4s",
                         unitToPlayer(uid), getUnitSubId(uid), pos[0], pos[1])
            log.info("End unit dump.")
        else:
            # TODO: Do something sensible.
            log.info("Don't know how to handle %r.", message)

    # TODO[#10]: Why is this in GameStateManager?
    def handshake(self, playerId):
        # Send map size (must come before ground info).
        msg = messages.MapSize(self.gameState.sizeInChunks)
        self.connectionManager.sendMessage(playerId, msg)

        # Send ground info.
        for x in range(len(self.gameState.groundTypes)):
            for y in range(len(self.gameState.groundTypes[x])):
                groundType = self.gameState.groundTypes[x][y]
                msg = messages.GroundInfo((x, y), groundType)
                self.connectionManager.sendMessage(playerId, msg)

        # Send resource pool info.
        for pool in self.gameState.resourcePools:
            msg = messages.ResourceLoc(pool)
            self.connectionManager.sendMessage(playerId, msg)

        # Send positions of all existing obelisks.
        for unitId in self.gameState.positions:
            # The gameState does not yet know about this new player, so their
            # id should not be in the gameState's mapping.
            assert unitToPlayer(unitId) != playerId
            otherPos = self.gameState.getPos(unitId)
            msg = messages.NewObelisk(unitId, otherPos)
            self.connectionManager.sendMessage(playerId, msg)

    # FIXME[#10]: Why is this in GameStateManager?
    def removeConnection(self, playerId):
        for unitId in self.gameState.getAllUnitsForPlayer(playerId):
            self.unitOrders.giveOrders(unitId, [DelUnitOrder()])

    # FIXME[#10]: Why is this in GameStateManager?
    def stringReceived(self, playerId, data):
        # Rate-limit the client.
        self.messageCounts[playerId] += 1
        if self.messageCounts[playerId] == MAXIMUM_MESSAGES_PER_TICK:
            log.warning("Received too many messages this tick from player %s",
                        playerId)
        if self.messageCounts[playerId] >= MAXIMUM_MESSAGES_PER_TICK:
            return

        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.OrderNew):
                self.unitOrders.createNewUnit(playerId, message.pos)
            elif isinstance(message, messages.OrderDel):
                for unitId in message.unitSet:
                    # TODO: Factor out this pair of checks? We're probably
                    # going to be doing them a *lot*.
                    if not playerId == unitToPlayer(unitId):
                        badEMessageArgument(
                            message, log, clientId=playerId,
                            reason="Can't delete other player's unit"
                        )
                    elif not self.gameState.isUnitIdValid(unitId):
                        badEMessageArgument(message, log, clientId=playerId,
                                            reason="No such unit")
                    else:
                        self.unitOrders.giveOrders(unitId, [DelUnitOrder()])
            elif isinstance(message, messages.OrderMove):
                unitSet = message.unitSet
                for unitId in unitSet:
                    if not playerId == unitToPlayer(unitId):
                        badEMessageArgument(
                            message, log, clientId=playerId,
                            reason="Can't order other player's unit"
                        )
                    elif not self.gameState.isUnitIdValid(unitId):
                        badEMessageArgument(message, log, clientId=playerId,
                                            reason="No such unit")
                    else:
                        try:
                            srcPos = self.gameState.getPos(unitId)
                            path = findPath(self.gameState, srcPos, message.dest)
                            log.debug("Issuing orders to unit %s: %s.",
                                      unitId, path)
                            orders = map(MoveUnitOrder, path)
                            self.unitOrders.giveOrders(unitId, orders)
                        except NoPathToTargetError:
                            log.debug("Can't order unit %s to %s: "
                                      "no path to target.",
                                      unitId, message.dest)
                            # If the target position is not reachable, just drop
                            # the command.
            else:
                badEMessageCommand(message, log, clientId=playerId)
        except InvalidMessageError as error:
            illFormedEMessage(error, log, clientId=playerId)

    # FIXME[#10]: Why is this in GameStateManager?
    def tick(self):
        self.applyOrders()
        self.messageCounts.clear()
        # FIXME: Shouldn't really go in tick(); I just put it here so we could
        # test handling of ResourceAmt in client.
        # Hack: just give everyone 42 resources.
        msg = messages.ResourceAmt(42)
        self.connectionManager.broadcastMessage(msg)

    def applyOrders(self):
        # Create any pending units.
        for playerId, pos in self.unitOrders.getPendingNewUnits():
            unitId = self.gameState.addUnit(playerId, pos)
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
    # TODO [#70]: Make use of BUILDS_PER_CHUNK.
    gameState.resourcePools.extend([
        (13, 16),
        (14, 16),
    ])

    return gameState

