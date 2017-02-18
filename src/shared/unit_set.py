from src.shared.config import MAX_PLAYER_UNITS
from src.shared.ident import UnitId

# TODO: Enforce MAX_PLAYER_UNITS cap.

class UnitSet(object):
    def __init__(self, units=[]):
        super(UnitSet, self).__init__()
        self.units = set(units)

    def encode(self):
        # TODO
        NotImplemented

    def decode(self):
        # TODO
        NotImplemented

    def add(self, unit):
        assert isinstance(unit, UnitId)
        self.units.add(unit)

    def remove(self, unit):
        assert isinstance(unit, UnitId)
        self.units.remove(unit)

    def __contains__(self, unit):
        assert isinstance(unit, UnitId)
        return (unit in self.units)

    def __iter__(self):
        for unit in sorted(self.units):
            yield unit
