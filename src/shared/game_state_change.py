from abc import ABCMeta, abstractmethod

class GameStateChange(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def apply(self, gameState):
        pass


class ResourceChange(GameStateChange):
    def __init__(self, playerId, delta):
        super(ResourceChange, self).__init__()
        self.playerId = playerId
        self.delta    = delta

    def apply(self, gameState):
        gameState.resources[self.playerId] -= self.delta
        assert gameState.resources[self.playerId] >= 0

