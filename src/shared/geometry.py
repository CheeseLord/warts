"""
Functions for doing geometry calculations in the various types of coordinates
shared between client and server.
"""

import heapq
import math

from src.shared.config import CHUNK_SIZE, BUILD_SIZE
from src.shared.exceptions import NoPathToTargetError
from src.shared.logconfig import newLogger

log = newLogger(__name__)

BUILDS_PER_CHUNK = CHUNK_SIZE / BUILD_SIZE

# Costs used by pathfinding code.
# Measure distances in unit coordinates.
ORTHOGONAL_COST = CHUNK_SIZE
DIAGONAL_COST   = int(ORTHOGONAL_COST * math.sqrt(2))

def findPath(gameState, srcPos, destPos):
    """
    Compute and return a path from srcPos to destPos, avoiding any obstacles.

    The returned path will be a list of waypoints such that a unit at srcPos
    could travel by straight line to each of the waypoints in order and thus
    get to destPos without hitting any obstacles.
    """

    log.debug("Searching for path from %s to %s", srcPos, destPos)

    chunkWidth, chunkHeight = gameState.sizeInChunks

    # Value larger than any actual distance.
    farFarAway = ORTHOGONAL_COST**2 * chunkWidth * chunkHeight

    srcChunk  = srcPos.chunk
    destChunk = destPos.chunk
    srcCX,  srcCY  = srcChunk
    destCX, destCY = destChunk

    # Make sure we're starting within the world.
    if not (0 <= srcCX < chunkWidth and 0 <= srcCY < chunkHeight):
        raise NoPathToTargetError("Starting point {} is outside the world."
                                  .format(srcPos))

    # If the source and dest points are in the same chunk, there's no point
    # doing a chunk-based search to find a path, because the result will be
    # trivial. Just go straight to the dest.
    if srcChunk == destChunk:
        return [destPos]

    # This list actually serves 2 purposes. First, it keeps track of which
    # chunks have been visited already. Second, for those that have been
    # visited, it tracks which chunk came before it in the shortest path from
    # the srcChunk to it.
    parents = [[None for _y in range(chunkHeight)]
               for _x in range(chunkWidth)]

    # Set to True for a node once we know we've found a shortest path to it, so
    # that we don't keep checking new paths to that node.
    nodeFinalized = [[False for _y in range(chunkHeight)]
                     for _x in range(chunkWidth)]

    # Shortest distance to each node from the start.
    distanceFromStart = [[farFarAway for _y in range(chunkHeight)]
                         for _x in range(chunkWidth)]
    distanceFromStart[srcCX][srcCY] = 0

    # Priority queue of chunks that we still need to search outward from, where
    # priority = distance from start + heuristic distance to end.
    chunksToCheck = []
    heapq.heappush(chunksToCheck, (_heuristicDistance(srcChunk, destChunk),
                                   srcChunk))

    while len(chunksToCheck) > 0:
        _, currChunk = heapq.heappop(chunksToCheck)
        log.debug("Pathfinding: search out from %s", currChunk)
        if currChunk == destChunk:
            break
        cx, cy = currChunk
        if nodeFinalized[cx][cy]:
            # Already expanded from this node; don't do it again.
            continue
        nodeFinalized[cx][cy] = True

        log.debug("Pathfinding: checking neighbors.")
        for addlDist, neighbor in _getValidNeighbors(currChunk, gameState):
            log.debug("Pathfinding: trying %s", neighbor)
            nx, ny = neighbor
            neighborStartDist = distanceFromStart[cx][cy] + addlDist
            if neighborStartDist < distanceFromStart[nx][ny]:
                log.debug("Pathfinding: found shorter path to neighbor.")
                distanceFromStart[nx][ny] = neighborStartDist
                parents[nx][ny] = currChunk
                neighborFwdDist = _heuristicDistance(neighbor, destChunk)
                neighborEstCost = neighborStartDist + neighborFwdDist
                heapq.heappush(chunksToCheck, (neighborEstCost, neighbor))

    if      (not _chunkInBounds(gameState, destChunk)) or \
            parents[destCX][destCY] is None:
        raise NoPathToTargetError("No path exists from {} to {}."
                                  .format(srcPos, destPos))

    # Build the list of waypoints backward, by following the trail of parents
    # all the way from dest to source.
    lim = chunkWidth * chunkHeight
    waypoints = []
    currChunk = destChunk

    while currChunk != srcChunk:
        waypoints.append(currChunk)
        cx, cy = currChunk
        currChunk = parents[cx][cy]
        assert currChunk is not None

        # If there's a bug, crash rather than hanging (it's easier to debug).
        lim -= 1
        assert lim >= 0, "Infinite loop detected in findPath"

    # Reverse the list of waypoints, since currently it's backward.
    waypoints.reverse()

    # Now convert the chunk coordinates to unit coordinates.
    waypoints = [Coord.fromCBU(chunk=chunk).chunkCenter for chunk in waypoints]

    # Note: The very first waypoint is still valid, because it's in a chunk
    # orthogonally adjacent to the chunk containing the source point, so
    # there's definitely not an obstacle in between.

    # We still need to correct the last waypoint, which is currently the center
    # of the dest chunk rather than the actual dest point. Note that we already
    # handled the case where srcChunk == destChunk, so waypoints can't be
    # empty.
    waypoints[-1] = destPos

    return waypoints

