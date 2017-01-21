import pytest

from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import chunkToUnit, unitToChunk, getChunkCenter
from src.shared.geometry import findPath


# TODO: Add the following new tests:
#
#
#   ..@..
#   A.@.B
#   ..@..
#
#
#   @@@@@@@@@@@
#   @.........@
#   @.......B.@
#   @..@@.....@
#   @..@@....@@
#   @.......@@@
#   @......@@@@
#   @.....@@@@@
#   @.A..@@@@@@
#   @...@@@@@@@
#   @@@@@@@@@@@
#
#
#   @@@@@@
#   @@@@B@
#   @@@@.@
#   @@@@.@
#   @A...@
#   @@@@@@
#
#
#   @@@@@@@
#   @@..B.@
#   @.@...@
#   @..@..@
#   @A..@.@
#   @.....@
#   @@@@@@@
#
#
#   @@@@@@@@@
#   @.......@
#   @...@...@
#   @...@...@
#   @.A.@.B.@
#   @...@...@
#   @.......@
#   @@@@@@@@@



class TestBasics:
    """
    Make sure the path finding never tries to send units through obstacles.
    """

    def test_tbone(self):
        # Note: the actual layout is transposed relative to this array!
        # TODO: We need a function that takes in an ASCII-art description of
        # what the test should look like and sets up the gameState, srcPos, and
        # destPos. Else we're never going to get all the coordinates right.
        groundTypes = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 1, 0, 0, 1],
            [1, 0, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        gameState = GameState(groundTypes=groundTypes)

        srcPos  = getChunkCenter((1, 2))
        destPos = getChunkCenter((1, 4))

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Check that none of the lines between waypoints pass through
        # impassible ground.

    def test_diagonallyBlocked(self):
        groundTypes = [
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 0, 0, 1],
            [1, 1, 1, 0, 0, 1],
            [1, 0, 0, 1, 1, 1],
            [1, 0, 0, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
        ]
        gameState = GameState(groundTypes=groundTypes)

        srcPos  = getChunkCenter((1, 4))
        destPos = getChunkCenter((4, 2))

        with pytest.raises(NoPathToTargetError):
            findPath(gameState, srcPos, destPos)


def checkWaypointsPassable(path, groundTypes):
    for unitPos in path:
        x, y = unitToChunk(unitPos)
        assert groundTypes[x][y] == 0



# Give a couple options for each one, since we've used a couple different
# notations in the past.
PASSABLE_DESCS   = (".", " ")
IMPASSABLE_DESCS = ("#", "@")

def parseTestCase(desc):
    assert type(desc) == str
    lines = desc.strip().split("\n")

    # Determine dimensions
    height = len(lines)
    widths = set(map(len, lines))
    assert len(widths) == 1
    width = next(iter(widths))

    pointsOfInterest = {}

    # Actually parse the description.
    groundTypes = [[None for y in range(height)] for x in range(width)]
    for y in range(height):
        for x in range(width):
            locDesc = lines[height - 1 - y][x]
            # TODO: Magic numbers bad.
            if locDesc in IMPASSABLE_DESCS:
                groundTypes[x][y] = 1
            elif locDesc in PASSABLE_DESCS:
                groundTypes[x][y] = 0
            elif locDesc.isalpha():
                # Points of interest are always passable, at least for now.
                groundTypes[x][y] = 0
                assert locDesc not in pointsOfInterest
                pointsOfInterest[locDesc] = (x, y)

    return (groundTypes, pointsOfInterest)

