from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import findPath
from src.shared.ident import unitToPlayer, playerToUnit
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, InvalidMessageError
from src.shared import messages
from src.shared.unit_orders import UnitOrders

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

        # TODO[#16]: Create *a* unit, not *the* unit.
        self.unitOrders.giveOrders(playerToUnit(playerId), [(0, 0)])

    # FIXME[#10]: Why is this in GameStateManager?
    def removeConnection(self, playerId):
        # TODO[#16]: Remove *all* units, not *the* unit.
        self.unitOrders.giveOrders(playerToUnit(playerId), None)

    # FIXME[#10]: Why is this in GameStateManager?
    def stringReceived(self, playerId, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.OrderMove):
                unitId = message.unitId
                try:
                    srcPos = self.gameState.getPos(unitId)
                    path = findPath(self.gameState, srcPos, message.dest)
                    log.debug("Issuing orders to unit {}: {}."
                              .format(unitId, path))
                    self.unitOrders.giveOrders(unitId, path)
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
        # TODO: Refactor this.
        orders = self.unitOrders.getAllUnitsNextOrders()
        for unitId in orders:
            # Remove unit.
            if orders[unitId] is None:
                # If a client manages to connect then disconnect within a
                # single tick, then it's possible the only order we'll ever
                # execute for their obelisk is the "remove" order, without
                # having first created it. In that case, we can't remove the
                # obelisk, because it doesn't exist: gameState.removePlayer
                # would crash if we tried and the clients would be confused if
                # we sent them a DeleteObelisk message for an unused id.
                if self.gameState.isUnitIdValid(unitId):
                    self.gameState.removeUnit(unitId)
                    msg = messages.DeleteObelisk(unitId)
                    self.connectionManager.broadcastMessage(msg)

            # Create player.
            elif unitId not in self.gameState.positions:
                self.gameState.addUnit(unitId, orders[unitId])
                pos = self.gameState.getPos(unitId)

                msg = messages.NewObelisk(unitId, pos)
                self.connectionManager.broadcastMessage(msg)

            # Move player.
            else:
                dest = orders[unitId]
                pos = self.gameState.getPos(unitId)
                # Don't try to move to the current position.
                while dest == pos:
                    self.unitOrders.removeNextOrder(unitId)
                    dest = self.unitOrders.getNextOrder(unitId)
                # log.debug("Moving unit {} (at {}) toward {}."
                #           .format(unitId, pos, dest))
                # If there are no more orders, don't move.
                if dest is None:
                    continue
                # POS_INT_CHECK
                for k in dest:
                    assert type(k) is int

                self.gameState.moveUnitToward(unitId, dest)
                pos = self.gameState.getPos(unitId)
                # TODO: Maybe only broadcast the new position if we handled a
                # valid command? Else the position isn't changed....
                msg = messages.SetPos(unitId, pos)
                self.connectionManager.broadcastMessage(msg)

