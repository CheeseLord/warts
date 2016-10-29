import os
import sys

from direct.task import Task  # This must be imported first.
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from direct.showbase.ShowBase import ShowBase
from panda3d import core
from panda3d.core import Point3, Mat4, Filename, NodePath

from src.shared import config
from src.shared import messages
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    invalidMessage, unhandledMessageCommand, InvalidMessageError

log = newLogger(__name__)


# TODO: Read from a config file.
DESIRED_FPS = 60


class WartsApp(ShowBase):
    """
    The application running all the graphics.
    """

    def __init__(self, backend):
        ShowBase.__init__(self)

        self.backend = backend

        # Our playerId.
        self.myId = -1

        # Set up event handling.
        self.keys = {}
        self.setupEventHandlers()
        self.setupMouseHandler()

        # Mapping from playerIds to obelisk nodes.
        self.obelisks = {}

        # Set up the background.
        self.scene = self.loader.loadModel("environment")
        self.scene.reparentTo(self.render)
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)

        # Set up camera control.
        self.cameraHolder = self.render.attachNewNode('CameraHolder')
        self.cameraHolder.setPos(0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.setCameraCustom()

        self.backend.graphicsReady(self)

    def cleanup(self):
        pass

    def setupMouseHandler(self):
        """
        Handle mouse clicks.
        """

        # Define the ground plane by a normal and a point.
        groundCollisionPlane = core.CollisionPlane(core.LPlanef(
            core.Vec3(0, 0, 1), core.Point3(0, 0, 0)))

        # Create a node path for the ground.
        self.groundPlaneNodePath = self.render.attachNewNode(
            core.CollisionNode("groundCollisionNode"))
        self.groundPlaneNodePath.node().addSolid(groundCollisionPlane)

        # Find the ray defined by the mouse click.
        mouseClickNode = core.CollisionNode("mouseRay")
        self.mouseClickNodePath = self.camera.attachNewNode(mouseClickNode)
        # TODO: Do we need to mouseClickNode.setFromCollideMask() here?
        self.mouseClickRay = core.CollisionRay()
        mouseClickNode.addSolid(self.mouseClickRay)

        # Create objects to traverse the node tree to find collisions.
        self.mouseClickHandler = core.CollisionHandlerQueue()
        self.mouseClickTraverser = core.CollisionTraverser("mouse click")
        self.mouseClickTraverser.addCollider(self.mouseClickNodePath,
                                             self.mouseClickHandler)

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

        # Handle mouse wheel.
        self.accept("wheel_up", self.zoomCamera, [True])
        self.accept("wheel_down", self.zoomCamera, [False])

        # Handle clicking.
        self.accept("mouse1", self.handleMouseClick, [])

        # Handle window close request (clicking the X, Alt-F4, etc.)
        self.win.set_close_request_event("window-close")
        self.accept("window-close", self.handleWindowClose)

    def addObelisk(self, playerId, pos):
        if self.myId < 0:
            raise RuntimeError("Must set ID before adding obelisks.")
        if playerId in self.obelisks:
            raise RuntimeError("Already have obelisk with id {id}."
                               .format(id=playerId))

        nodeName = "obeliskNode-{}".format(playerId)
        x, y = pos

        log.info("Adding obelisk {} at ({}, {})".format(playerId, x, y))

        obeliskNode = self.render.attachNewNode(nodeName)
        obeliskNode.setPos(x, y, 0)

        if playerId == self.myId:
            modelName = "test-model.egg"
        else:
            modelName = "other-obelisk.egg"
        obelisk = self.loader.loadModel(getModelPath(modelName))
        obelisk.reparentTo(obeliskNode)
        obelisk.setPos(0, 0, 2.5)

        self.obelisks[playerId] = obeliskNode

    def removeObelisk(self, playerId):
        log.info("Removing obelisk {}".format(playerId))
        obeliskNode = self.obelisks.pop(playerId)
        obeliskNode.removeNode()

    def moveObelisk(self, playerId, pos):
        if playerId not in self.obelisks:
            raise RuntimeError("There is no obelisk with id {id}."
                               .format(id=playerId))
        x, y = pos
        log.debug("Moving obelisk {} to ({}, {})".format(playerId, x, y))
        myInterval = self.obelisks[playerId].posInterval(config.TICK_LENGTH,
                                                         (x, y, 0))
        myInterval.start()

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
        self.prevCameraPos = self.camera.getPos()
        self.prevCameraHpr = self.camera.getHpr()

        # Use the existing camera location, rather than jumping back to the one
        # from last time the default camera controller was active.
        # Copied from https://www.panda3d.org/manual/index.php/Mouse_Support
        mat = Mat4(camera.getMat())
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

    def updateCameraTask(self, task):
        """
        Move the camera sensibly.
        """

        dt = globalClock.getDt()
        translateSpeed = 30 * dt
        rotateSpeed = 50 * dt

        forward = translateSpeed * (self.keys["arrow_up"] -
                                    self.keys["arrow_down"])
        sideways = translateSpeed * (self.keys["arrow_right"] -
                                     self.keys["arrow_left"])
        # Check if the mouse is over the window.
        if base.mouseWatcherNode.hasMouse():
            # Get the position.
            # Each coordinate is normalized to the interval [-1, 1].
            mousePos = base.mouseWatcherNode.getMouse()
            xPos, yPos = mousePos.getX(), mousePos.getY()
            # Only move if the mouse is close to the edge.
            if abs(xPos) > 0.4:
                sideways += 2 * translateSpeed * xPos
            if abs(yPos) > 0.4:
                forward += 2 * translateSpeed * yPos
        self.cameraHolder.setPos(self.cameraHolder, sideways, forward, 0)

        rotate = rotateSpeed * (self.keys["a"] - self.keys["d"])
        self.cameraHolder.setHpr(self.cameraHolder, rotate, 0, 0)

        return Task.cont

    def zoomCamera(self, inward):
        """
        Zoom in or out.
        """

        dt = globalClock.getDt()
        zoomSpeed = 100 * dt

        zoom = -zoomSpeed if inward else zoomSpeed
        self.cameraHolder.setPos(self.cameraHolder, 0, 0, zoom)

    def handleMouseClick(self):
        # Make sure the mouse is inside the screen
        if self.mouseWatcherNode.hasMouse():
            # Get the screen coordinates of the mouse, normalized to [-1, 1].
            mousePos = self.mouseWatcherNode.getMouse()

            # Make the ray extend from the camera, in the direction of the
            # mouse.
            self.mouseClickRay.setFromLens(self.camNode, mousePos)

            # Check each object in the node tree for collision with the mouse.
            self.mouseClickTraverser.traverse(self.render)
            for entry in self.mouseClickHandler.getEntries():
                if entry.hasInto():
                    # Check if each intersection is with the ground.
                    if entry.getIntoNodePath() == self.groundPlaneNodePath:
                        if self.usingCustomCamera:
                            clickedPoint = entry.getSurfacePoint(self.render)
                            x, y, z = clickedPoint
                            message = messages.Click((x, y))
                            self.backend.graphicsMessage(message.serialize())

    def handleWindowClose(self):
        log.info("Window close requested -- shutting down client.")
        message = messages.RequestQuit()
        self.backend.graphicsMessage(message.serialize())

    def backendMessage(self, data):
        try:
            message = deserializeMessage(data)
            if isinstance(message, messages.YourIdIs):
                if self.myId >= 0:
                    raise RuntimeError("ID already set; can't change it now.")
                self.myId = message.playerId
                log.info("Your id is {id}.".format(id=self.myId))
            elif isinstance(message, messages.NewObelisk):
                self.addObelisk(message.playerId, message.pos)
            elif isinstance(message, messages.DeleteObelisk):
                self.removeObelisk(message.playerId)
            elif isinstance(message, messages.SetPos):
                self.moveObelisk(message.playerId, message.pos)
            else:
                unhandledMessageCommand(message, log, sender="server")
        except InvalidMessageError as error:
            invalidMessage(error, log, sender="server")


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
