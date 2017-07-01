from collections import defaultdict
import math

from src.shared.ident import UnitId, unitToPlayer, getUnitSubId

class GameState:
    def __init__(self, mapSize):
        self.positions = {}
        self.resources = defaultdict(int)

        self.mapSize = tuple(mapSize)
        mapWidth, mapHeight = self.mapSize
        # Reference chunks as [x][y].
        self.groundTypes = [[0 for y in range(mapHeight)]
                            for x in range(mapWidth)]
        self.resourcePools = []

    @property
    def sizeInChunks(self):
        return self.mapSize

    def chunkInBounds(self, cPos):
        x, y = cPos
        return (0 <= x < len(self.groundTypes) and
                0 <= y < len(self.groundTypes[0]))

    def chunkIsPassable(self, cPos):
        x, y = cPos
        return self.chunkInBounds(cPos) and self.groundTypes[x][y] == 0

    def addUnit(self, playerId, position):
        unitId = self.createNewUnitId(playerId)
        assert unitId not in self.positions

        self.positions[unitId] = position
        return unitId

    def removeUnit(self, unitId):
        self.checkId(unitId)
        del self.positions[unitId]

    def moveUnitToward(self, unitId, dest):
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
        self.moveUnitTo(unitId, newPos)

    # Does anyone actually use this function?
    def moveUnitBy(self, unitId, deltaPos):
        self.checkId(unitId)
        x, y = self.getPos(unitId)
        dx, dy = deltaPos
        x += dx
        y += dy
        self.moveUnitTo(unitId, (x, y))

    def moveUnitTo(self, unitId, newPos):
        self.checkId(unitId)
        # POS_INT_CHECK
        for k in newPos:
            assert type(k) is int
        self.positions[unitId] = newPos

    def getPos(self, unitId):
        self.checkId(unitId)
        return self.positions[unitId]

    # Internal helper function to generate a new unit id.
    def createNewUnitId(self, playerId):
        # For now, just return 1 + max(all existing unit ids for playerId)
        # TODO: Randomize it better, to avoid the German tank problem.
        highest = -1
        for unitId in self.getAllUnitsForPlayer(playerId):
            highest = max(highest, getUnitSubId(unitId))
        return UnitId(playerId, 1 + highest)

    def getAllUnitsForPlayer(self, playerId):
        for unitId in self.getAllUnits():
            if unitToPlayer(unitId) == playerId:
                yield unitId

    def getAllUnits(self):
        for unitId in self.positions.keys():
            yield unitId

    def checkId(self, unitId):
        if not self.isUnitIdValid(unitId):
            raise ValueError("There's no unit with id {}.".format(unitId))

    def isUnitIdValid(self, unitId):
        return unitId in self.positions

