class UnitOrders(object):
    def __init__(self):
        self.orders = {}

    def giveOrder(self, unit, position):
        self.orders[unit] = position

    def getOrders(self):
        orders = self.orders
        self.orders = {}
        return orders
