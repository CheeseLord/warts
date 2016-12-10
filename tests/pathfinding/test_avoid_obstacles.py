from src.shared.game_state import GameState
from src.shared.geometry import findPath, chunkToUnit, unitToChunk


class TestAvoidObstacles:
    """
    Make sure the path finding never tries to send units through obstacles.
    """

    def test_tbone(self):
        groundTypes = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 1, 0, 0, 1],
            [1, 0, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        gameState = GameState(groundTypes=groundTypes)

        # TODO: Don't assume the chunks are big enough.
        srcPos  = chunkToUnit((1, 2))
        destPos = chunkToUnit((1, 4))

        path = findPath(gameState, srcPos, destPos)

        # TODO: Factor this into a function so we can test other maps.
        # Check that none of the waypoints are impassible.
        for unitPos in path:
            x, y = unitToChunk(unitPos)
            assert groundTypes[x][y] == 0
        # TODO: Check that none of the lines between waypoints pass through
        # impassible ground.

