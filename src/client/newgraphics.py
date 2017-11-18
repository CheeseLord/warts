import os
import sys

# from direct.task import Task  # This must be imported first.
#                               # Why must it be imported first?
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename

from src.shared.geometry import Coord, Distance
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage
from src.shared import messages
from src.shared.utils import minmax
from src.client.backend import worldToGraphicsPos

log = newLogger(__name__)

# TODO[#34]: Read from a config file.
DESIRED_FPS = 60

class WartsApp(ShowBase):
    def __init__(self, graphicsInterface, gameState):
        ShowBase.__init__(self)

        self.gameState = gameState

        self.groundNodes = None
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

        if self.firstTick:
            if not self.gameState.hasSize:
                log.error("GameState must be assigned a size before first "
                          "tick().")
                return
            width, height = self.gameState.sizeInChunks
            self.groundNodes = [[None for _x in range(height)]
                                for _y in range(width)]
            for cx in range(width):
                for cy in range(height):
                    self.addGround((cx, cy),
                                   self.gameState.groundTypes[cx][cy])

            self.firstTick = False

    def addGround(self, chunkIndex, terrainType):
        cx, cy = chunkIndex
        wPos = Coord.fromCBU(chunk=(chunkIndex))

        if terrainType == 0:
            modelName = "green-ground.egg"
        else:
            modelName = "red-ground.egg"
            if terrainType != 1:
                log.warn("Unrecognized terrain type %d", terrainType)

        gPos1 = worldToGraphicsPos(wPos)
        gPos2 = worldToGraphicsPos(wPos +
                                   Distance.fromCBU(chunk=(1,1)))

        # Figure out where we want the tile.
        goalCenterX = 0.5 * (gPos2[0] + gPos1[0])
        goalCenterY = 0.5 * (gPos2[1] + gPos1[1])
        goalWidthX  =    abs(gPos2[0] - gPos1[0])
        goalWidthY  =    abs(gPos2[1] - gPos1[1])

        model = self.loader.loadModel(getModelPath(modelName))

        # Put the model in the scene, but don't position it yet.
        rootNode = self.render.attachNewNode("")
        model.reparentTo(rootNode)

        # Rescale the model about its origin. The x and y coordinates of the
        # model's origin should be chosen as wherever it looks like the model's
        # center of mass is, so that rotation about the origin (in the xy
        # plane) feels natural.
        # TODO[#9]: Set a convention for model bounds so we don't have to do a
        # getTightBounds every time. This is dumb.
        # TODO[#3]: Or, as an alternative shorter-term solution, just define a
        # scale in the config files for the few models that aren't ours.
        bound1, bound2 = model.getTightBounds()
        modelWidthX = abs(bound2[0] - bound1[0])
        modelWidthY = abs(bound2[1] - bound1[1])

        # Scale it to the largest it can be while still fitting within the goal
        # rect. If the aspect ratio of the goal rect is different from that of
        # the model, then it'll only fill that rect in one dimension.
        # altScaleFactor is used for sanity checks below.
        scaleFactor, altScaleFactor = minmax(goalWidthX / modelWidthX,
                                             goalWidthY / modelWidthY)

        # Sanity check the scale factor.
        if scaleFactor <= 0.0:
            if scaleFactor == 0.0:
                log.warn("Ground %s will be scaled negatively!", chunkIndex)
            else:
                log.warn("Ground %s will be scaled to zero size.", chunkIndex)
        else:
            # TODO[#9]: Currently the example panda triggers this warning.
            # TODO[#3]: Magic numbers bad.
            if altScaleFactor / scaleFactor > 1.001:
                log.warn("Ground %s has different aspect ratio than "
                         "its model: model of size %.3g x %.3g being scaled "
                         "into %.3g x %.3g.",
                         chunkIndex, modelWidthX, modelWidthY,
                         goalWidthX, goalWidthY)

        model.setScale(scaleFactor)

        # Place the model at z=0. The model's origin should be placed so that
        # this looks natural -- for most units this means it should be right at
        # the bottom of the model, but if we add any units that are intended to
        # float above the ground, then this can be accomplished by just
        # positioning the model above its origin.
        rootNode.setPos(goalCenterX, goalCenterY, 0.0)

        self.groundNodes[cx][cy] = rootNode


def getModelPath(modelName):
    """
    Return the Panda3D path for a model.
    """

    # Instructions for loading models at:
    #    https://www.panda3d.org/manual/index.php/Loading_Models

    repository = os.path.abspath(sys.path[0])
    repository = Filename.fromOsSpecific(repository).getFullpath()
    if not repository.endswith('/'):
        repository += '/'
    modelsDir = repository + 'assets/models/'

    return modelsDir + modelName

