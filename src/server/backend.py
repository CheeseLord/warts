from src.shared.ident import unitToPlayer, getUnitSubId
from src.shared.logconfig import newLogger

log = newLogger(__name__)

class Backend(object):
    def __init__(self):
        super(Backend, self).__init__()

        self.gameStateManager = None
        self.clientInterfacer = None

        self.stdio = None

    # These next two methods must be called immediately after __init__, before
    # any other methods.
    def setGameStateManager(self, gameStateManager):
        self.gameStateManager = gameStateManager

    def setClientInterfacer(self, clientInterfacer):
        self.clientInterfacer = clientInterfacer

    def tick(self):
        self.gameStateManager.tick()
        self.clientInterfacer.tick()

    def stdioReady(self, stdioComponent):
        assert self.stdio is None
        self.stdio = stdioComponent
        assert self.stdio is not None

    def stdioMessage(self, message):
        # TODO[#48]: Use a real message here.
        if message == "dump":
            log.info("Dumping all unit info...")
            gameState = self.gameStateManager.gameState
            for uid in sorted(gameState.positions.keys()):
                pos = gameState.positions[uid]
                ux, uy = pos.unit
                # TODO: Factor this out (maybe into gamestate?)
                # "    {player:>2}: {subId:>3} @ {x:>4}, {y:>4}"
                log.info("    %2s: %3s @ %4s, %4s",
                         unitToPlayer(uid), getUnitSubId(uid), ux, uy)
            log.info("End unit dump.")
        else:
            # TODO: Do something sensible.
            log.info("Don't know how to handle %r.", message)
