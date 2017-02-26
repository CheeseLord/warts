import pytest

from src.shared.exceptions import NoPathToTargetError
from src.shared.game_state import GameState
from src.shared.geometry import chunkToUnit, unitToChunk, getChunkCenter
from src.shared.geometry import findPath



class TestBasics:
    """
    Make sure the path finding never tries to send units through obstacles.
    """

    def test_tbone(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                #######
                #.A#B.#
                #.###.#
                #.....#
                #######
            """
        )
        # TODO: Maybe create the GameState and do the getChunkCenters in
        # parseTestCase?
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Check that none of the lines between waypoints pass through
        # impassible ground.

    def test_diagonallyBlocked(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                ######
                ###A.#
                ###..#
                #..###
                #.B###
                ######
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        with pytest.raises(NoPathToTargetError):
            findPath(gameState, srcPos, destPos)

    def test_noOutsideWall(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                ..#..
                A.#.B
                ..#..
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        with pytest.raises(NoPathToTargetError):
            findPath(gameState, srcPos, destPos)

    def test_aroundColumn(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                ###########
                #.........#
                #.......B.#
                #..##.....#
                #..##....##
                #.......###
                #......####
                #.....#####
                #.A..######
                #...#######
                ###########
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Check that we didn't take the long way around.

    def test_aroundCorner(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                ######
                ####B#
                ####.#
                ####.#
                #A...#
                ######
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Was there supposed to be some extra checking in this test? I
        # forget.

    def test_orthogWall(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                #########
                #.......#
                #...#...#
                #...#...#
                #.A.#.B.#
                #...#...#
                #.......#
                #########
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Test that we went around the shorter way.

    def test_diagWall(self):
        groundTypes, pointsOfInterest = parseTestCase(
            """
                #######
                ##..B.#
                #.#...#
                #..#..#
                #A..#.#
                #.....#
                #######
            """
        )
        gameState = GameState(groundTypes=groundTypes)
        srcPos  = getChunkCenter(pointsOfInterest["A"])
        destPos = getChunkCenter(pointsOfInterest["B"])

        path = findPath(gameState, srcPos, destPos)
        checkWaypointsPassable(path, groundTypes)

        # TODO: Test that we didn't cut through the wall.


def checkWaypointsPassable(path, groundTypes):
    for unitPos in path:
        x, y = unitToChunk(unitPos)
        assert groundTypes[x][y] == 0

    # TODO: Check that none of the lines between waypoints pass through
    # impassible ground.



# Give a couple options for each one, since we've used a couple different
# notations in the past.
PASSABLE_DESCS   = (".", " ")
IMPASSABLE_DESCS = ("#", "@")

def parseTestCase(desc):
    assert type(desc) == str
    lines = map(lambda s: s.strip(), desc.strip().split("\n"))

    # Determine dimensions
    height = len(lines)
    widths = set(map(len, lines))
    if len(widths) != 1:
        print "Error: len(widths) is {}, not 1".format(len(widths))
        print "--------"
        print lines
        print "--------"
        print widths
        print "--------"
        assert False
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

