from src.shared import messages
from src.shared.game_state import GameState
from src.shared.unit_orders import UnitOrders
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    invalidData, invalidMessage, InvalidMessageError

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
        for otherId in self.gameState.positions:
            # We will broadcast this one to everyone, including ourself.
            if otherId == playerId:
                continue
            otherPos = self.gameState.getPos(otherId)
            self.sendMessage(playerId, messages.NewObelisk(otherId, otherPos))

        self.unitOrders.giveOrder(playerId, (0, 0))

    def removeConnection(self, playerId):
        self.unitOrders.giveOrder(playerId, None)

    def stringReceived(self, playerId, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.MoveTo):
                self.unitOrders.giveOrder(playerId, message.dest)
            else:
                invalidMessage(message, log,
                               sender="client {id}".format(playerId))
        except InvalidMessageError:
            # TODO: Log error message.
            invalidData(data, log, sender="client {id}".format(playerId))

    def applyOrders(self):
        # TODO: Refactor this.
        orders = self.unitOrders.getOrders()
        for playerId in orders:
            # Remove player.
            if orders[playerId] is None:
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
                self.gameState.movePlayerToward(playerId, dest)

                pos = self.gameState.getPos(playerId)
                if pos != dest:
                    # Need to keep moving on the next turn.
                    # TODO: Probably shouldn't've removed the order in the
                    # first place....
                    self.unitOrders.giveOrder(playerId, dest)

                # TODO: Maybe only broadcast the new position if we handled a
                # valid command? Else the position isn't changed....
                self.broadcastMessage(messages.SetPos(playerId, pos))
