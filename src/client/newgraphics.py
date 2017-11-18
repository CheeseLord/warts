import os
import sys

from direct.task import Task  # This must be imported first.
                              # Why must it be imported first?
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Mat4, Filename, ClockObject

from src.shared.geometry import Coord, Distance
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage
from src.shared import messages
from src.shared.utils import minmax
from src.client.backend import worldToGraphicsPos
from src.client import messages as cmessages

log = newLogger(__name__)

# TODO[#34]: Read from a config file.
DESIRED_FPS = 60

# Fraction of the window (on each axis) taken up by the "edge scrolling"
# region. Note that half of the region is on each side.
EDGE_SCROLL_WIDTH = 0.2


class WartsApp(ShowBase):
    def __init__(self, graphicsInterface, gameState):
        ShowBase.__init__(self)

        self.graphicsInterface = graphicsInterface
        self.gameState = gameState

        self.groundNodes = None
        self.firstTick = True


        # This is available as a global, but pylint gives an undefined-variable
        # warning if we use it that way. Looking at
        #     https://www.panda3d.org/manual/index.php/ShowBase
        # I would have thought we could reference it as either
        # self.globalClock, direct.showbase.ShowBase.globalClock, or possibly
        # direct.showbase.globalClock, but none of those seems to work. To
        # avoid the pylint warnings, create self.globalClock manually.
        self.globalClock = ClockObject.getGlobalClock()

        # Set up event handling.
        self.mouseState = {}
        self.keys = {}
        self.setupEventHandlers()

        # Set up camera control.
        self.cameraHolder = self.render.attachNewNode('CameraHolder')
        self.cameraHolder.setPos(0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.usingCustomCamera = True
        self.setCameraCustom()


        graphicsInterface.graphicsReady(self)

    def cleanup(self):
        pass

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

    def setCameraCustom(self):
        """
        Change to using our custom task to control the camera.
        """

        # Disable the default mouse-based camera control task, so we don't have
        # to fight with it for control of the camera.
        self.disableMouse()

        # Face the camera in the appropriate angle.
        self.camera.setHpr(self.prevCameraHpr)

        # Put it in the same location as the cameraHolder, and make it stay
        # put relative to the cameraHolder (so we can move the camera around by
        # changing the cameraHolder's position).
        self.camera.reparentTo(self.cameraHolder)
        self.camera.setPos(0, 0, 0)

        # Substitute our own camera control task.
        self.taskMgr.add(self.updateCameraTask, "UpdateCameraTask")

        self.usingCustomCamera = True

    def setCameraDefault(self):
        """
        Change to using the default mouse-based camera controls.
        """

        self.taskMgr.remove("UpdateCameraTask")

        # Save current location for when this control style is restored.
        self.prevCameraHpr = self.camera.getHpr()

        # Use the existing camera location, rather than jumping back to the one
        # from last time the default camera controller was active.
        # Copied from https://www.panda3d.org/manual/index.php/Mouse_Support
        mat = Mat4(self.camera.getMat())
        mat.invertInPlace()
        self.mouseInterfaceNode.setMat(mat)
        self.enableMouse()

        self.usingCustomCamera = False

    def toggleCameraStyle(self):
        """
        Switch to whichever style of camera control isn't currently active.
        """

        if self.usingCustomCamera:
            self.setCameraDefault()
        else:
            self.setCameraCustom()

    # We don't use task, but we can't remove it because the function signature
    # is from Panda3D.
    def updateCameraTask(self, task):  # pylint: disable=unused-argument
        """
        Move the camera sensibly.
        """

        dt = self.globalClock.getDt()
        translateSpeed = 30 * dt
        rotateSpeed    = 50 * dt

        # Separately track whether the camera should translate in each of the 4
        # directions. These 4 are initialized based on the various inputs that
        # might tell us to scroll, and different inputs saying the same thing
        # don't stack. That way if we get inputs saying both "left" and
        # "right", they can cancel and the camera just won't move along that
        # axis -- even if, say, there are two inputs saying "left" and only one
        # saying "right'.
        moveLeft  = self.keys["arrow_left"]
        moveRight = self.keys["arrow_right"]
        moveUp    = self.keys["arrow_up"]
        moveDown  = self.keys["arrow_down"]

        # Check if the mouse is over the window.
        if self.mouseWatcherNode.hasMouse():
            # Get the position.
            # Each coordinate is normalized to the interval [-1, 1].
            mousePos = self.mouseWatcherNode.getMouse()
            xPos, yPos = mousePos.getX(), mousePos.getY()
            # Only move if the mouse is close to the edge, and actually within
            # the window.
            if  (1.0 - EDGE_SCROLL_WIDTH) < xPos <=  1.0:
                moveRight = 1
            if -(1.0 - EDGE_SCROLL_WIDTH) > xPos >= -1.0:
                moveLeft  = 1
            if  (1.0 - EDGE_SCROLL_WIDTH) < yPos <=  1.0:
                moveUp    = 1
            if -(1.0 - EDGE_SCROLL_WIDTH) > yPos >= -1.0:
                moveDown  = 1

        forward  = translateSpeed * (moveUp    - moveDown)
        sideways = translateSpeed * (moveRight - moveLeft)
        self.cameraHolder.setPos(self.cameraHolder, sideways, forward, 0)

        # Selection box logic -- TODO
        # if sideways != 0 or forward != 0:
        #     self.updateSelectionBox()

        rotate = rotateSpeed * (self.keys["a"] - self.keys["d"])
        self.cameraHolder.setHpr(self.cameraHolder, rotate, 0, 0)

        return Task.cont

    def zoomCamera(self, inward):
        """
        Zoom in or out.
        """

        dt = self.globalClock.getDt()
        zoomSpeed = 100 * dt

        zoom = -zoomSpeed if inward else zoomSpeed
        self.cameraHolder.setPos(self.cameraHolder, 0, 0, zoom)

    def getMousePos(self):
        # Check if the mouse is over the window.
        if self.mouseWatcherNode.hasMouse():
            # Get the position.
            # Each coordinate is normalized to the interval [-1, 1].
            mousePoint = self.mouseWatcherNode.getMouse()
            # Create a copy of mousePoint rather than returning a reference to
            # it, because mousePoint will be modified in place by Panda.
            return (mousePoint.getX(), mousePoint.getY())
        else:
            return None

    def handleWindowClose(self):
        log.info("Window close requested -- shutting down client.")
        # When in Rome, send messages like the Romans do, I guess.
        # TODO: Get rid of messages, I think.
        message = cmessages.RequestQuit()
        self.graphicsInterface.graphicsMessage(message.serialize())

    def setupEventHandlers(self):
        def pushKey(key, value):
            self.keys[key] = value

        for key in ["arrow_up", "arrow_left", "arrow_right", "arrow_down",
                    "w", "a", "d", "s"]:
            self.keys[key] = False
            self.accept(key, pushKey, [key, True])
            self.accept("shift-%s" % key, pushKey, [key, True])
            self.accept("%s-up" % key, pushKey, [key, False])

        # Camera toggle.
        self.accept("f3",       self.toggleCameraStyle, [])
        self.accept("shift-f3", self.toggleCameraStyle, [])

        # Center view.
        # self.accept("space", self.centerView, []) -- TODO

        # Handle mouse wheel.
        self.accept("wheel_up", self.zoomCamera, [True])
        self.accept("wheel_down", self.zoomCamera, [False])

        # # Handle clicking. -- TODO
        # self.accept("mouse1",    self.pandaEventMouseDown, [1, []])
        # self.accept("mouse1-up", self.pandaEventMouseUp,   [1])
        # # TODO: Make sure this is always the right mouse button.
        # self.accept("mouse3",    self.pandaEventMouseDown, [3, []])
        # self.accept("mouse3-up", self.pandaEventMouseUp,   [3])
        #
        # # Handle clicking with modifier keys.
        # self.accept("shift-mouse1",   self.pandaEventMouseDown,
        #             [1, ["shift"]])
        # self.accept("control-mouse1", self.pandaEventMouseDown,
        #             [1, ["control"]])
        # self.accept("shift-mouse3",   self.pandaEventMouseDown,
        #             [3, ["shift"]])
        # self.accept("control-mouse3", self.pandaEventMouseDown,
        #             [3, ["control"]])

        # Handle window close request (clicking the X, Alt-F4, etc.)
        self.win.set_close_request_event("window-close")
        self.accept("window-close", self.handleWindowClose)



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

