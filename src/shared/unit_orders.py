class UnitOrders(object):
    def __init__(self):
        self.orders = {}

    def giveOrders(self, unit, orders):
        if orders is not None and not isinstance(orders, list):
            orders = list(orders)
        self.orders[unit] = orders

    def getNextOrder(self, unit):
        try:
            orders = self.orders[unit]
            if orders is None:
                return None
            else:
                return orders[0]
        except (KeyError, IndexError):
            return None

    def removeNextOrder(self, unit):
        self.orders[unit] = self.orders[unit][1:]
        if not self.orders[unit]:
            del self.orders[unit]

    def getAllUnitsNextOrders(self):
        return {x: self.getNextOrder(x) for x in self.orders}

