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
        assert type(orders) == list
        for order in orders:
            assert isinstance(order, Order)
        self.orders[unit] = orders

    def hasNextOrder(self, unit):
        return unit in self.orders and len(self.orders[unit]) > 0

    def getNextOrder(self, unit):
        # FIXME: Just return None or something if not hasNextOrder?
        assert self.hasNextOrder(unit)
        return self.orders[unit][0]

    def removeNextOrder(self, unit):
        self.orders[unit] = self.orders[unit][1:]

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

