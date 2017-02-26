from collections import defaultdict

from src.shared.ident import UnitId, unitToPlayer, getUnitSubId

class UnitSet(object):
    def __init__(self, units=None):
        super(UnitSet, self).__init__()
        if units is None:
            units = []
        self.units = defaultdict(set)
        self.addMany(units)

    def serialize(self):
        desc = ""
        isFirst = True
        for playerId in sorted(self.units.keys()):
            part = ""
            if not isFirst:
                part += ","
            isFirst = False
            part += str(playerId)
            part += ":"
            part += _serializeSubIds(self.units[playerId])
            desc += part
        return desc

    @classmethod
    def deserialize(cls, desc):
        ret = cls()
        for part in desc.split(","):
            playerId, _, subIdDesc = part.partition(":")
            subIds = _deserializeSubIds(subIdDesc)
            ret._addManyHomogeneous(int(playerId), subIds)
        return ret

    # TODO: Optimize better. Make use of _addManyHomogeneous if there's a lot
    # of units? Or just expose that one as a public method....
    def addMany(self, units):
        for unit in units:
            self.add(unit)

    def _addManyHomogeneous(self, playerId, subIds):
        self.units[playerId].update(subIds)

    def add(self, unit):
        assert isinstance(unit, UnitId)
        playerId = unitToPlayer(unit)
        subId    = getUnitSubId(unit)
        self.units[playerId].add(subId)

    def remove(self, unit):
        assert isinstance(unit, UnitId)
        playerId = unitToPlayer(unit)
        subId    = getUnitSubId(unit)
        self.units[playerId].remove(subId)
        if not self.units[playerId]:
            del self.units[playerId]

    def __len__(self):
        count = 0
        for units in self.units.values():
            count += len(units)
        return count

    def __contains__(self, unit):
        assert isinstance(unit, UnitId)
        playerId = unitToPlayer(unit)
        subId    = getUnitSubId(unit)
        return (subId in self.units[playerId])

    def __iter__(self):
        for playerId in sorted(self.units.keys()):
            for subId in sorted(self.units[playerId]):
                yield UnitId(playerId, subId)

    def __repr__(self):
        s = "{"
        isFirst = True
        for playerId in sorted(self.units.keys()):
            part = ""
            if not isFirst:
                part += ", "
            isFirst = False
            part += repr(playerId) + ": " + repr(sorted(self.units[playerId]))
            s += part
        s += "}"
        return s

def _serializeSubIds(subIds):
    """
    Serialize a set of unit subIds, without regard for the playerId.
    """

    val = 0
    for i in subIds:
        val |= (1 << i)
    return "{:x}".format(val)

def _deserializeSubIds(desc):
    """
    Serialize a set of unit subIds, without regard for the playerId.
    """

    val = int(desc, 16)
    ret = []
    subId = 0
    bit   = 1
    while bit <= val:
        if val & bit:
            ret.append(subId)
        bit   <<= 1
        subId  += 1
    return ret

