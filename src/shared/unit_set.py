from collections import defaultdict

from src.shared.ident import UnitId, unitToPlayer, getUnitSubId

class UnitSet(object):
    def __init__(self, units=[]):
        super(UnitSet, self).__init__()
        self.units = set()
        # TODO: This.
        # self.units = defaultdict(set)
        self.addMany(units)

    def serialize(self):
        # TODO
        NotImplemented

    @classmethod
    def deserialize(cls, desc):
        # TODO
        NotImplemented

    def addMany(self, units):
        for unit in units:
            self.add(unit)

    def add(self, unit):
        assert isinstance(unit, UnitId)
        self.units.add(unit)

    def remove(self, unit):
        assert isinstance(unit, UnitId)
        self.units.remove(unit)

    def __len__(self):
        return len(self.units)

    def __contains__(self, unit):
        assert isinstance(unit, UnitId)
        return (unit in self.units)

    def __iter__(self):
        for unit in sorted(self.units):
            yield unit

