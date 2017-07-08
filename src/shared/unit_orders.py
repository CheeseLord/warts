class UnitOrders(object):
    def __init__(self):
        self.orders = {}
        # List of units to create at next tick.
        self.pendingNewUnits = []

    def createNewUnit(self, playerId, pos):
        self.pendingNewUnits.append((playerId, pos))

    def getPendingNewUnits(self):
        for x in self.pendingNewUnits:
            yield x

    def clearPendingNewUnits(self):
        self.pendingNewUnits = []

    def giveOrders(self, unit, orders):
        assert isinstance(orders, list)
        for order in orders:
            assert isinstance(order, Order)
        self.orders[unit] = orders

    def clearOrders(self, unit):
        del self.orders[unit]

    def hasNextOrder(self, unit):
        return unit in self.orders and len(self.orders[unit]) > 0

    def getNextOrder(self, unit):
        # FIXME: Just return None or something if not hasNextOrder?
        assert self.hasNextOrder(unit)
        return self.orders[unit][0]

    def removeNextOrder(self, unit):
        self.orders[unit] = self.orders[unit][1:]

    def getAllUnitsWithOrders(self):
        """
        Generate the ids of all units that have a nonempty list of orders.
        """

        # While we're at it, lazily remove any units from the mapping if they
        # don't actually have orders.
        unitsWithNoOrders = []

        # Note! Don't change this to use iteritems(). We need to make sure that
        # the caller can modify the unit orders while they are iterating over
        # this list, without messing up the iteration. Currently this is
        # accomplished by just getting the whole list of unit IDs up front
        # (self.orders.keys()) and then iterating over that list.
        for unitId in self.orders.keys():
            if self.orders[unitId]:
                yield unitId
            else:
                # Don't actually remove the unit yet, because modifying a
                # container while iterating over it tends to cause problems.
                # Instead, store it in a list to remove later.
                unitsWithNoOrders.append(unitId)

        for unitId in unitsWithNoOrders:
            del self.orders[unitId]

    ### Probably not needed anymore.
    # def getAllUnitsNextOrders(self):
    #     return {x: self.getNextOrder(x) for x in self.orders
    #                                     if self.hasNextOrder(x)}


class Order(object):
    pass

class DelUnitOrder(Order):
    pass

class MoveUnitOrder(Order):
    def __init__(self, dest):
        super(MoveUnitOrder, self).__init__()
        self.dest   = dest

