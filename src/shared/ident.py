class UnitId:
    def __init__(self, playerId, unitSubId):
        assert playerId  >= 0
        assert unitSubId >= 0
        self.playerId = playerId
        self.subId    = unitSubId

    def __eq__(self, other):
        return self.playerId == other.playerId and self.subId == other.subId

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.playerId, self.subId))

    def __repr__(self):
        return repr((self.playerId, self.subId))

# TODO: These names sound like they're for coordinate conversions. Need to put
# an actual noun somewhere in the name.
def unitToPlayer(unitId):
    return unitId.playerId

def getUnitSubId(unitId):
    return unitId.subId

# For using UnitIds in messages
def encodeUnitId(unitId):
    return (str(unitId.playerId), str(unitId.subId))

def parseUnitId(words):
    # TODO: Somewhere higher up, handle all exceptions in parsing functions and
    # turn them into InvalidMessageErrors. Do we do this already?
    playerId, subId = map(int, words)
    return UnitId(playerId, subId)
