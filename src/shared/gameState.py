class GameState:
    def __init__(self):
        self.positions = {}

    def addPlayer(self, playerId, position):
        if playerId in self.positions:
            raise ValueError("There's already a player with id {}."
                             .format(playerId))
        self.positions[playerId] = position

    def removePlayer(self, playerId):
        self.checkId(playerId)
        del self.positions[playerId]

    def movePlayerBy(self, playerId, deltaPos):
        self.checkId(playerId)
        x, y = self.getPos(playerId)
        dx, dy = deltaPos
        x += dx
        y += dy
        self.movePlayerTo(playerId, (x, y))

    def movePlayerTo(self, playerId, newPos):
        self.checkId(playerId)
        self.positions[playerId] = newPos

    def getPos(self, playerId):
        self.checkId(playerId)
        return self.positions[playerId]

    def checkId(self, playerId):
        if playerId not in self.positions:
            raise ValueError("There's no player with id {}.".format(playerId))
