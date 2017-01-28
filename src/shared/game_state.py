import math

class GameState:
    def __init__(self, groundTypes=None):
        self.positions = {}

        self.groundTypes = groundTypes
        if self.groundTypes is None:
            # 10x5. Stored [x][y].
            # TODO [#3]: Magic numbers bad.
            self.groundTypes = [[0 for y in range(5)] for x in range(10)]
            self.groundTypes[5][3] = 1

            # Some more impassable squares, to better exercise the pathfinding.
            self.groundTypes[1][1] = 1
            self.groundTypes[1][2] = 1
            self.groundTypes[1][3] = 1
            self.groundTypes[2][3] = 1
            self.groundTypes[3][2] = 1

    @property
    def sizeInChunks(self):
        # Note: don't allow a map where either dimension is zero.
        return (len(self.groundTypes), len(self.groundTypes[0]))

    def chunkInBounds(self, cPos):
        x, y = cPos
        return (0 <= x < len(self.groundTypes) and
                0 <= y < len(self.groundTypes[0]))

    def chunkIsPassable(self, cPos):
        x, y = cPos
        return self.chunkInBounds(cPos) and self.groundTypes[x][y] == 0

    # FIXME: Rename this.
    def addPlayer(self, unitId, position):
        if unitId in self.positions:
            raise ValueError("There's already a unit with id {}."
                             .format(unitId))

        # POS_INT_CHECK
        for k in position:
            assert type(k) is int
        self.positions[unitId] = position

    # FIXME: Rename this.
    def removePlayer(self, unitId):
        self.checkId(unitId)
        del self.positions[unitId]

    # FIXME: Rename this.
    def movePlayerToward(self, unitId, dest):
        # TODO: Take in elapsed ticks; have an actual speed, rather than a
        # constant "move amount per update".
        MAX_SPEED = 3.0

        self.checkId(unitId)

        oldPos = self.getPos(unitId)
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

        newPos = tuple(int(round(x)) for x in newPos)
        self.movePlayerTo(unitId, newPos)

    # FIXME: Rename this.
    # Does anyone actually use this function?
    def movePlayerBy(self, unitId, deltaPos):
        self.checkId(unitId)
        x, y = self.getPos(unitId)
        dx, dy = deltaPos
        x += dx
        y += dy
        self.movePlayerTo(unitId, (x, y))

    # FIXME: Rename this.
    def movePlayerTo(self, unitId, newPos):
        self.checkId(unitId)
        # POS_INT_CHECK
        for k in newPos:
            assert type(k) is int
        self.positions[unitId] = newPos

    def getPos(self, unitId):
        self.checkId(unitId)
        return self.positions[unitId]

    def checkId(self, unitId):
        if not self.isIdValid(unitId):
            raise ValueError("There's no unit with id {}.".format(unitId))

    def isIdValid(self, unitId):
        return unitId in self.positions

