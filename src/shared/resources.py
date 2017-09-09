# TODO: Actually use this class.

# Unreachable. You don't say.
# pylint: disable=unreachable
raise NotImplementedError, "This class doesn't work yet."

# Size of every resource pool in build coordinates.
RESOURCE_WIDTH  = 2
RESOURCE_HEIGHT = 1

class ResourcePool(object):
    def __init__(self, pos):
        super(ResourcePool, self).__init__()
        self.pos = pos

    # Note: these next 8 will probably go in a general 'Structure' class.

    @property
    def west(self):
        return self.pos[0]
    @property
    def south(self):
        return self.pos[1]
    @property
    def east(self):
        return self.pos[0] + RESOURCE_WIDTH
    @property
    def north(self):
        return self.pos[1] + RESOURCE_HEIGHT

    @property
    def sw(self):
        return (self.west, self.south)
    @property
    def nw(self):
        return (self.west, self.north)
    @property
    def se(self):
        return (self.east, self.south)
    @property
    def ne(self):
        return (self.east, self.north)

