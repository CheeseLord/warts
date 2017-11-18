# from direct.task import Task  # This must be imported first.
#                               # Why must it be imported first?
from direct.showbase.ShowBase import ShowBase

from src.shared.logconfig import newLogger

log = newLogger(__name__)

# TODO[#34]: Read from a config file.
DESIRED_FPS = 60

class WartsApp(ShowBase):
    def __init__(self, graphicsInterface):
        ShowBase.__init__(self)
        graphicsInterface.graphicsReady(self)

    # For backward compatibility.
    # TODO[#84]: Remove when old graphics goes away.
    def interfaceMessage(self, data):
        pass