def _heuristicDistance(chunkA, chunkB):
    """
    Return a heuristic estimate of the distance between chunk A and chunk B,
    in *unit coordinates*.
    """

    # Use Euclidean distance as the heuristic.
    ax, ay = chunkA
    bx, by = chunkB
    deltaX = ORTHOGONAL_COST * (bx - ax)
    deltaY = ORTHOGONAL_COST * (by - ay)
    return int(math.hypot(deltaX, deltaY))

# Helper function for findPath.
def _getValidNeighbors(chunkPos, gameState):
    x, y = chunkPos

    # The 8 neighbors, separated into those orthogonally adjaent and those
    # diagonally adjacent. Within each category, the particular neighbors are
    # in random order.
    diagonals = [
        (x - 1, y + 1), # northwest
        (x + 1, y - 1), # southeast
        (x - 1, y - 1), # southwest
        (x + 1, y + 1), # northeast
    ]
    orthogonals = [
        (x,     y - 1), # south
        (x,     y + 1), # north
        (x + 1, y    ), # east
        (x - 1, y    ), # west
    ]

    # Try diagonals first, so that when crossing a non-square rectangle we do
    # the diagonal part of the path before the orthogonal part.
    for neighbor in diagonals:
        if      _chunkInBounds(gameState, neighbor) and \
                _chunkIsPassable(gameState, neighbor):
            # Check that the other two corners of the square are passable, so
            # we don't try to move through zero-width spaces in cases like:
            #     @@ B
            #     @@/
            #      /@@
            #     A @@
            nx, ny = neighbor
            if      _chunkIsPassable(gameState, ( x, ny)) and \
                    _chunkIsPassable(gameState, (nx,  y)):
                yield (DIAGONAL_COST, neighbor)
    for neighbor in orthogonals:
        if      _chunkInBounds(gameState, neighbor) and \
                _chunkIsPassable(gameState, neighbor):
            yield (ORTHOGONAL_COST, neighbor)

def _chunkInBounds(gameState, chunkPos):
    return gameState.inBounds(Coord.fromCBU(chunk=chunkPos))

def _chunkIsPassable(gameState, chunkPos):
    return gameState.isPassable(Coord.fromCBU(chunk=chunkPos))


