"""
Functions for doing geometry calculations in the various types of coordinates
shared between client and server.
"""

import heapq
import math

from src.shared.config import CHUNK_SIZE
from src.shared.exceptions import NoPathToTargetError
from src.shared.logconfig import newLogger

log = newLogger(__name__)

def findPath(gameState, srcPos, destPos):
    """
    Compute and return a path from srcPos to destPos, avoiding any obstacles.

    The returned path will be a list of waypoints such that a unit at srcPos
    could travel by straight line to each of the waypoints in order and thus
    get to destPos without hitting any obstacles.
    """

    log.debug("Searching for path from {} to {}".format(srcPos, destPos))

    chunkWidth, chunkHeight = gameState.sizeInChunks

    # We indicate that a chunk hasn't been visited yet by setting its parent to
    # this special value.
    UNVISITED  = (-1, -1)
    # Value larger than any actual distance.
    FAR_FAR_AWAY = CHUNK_SIZE * CHUNK_SIZE * chunkWidth * chunkHeight

    srcChunk  = unitToChunk(srcPos)
    destChunk = unitToChunk(destPos)
    srcCX,  srcCY  = srcChunk
    destCX, destCY = destChunk

    # If the source and dest points are in the same chunk, there's no point
    # doing a chunk-based search to find a path, because the result will be
    # trivial. Just go straight to the dest.
    if srcChunk == destChunk:
        return [destPos]

    # This list actually serves 2 purposes. First, it keeps track of which
    # chunks have been visited already. Second, for those that have been
    # visited, it tracks which chunk came before it in the shortest path from
    # the srcChunk to it.
    parents = [[UNVISITED for y in range(chunkHeight)]
               for x in range(chunkWidth)]

    # Set to True for a node once we know we've found a shortest path to it, so
    # that we don't keep checking new paths to that node.
    nodeFinalized = [[False for y in range(chunkHeight)]
                      for x in range(chunkWidth)]

    # Shortest distance to each node from the start.
    distanceFromStart = [[FAR_FAR_AWAY for y in range(chunkHeight)]
                         for x in range(chunkWidth)]
    distanceFromStart[srcCX][srcCY] = 0

    # Priority queue of chunks that we still need to search outward from, where
    # priority = distance from start + heuristic distance to end.
    chunksToCheck = []
    heapq.heappush(chunksToCheck, (_heuristicDistance(srcChunk, destChunk),
                                   srcChunk))

    while len(chunksToCheck) > 0:
        _, currChunk = heapq.heappop(chunksToCheck)
        log.debug("Pathfinding: search out from {}".format(currChunk))
        if currChunk == destChunk:
            break
        cx, cy = currChunk
        if nodeFinalized[cx][cy]:
            # Already expanded from this node; don't do it again.
            continue
        nodeFinalized[cx][cy] = True

        log.debug("Pathfinding: checking neighbors.")

        for neighbor in _getNeighbors(currChunk):
            log.debug("Pathfinding: trying {}".format(neighbor))
            if      gameState.chunkInBounds(neighbor) and \
                    gameState.chunkIsPassable(neighbor):
                log.debug("Pathfinding: neighbor is valid.")
                nx, ny = neighbor
                # Distances in unit coordinates, so add CHUNK_SIZE, not 1.
                neighborStartDist = distanceFromStart[cx][cy] + CHUNK_SIZE
                if neighborStartDist < distanceFromStart[nx][ny]:
                    log.debug("Pathfinding: found shorter path to neighbor.")
                    distanceFromStart[nx][ny] = neighborStartDist
                    parents[nx][ny] = currChunk
                    neighborFwdDist = _heuristicDistance(neighbor, destChunk)
                    neighborEstCost = neighborStartDist + neighborFwdDist
                    heapq.heappush(chunksToCheck, (neighborEstCost, neighbor))

    if      (not gameState.chunkInBounds(destChunk)) or \
            parents[destCX][destCY] == UNVISITED:
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
        assert currChunk != UNVISITED

        # If there's a bug, crash rather than hanging (it's easier to debug).
        lim -= 1
        assert lim >= 0, "Infinite loop detected in findPath"

    # Reverse the list of waypoints, since currently it's backward.
    waypoints.reverse()

    # Now convert the chunk coordinates to unit coordinates.
    waypoints = map(getChunkCenter, waypoints)

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
    deltaX = CHUNK_SIZE * (bx - ax)
    deltaY = CHUNK_SIZE * (by - ay)
    return int(math.hypot(deltaX, deltaY))

# Helper function for findPath.
def _getNeighbors(chunkPos):
    x, y = chunkPos
    yield (x - 1, y)
    yield (x + 1, y)
    yield (x, y - 1)
    yield (x, y + 1)

def getChunkCenter(chunkPos):
    """
    Return the unit coordinates of the center of chunkPos.
    """
    return tuple(map(lambda x: x + CHUNK_SIZE // 2, chunkToUnit(chunkPos)))

def chunkToUnit(chunkPos):
    """
    Return the unit coordinates of the origin corner of chunkPos.
    """
    return tuple(map(lambda x: x * CHUNK_SIZE, chunkPos))

def unitToChunk(unitPos):
    """
    Return the chunk coordinates of the chunk containing unitPos.
    """
    return tuple(map(lambda x: x // CHUNK_SIZE, unitPos))

