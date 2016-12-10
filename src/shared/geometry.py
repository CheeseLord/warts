"""
Functions for doing geometry calculations in the various types of coordinates
shared between client and server.
"""

from Queue import Queue

from src.shared.config import CHUNK_SIZE
from src.shared.exceptions import NoPathToTargetError

def findPath(gameState, srcPos, destPos):
    """
    Compute and return a path from srcPos to destPos, avoiding any obstacles.

    The returned path will be a list of waypoints such that a unit at srcPos
    could travel by straight line to each of the waypoints in order and thus
    get to destPos without hitting any obstacles.
    """

    # We indicate that a chunk hasn't been visited yet by setting its parent to
    # this special value.
    UNVISITED  = (-1, -1)

    srcChunk  = unitToChunk(srcPos)
    destChunk = unitToChunk(destPos)

    # If the source and dest points are in the same chunk, there's no point
    # doing a chunk-based search to find a path, because the result will be
    # trivial. Just go straight to the dest.
    if srcChunk == destChunk:
        return [destPos]

    # This list actually serves 2 purposes. First, it keeps track of which
    # chunks have been visited already. Second, for those that have been
    # visited, it tracks which chunk came before it in the shortest path from
    # the srcChunk to it.
    chunkWidth, chunkHeight = gameState.sizeInChunks
    parents = [[UNVISITED for y in range(chunkHeight)]
               for x in range(chunkWidth)]

    # Queue of chunks that we still need to search outward from.
    chunksToCheck = Queue()
    chunksToCheck.put(srcChunk)

    # Perform a breadth-first search.
    # TODO [#11]: Use A* instead.
    while not chunksToCheck.empty():
        currChunk = chunksToCheck.get()
        if currChunk == destChunk:
            break
        for neighbor in _getNeighbors(currChunk):
            nx, ny = neighbor
            if      gameState.chunkInBounds(neighbor) and \
                    parents[nx][ny] == UNVISITED and \
                    gameState.chunkIsPassable(neighbor):
                chunksToCheck.put(neighbor)
                parents[nx][ny] = currChunk

    destCX, destCY = destChunk
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