class AbstractCoord(object):
    def __init__(self, uPos):
        super(AbstractCoord, self).__init__()
        self.x, self.y = uPos

    @classmethod
    def fromUnit(cls, unit):
        return cls(unit)

    @classmethod
    def fromCBU(cls, chunk=(0,0), build=(0,0), unit=(0,0)):
        cx, cy = chunk
        bx, by = build
        ux, uy = unit
        x = cx * CHUNK_SIZE + bx * BUILD_SIZE + ux
        y = cy * CHUNK_SIZE + by * BUILD_SIZE + uy
        return cls((x, y))

    @property
    def chunk(self):
        return (self.x // CHUNK_SIZE, self.y // CHUNK_SIZE)

    @property
    def build(self):
        return (self.x // BUILD_SIZE, self.y // BUILD_SIZE)

    @property
    def unit(self):
        return (self.x, self.y)

    @property
    def buildSub(self):
        return ((self.x % CHUNK_SIZE) // BUILD_SIZE,
                (self.y % CHUNK_SIZE) // BUILD_SIZE)

    @property
    def unitSub(self):
        return (self.x % BUILD_SIZE, self.y % BUILD_SIZE)

    @property
    def truncToChunk(self):
        return self.fromCBU(chunk=self.chunk)

    @property
    def truncToBuild(self):
        return self.fromCBU(build=self.build)

    def serialize(self):
        return [str(int(x)) for x in self.unit]

    @classmethod
    def deserialize(cls, descs):
        assert len(descs) == 2
        return cls.fromUnit(map(int, descs))

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.x, self.y)

    def __str__(self):
        cx, cy = self.chunk
        bx, by = self.build
        ux, uy = self.unit
        return "({cx}.{bx}.{ux}, {cy}.{by}.{uy})".format(
            cx=cx, cy=cy, bx=bx, by=by, ux=ux, uy=uy
        )

    def __eq__(self, rhs):
        if not isinstance(self, type(rhs)) and not isinstance(rhs, type(self)):
            raise TypeError("Cannot compare {} with {}.".format(
                type(self), type(rhs)
            ))
        return self.x == rhs.x and self.y == rhs.y

    def __ne__(self, rhs):
        if not isinstance(self, type(rhs)) and not isinstance(rhs, type(self)):
            raise TypeError("Cannot compare {} with {}.".format(
                type(self), type(rhs)
            ))
        return self.x != rhs.x and self.y != rhs.y

    # Coord + Coord = err
    # Coord + Dist  = Coord
    # Dist  + Coord = Coord
    # Dist  + Dist  = Dist
    #
    # Coord - Coord = Dist
    # Coord - Dist  = Coord
    # Dist  - Coord = err
    # Dist  - Dist  = Dist
    #
    #       - Coord = err
    #       - Dist  = Dist

    def __add__(self, rhs):
        if isinstance(self, Coord) and isinstance(rhs, Coord):
            raise TypeError("Cannot add two Coords.")
        elif isinstance(self, Distance) and isinstance(rhs, Distance):
            retType = Distance
        else:
            # Coord + Distance or Distance + Coord
            retType = Coord

        x = self.x + rhs.x
        y = self.y + rhs.y
        return retType((x, y))

    def __sub__(self, rhs):
        if isinstance(self, Coord) == isinstance(rhs, Coord):
            # Coord - Coord or Distance - Distance
            retType = Distance
        elif isinstance(self, Coord):
            # Coord - Distance
            retType = Coord
        else:
            # Distance - Coord
            raise TypeError("Cannot subtract Distance - Coord.")

        x = self.x - rhs.x
        y = self.y - rhs.y
        return retType((x, y))

class Distance(AbstractCoord):
    def length(self):
        "Return the Euclidean length of this Distance."
        return math.hypot(self.x, self.y)

    def __neg__(self):
        x = - self.x
        y = - self.y
        return Distance((x, y))

    def __rmul__(self, lhs):
        if not isinstance(lhs, int) and not isinstance(lhs, float):
            raise TypeError("Cannot multiply Distance by {}.".format(
                type(lhs)
            ))
        return Distance((int(round(self.x * lhs)), int(round(self.y * lhs))))

    def __mul__(self, rhs):
        return rhs * self

class Coord(AbstractCoord):
    @property
    def chunkCenter(self):
        """
        Return the Coord of the center of the chunk containing this Coord.
        """
        return self.fromCBU(chunk=self.chunk,
                            unit=(CHUNK_SIZE // 2, CHUNK_SIZE // 2))

