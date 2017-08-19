from abc import ABCMeta, abstractmethod

from src.shared.logconfig import newLogger
from src.shared.utils import thisShouldNeverHappen

log = newLogger(__name__)

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
        gameState.resources[self.playerId] += self.delta
        if gameState.resources[self.playerId] < 0:
            log.error("Player %d has %r resources.",
                      self.playerId, gameState.resources[self.playerId])
            thisShouldNeverHappen()

