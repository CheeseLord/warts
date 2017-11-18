# from direct.task import Task  # This must be imported first.
#                               # Why must it be imported first?
from direct.showbase.ShowBase import ShowBase

from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage
from src.shared import messages

log = newLogger(__name__)

# TODO[#34]: Read from a config file.
DESIRED_FPS = 60

class WartsApp(ShowBase):
    def __init__(self, graphicsInterface):
        ShowBase.__init__(self)

        self.firstTick = True

        graphicsInterface.graphicsReady(self)

    # For backward compatibility.
    # TODO[#84]: Remove when old graphics goes away; have backend just call
    # tick() directly.
    def interfaceMessage(self, data):
        message = deserializeMessage(data)
        if isinstance(message, messages.Tick):
            self.tick()

        # Ignore everything else.

    def tick(self):
        log.debug("Graphics: tick()")

        # TODO: Call addGround() if this is the first time. We need a reference
        # to the GameState to do that.

        self.firstTick = False

