from src.shared import messages
from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import findPath
from src.shared.unit_orders import UnitOrders
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, InvalidMessageError

log = newLogger(__name__)


class CommandHandler(object):
    def __init__(self, connectionManager):
        super(CommandHandler, self).__init__()

        self.gameState = GameState()
        self.unitOrders = UnitOrders()
        self.connectionManager = connectionManager

    def broadcastMessage(self, message):
        self.connectionManager.broadcastMessage(message)

    def sendMessage(self, playerId, message):
        self.connectionManager.sendMessage(playerId, message)

    def createConnection(self, playerId):
        self.sendMessage(playerId, messages.YourIdIs(playerId))

        # Send ground info.
        for x in range(len(self.gameState.groundTypes)):
            for y in range(len(self.gameState.groundTypes[x])):
                groundType = self.gameState.groundTypes[x][y]
                msg = messages.GroundInfo((x, y), groundType)
                self.sendMessage(playerId, msg)

        # Send positions of all existing obelisks.
        for otherId in self.gameState.positions:
            # The gameState does not yet know about this new player, so their
            # id should not be in the gameState's mapping.
            assert otherId != playerId
            otherPos = self.gameState.getPos(otherId)
            self.sendMessage(playerId, messages.NewObelisk(otherId, otherPos))

        self.unitOrders.giveOrders(playerId, [(0, 0)])

    def removeConnection(self, playerId):
        self.unitOrders.giveOrders(playerId, None)

    def stringReceived(self, playerId, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.MoveTo):
                try:
                    srcPos = self.gameState.getPos(playerId)
                    path = findPath(self.gameState, srcPos, message.dest)
                    log.debug("Issuing orders to player {}: {}."
                              .format(playerId, path))
                    self.unitOrders.giveOrders(playerId, path)
                except NoPathToTargetError:
                    log.debug("Can't order player {} to {}: no path to target."
                              .format(playerId, message.dest))
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
        for playerId in orders:
            # Remove player.
            if orders[playerId] is None:
                # If a client manages to connect then disconnect within a
                # single tick, then it's possible the only order we'll ever
                # execute for their obelisk is the "remove" order, without
                # having first created it. In that case, we can't remove the
                # obelisk, because it doesn't exist: gameState.removePlayer
                # would crash if we tried and the clients would be confused if
                # we sent them a DeleteObelisk message for an unused id.
                if self.gameState.isIdValid(playerId):
                    self.gameState.removePlayer(playerId)
                    self.broadcastMessage(messages.DeleteObelisk(playerId))

            # Create player.
            elif playerId not in self.gameState.positions:
                self.gameState.addPlayer(playerId, orders[playerId])
                pos = self.gameState.getPos(playerId)

                self.broadcastMessage(messages.NewObelisk(playerId, pos))

            # Move player.
            else:
                dest = orders[playerId]
                pos = self.gameState.getPos(playerId)
                # Don't try to move to the current position.
                while dest == pos:
                    self.unitOrders.removeNextOrder(playerId)
                    dest = self.unitOrders.getNextOrder(playerId)
                # log.debug("Moving player {} (at {}) toward {}."
                #           .format(playerId, pos, dest))
                # If there are no more orders, don't move.
                if dest is None:
                    continue
                # POS_INT_CHECK
                for k in dest:
                    assert type(k) is int

                self.gameState.movePlayerToward(playerId, dest)
                pos = self.gameState.getPos(playerId)
                # TODO: Maybe only broadcast the new position if we handled a
                # valid command? Else the position isn't changed....
                self.broadcastMessage(messages.SetPos(playerId, pos))

