class UserDefinedError(StandardError):
    pass

# Used when the pathfinding code can't find a path between the points given to
# it.
class NoPathToTargetError(UserDefinedError):
    pass
