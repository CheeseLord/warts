import math

class GameState:
    def __init__(self):
        self.positions = {}

    def addPlayer(self, playerId, position):
        if playerId in self.positions:
            raise ValueError("There's already a player with id {}."
                             .format(playerId))
        self.positions[playerId] = tuple(int(round(x)) for x in position)

    def removePlayer(self, playerId):
        self.checkId(playerId)
        del self.positions[playerId]

    def movePlayerToward(self, playerId, dest):
        # TODO: Take in elapsed ticks; have an actual speed, rather than a
        # constant "move amount per update".
        MAX_SPEED = 3.0

        self.checkId(playerId)

        oldPos = self.getPos(playerId)
        distance = math.hypot(dest[0] - oldPos[0], dest[1] - oldPos[1])
        if distance <= MAX_SPEED:
            # We have enough speed to reach our destination this tick.
            newPos = dest
        else:
            # MAX_SPEED is nonzero, and distance > MAX_SPEED, so we are not
            # dividing by zero. (Or distance is NaN, in which case
            # distance !> MAX_SPEED, but we're still not dividing by zero.)
            fraction = MAX_SPEED / distance
            newPos = (oldPos[0] + fraction * (dest[0] - oldPos[0]),
                      oldPos[1] + fraction * (dest[1] - oldPos[1]))

        self.movePlayerTo(playerId, newPos)

    def movePlayerBy(self, playerId, deltaPos):
        self.checkId(playerId)
        x, y = self.getPos(playerId)
        dx, dy = deltaPos
        x += dx
        y += dy
        self.movePlayerTo(playerId, (x, y))

    def movePlayerTo(self, playerId, newPos):
        self.checkId(playerId)
        self.positions[playerId] = tuple(int(round(x)) for x in newPos)

    def getPos(self, playerId):
        self.checkId(playerId)
        return self.positions[playerId]

    def checkId(self, playerId):
        if playerId not in self.positions:
            raise ValueError("There's no player with id {}.".format(playerId))

