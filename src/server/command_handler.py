from src.shared import messages
from src.shared.gameState import GameState
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage

log = newLogger(__name__)


class CommandHandler(object):
    def __init__(self, connectionManager):
        self.gameState = GameState()
        self.connectionManager = connectionManager

    def broadcastMessage(self, message):
        self.connectionManager.broadcastMessage(message)

    def sendMessage(self, playerId, message):
        self.connectionManager.sendMessage(playerId, message)

    def createConnection(self, playerId):
        self.gameState.addPlayer(playerId, (0, 0))
        pos = self.gameState.getPos(playerId)

        self.sendMessage(playerId, messages.YourIdIs(playerId))
        self.broadcastMessage(messages.NewObelisk(playerId, pos))
        for otherId in self.gameState.positions:
            # We already broadcast this one to everyone, including ourself.
            if otherId == playerId:
                continue
            otherPos = self.gameState.getPos(otherId)
            self.sendMessage(playerId, messages.NewObelisk(otherId, otherPos))

    def removeConnection(self, playerId):
        self.gameState.removePlayer(playerId)
        self.broadcastMessage(messages.DeleteObelisk(playerId))

    def stringReceived(self, playerId, data):
        # command = data.strip().lower()

        # STEP_SIZE = 1.0
        # RELATIVE_MOVES = {
        #     'n': [ 0.0,        STEP_SIZE],
        #     's': [ 0.0,       -STEP_SIZE],
        #     'e': [ STEP_SIZE,        0.0],
        #     'w': [-STEP_SIZE,        0.0],
        # }

        # if command in RELATIVE_MOVES:
        #     self.gameState.movePlayerBy(playerId,
        #                                 RELATIVE_MOVES[command])

        # else:
        #     newPos = decodePosition(command)
        #     if newPos is not None:
        #         self.gameState.movePlayerTo(playerId, newPos)

        message = deserializeMessage(data, errorOnFail=False)
        if isinstance(message, messages.MoveTo):
            self.gameState.movePlayerTo(playerId, message.dest)

            # TODO: Maybe only broadcast the new position if we handled a valid
            # command? Else the position isn't changed....
            pos = self.gameState.getPos(playerId)
            self.broadcastMessage(messages.SetPos(playerId, pos))
        else:
            log.warning("Unrecognized message from client {id}: {data!r}."
                        .format(id=playerId, data=data))
