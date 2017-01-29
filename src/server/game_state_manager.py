from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import findPath
from src.shared.ident import unitToPlayer, playerToUnit
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, InvalidMessageError
from src.shared import messages
from src.shared.unit_orders import UnitOrders, Order, DelUnitOrder, \
    MoveUnitOrder

log = newLogger(__name__)


class GameStateManager(object):
    def __init__(self, connectionManager):
        super(GameStateManager, self).__init__()

        self.gameState = GameState()
        self.unitOrders = UnitOrders()
        self.connectionManager = connectionManager

    # TODO[#10]: Why is this in GameStateManager?
    def handshake(self, playerId):
        # Send ground info.
        for x in range(len(self.gameState.groundTypes)):
            for y in range(len(self.gameState.groundTypes[x])):
                groundType = self.gameState.groundTypes[x][y]
                msg = messages.GroundInfo((x, y), groundType)
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
        try:
            message = deserializeMessage(data)
            # FIXME[#17]: For all except OrderNew, validate that the unit
            # belongs to the player issuing the order.
            if isinstance(message, messages.OrderNew):
                self.unitOrders.createNewUnit(playerId, message.pos)
            elif isinstance(message, messages.OrderDel):
                # TODO[#16]: Remove *a* unit, not *the* unit.
                self.unitOrders.giveOrders(message.unitId, [DelUnitOrder()])
            elif isinstance(message, messages.OrderMove):
                unitId = message.unitId
                try:
                    srcPos = self.gameState.getPos(unitId)
                    path = findPath(self.gameState, srcPos, message.dest)
                    log.debug("Issuing orders to unit {}: {}."
                              .format(unitId, path))
                    orders = map(MoveUnitOrder, path)
                    self.unitOrders.giveOrders(unitId, orders)
                except NoPathToTargetError:
                    log.debug("Can't order unit {} to {}: no path to target."
                              .format(unitId, message.dest))
                    # If the target position is not reachable, just drop the
                    # command.
                    pass
            else:
                unhandledMessageCommand(message, log,
                    sender="client {id}".format(id=playerId))
        except InvalidMessageError as error:
            illFormedMessage(error, log,
                sender="client {id}".format(id=playerId))

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
        for unitId in self.gameState.getAllUnits():
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
                    msg = messages.DeleteObelisk(unitId)
                    self.connectionManager.broadcastMessage(msg)
                done = True

            # Move player.
            elif isinstance(order, MoveUnitOrder):
                dest = order.dest
                pos  = self.gameState.getPos(unitId)

                # Don't try to move to the current position.
                if dest != pos:
                    # log.debug("Moving unit {} (at {}) toward {}."
                    #           .format(unitId, pos, dest))
                    assert dest is not None
                    # POS_INT_CHECK
                    for k in dest:
                        assert type(k) is int

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

