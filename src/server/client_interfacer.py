from collections import defaultdict

from src.shared.exceptions import NoPathToTargetError
from src.shared.geometry import findPath
from src.shared.ident import unitToPlayer
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    badEMessageArgument, illFormedEMessage, badEMessageCommand, \
    InvalidMessageError
from src.shared import messages
from src.shared.unit_orders import DelUnitOrder, MoveUnitOrder

log = newLogger(__name__)

# TODO[#10]: Why is this in GameStateManager?
MAXIMUM_MESSAGES_PER_TICK = 10

class ClientInterfacer(object):
    def __init__(self, backend, gameStateManager, connections):
        super(ClientInterfacer, self).__init__()

        self.backend           = backend
        self.gameStateManager  = gameStateManager
        self.connectionManager = connections

        self.backend.setClientInterfacer(self)

        self.messageCounts = defaultdict(int)

    # TODO[#10]: Why is this in GameStateManager?
    def handshake(self, playerId):
        # Send map size (must come before ground info).
        msg = messages.MapSize(self.gameStateManager.gameState.sizeInChunks)
        self.connectionManager.sendMessage(playerId, msg)

        # Send ground info.
        gameState = self.gameStateManager.gameState
        for x in range(len(gameState.groundTypes)):
            for y in range(len(gameState.groundTypes[x])):
                groundType = gameState.groundTypes[x][y]
                msg = messages.GroundInfo((x, y), groundType)
                self.connectionManager.sendMessage(playerId, msg)

        # Send resource pool info.
        for pool in self.gameStateManager.gameState.resourcePools:
            msg = messages.ResourceLoc(pool)
            self.connectionManager.sendMessage(playerId, msg)

        # Send positions of all existing obelisks.
        for unitId in self.gameStateManager.gameState.positions:
            # The gameState does not yet know about this new player, so their
            # id should not be in the gameState's mapping.
            assert unitToPlayer(unitId) != playerId
            otherPos = self.gameStateManager.gameState.getPos(unitId)
            msg = messages.NewObelisk(unitId, otherPos)
            self.connectionManager.sendMessage(playerId, msg)

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
            gameState = self.gameStateManager.gameState
            if isinstance(message, messages.OrderNew):
                self.gameStateManager.unitOrders.createNewUnit(playerId,
                                                               message.pos)
            elif isinstance(message, messages.OrderDel):
                for unitId in message.unitSet:
                    # TODO: Factor out this pair of checks? We're probably
                    # going to be doing them a *lot*.
                    if not playerId == unitToPlayer(unitId):
                        badEMessageArgument(
                            message, log, clientId=playerId,
                            reason="Can't delete other player's unit"
                        )
                    elif not gameState.isUnitIdValid(unitId):
                        badEMessageArgument(message, log, clientId=playerId,
                                            reason="No such unit")
                    else:
                        self.gameStateManager.unitOrders.giveOrders(
                            unitId, [DelUnitOrder()]
                        )
            elif isinstance(message, messages.OrderMove):
                unitSet = message.unitSet
                for unitId in unitSet:
                    if not playerId == unitToPlayer(unitId):
                        badEMessageArgument(
                            message, log, clientId=playerId,
                            reason="Can't order other player's unit"
                        )
                    elif not gameState.isUnitIdValid(unitId):
                        badEMessageArgument(message, log, clientId=playerId,
                                            reason="No such unit")
                    else:
                        try:
                            srcPos = gameState.getPos(unitId)
                            path = findPath(gameState, srcPos, message.dest)
                            log.debug("Issuing orders to unit %s: %s.",
                                      unitId, path)
                            orders = map(MoveUnitOrder, path)
                            self.gameStateManager.unitOrders.giveOrders(
                                unitId, orders
                            )
                        except NoPathToTargetError:
                            log.debug("Can't order unit %s to %s: "
                                      "no path to target.",
                                      unitId, message.dest)
                            # If the target position is not reachable, just
                            # drop the command.
            else:
                badEMessageCommand(message, log, clientId=playerId)
        except InvalidMessageError as error:
            illFormedEMessage(error, log, clientId=playerId)

    def tick(self):
        self.messageCounts.clear()

