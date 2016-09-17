from src.shared.encode import decodePosition


class CommandHandler(object):
    def __init__(self, gameState, connectionManager):
        self.gameState = gameState
        self.connectionManager = connectionManager

    def broadcastMessage(self, *args, **kwargs):
        self.connectionManager.broadcastMessage(*args, **kwargs)

    def sendMessage(self, *args, **kwargs):
        self.connectionManager.sendMessage(*args, **kwargs)

    def createConnection(self, playerId):
        playerX, playerY = self.gameState.getPos(playerId)

        self.sendMessage(playerId, "your_id_is", [playerId])
        self.broadcastMessage("new_obelisk", [playerX, playerY])
        for otherId in self.gameState.positions:
            # We already broadcast this one to everyone, including ourself.
            if otherId == playerId:
                continue
            otherX, otherY = self.gameState.getPos(otherId)
            self.sendMessage("new_obelisk", [otherId, otherX, otherY])

    def removeConnection(self, playerId):
        self.broadcastMessage("delete_obelisk", [playerId])
        self.gameState.removePlayer(playerId)

    def stringReceived(self, playerId, data):
        command = data.strip().lower()

        STEP_SIZE = 1.0
        RELATIVE_MOVES = {
            'n': [ 0.0,        STEP_SIZE],
            's': [ 0.0,       -STEP_SIZE],
            'e': [ STEP_SIZE,        0.0],
            'w': [-STEP_SIZE,        0.0],
        }

        if command in RELATIVE_MOVES:
            self.gameState.movePlayerBy(playerId,
                                        RELATIVE_MOVES[command])

        else:
            newPos = decodePosition(command)
            if newPos is not None:
                self.gameState.movePlayerTo(playerId, newPos)

        # TODO: Maybe only broadcast the new position if we handled a valid
        # command? Else the position isn't changed....
        playerX, playerY = self.gameState.getPos(playerId)
        self.broadcastMessage("set_pos", [playerId, playerX, myY])
