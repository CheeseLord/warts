import math
import os
import sys

from direct.task import Task  # This must be imported first.
from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from panda3d import core
from panda3d.core import Point3, Mat4, Filename, NodePath

from src.shared import config
from src.shared import messages
from src.shared.geometry import chunkToUnit
from src.shared.ident import unitToPlayer
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, invalidMessageArgument, \
    InvalidMessageError
from src.shared.unit_set import UnitSet
from src.client.backend import unitToGraphics, GRAPHICS_SCALE

log = newLogger(__name__)


# TODO[#34]: Read from a config file.
DESIRED_FPS = 60


class WartsApp(ShowBase):
    """
    The application running all the graphics.
    """

    def __init__(self, graphicsInterface):
        ShowBase.__init__(self)

        self.graphicsInterface = graphicsInterface

        # Our playerId.
        # TODO[#34]: Graphics shouldn't even know this.
        self.myId = -1

        # Set up event handling.
        self.keys = {}
        self.setupEventHandlers()
        self.setupMouseHandler()

        # Mapping from unitIds to obelisk actors.
        # TODO[#34]: Shouldn't use UnitIds.
        self.obelisks = {}

        # Set up camera control.
        self.cameraHolder = self.render.attachNewNode('CameraHolder')
        self.cameraHolder.setPos(0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.setCameraCustom()

        self.graphicsInterface.graphicsReady(self)

    def cleanup(self):
        pass

    # TODO[#34]: Just have a generic addModel method. Don't do all this id
    # checking.
    def addObelisk(self, unitId, pos):
        if self.myId < 0:
            raise RuntimeError("Must set ID before adding obelisks.")
        if unitId in self.obelisks:
            raise RuntimeError("Already have obelisk with id {id}."
                               .format(id=unitId))

        log.info("Adding obelisk {} at {}".format(unitId, pos))
        x, y = unitToGraphics(pos)

        if unitToPlayer(unitId) == self.myId:
            # The example panda from the Panda3D "Hello world" tutorial.
            obelisk = Actor("models/panda-model",
                            {"walk": "models/panda-walk4"})
            obelisk.setScale(0.004, 0.004, 0.004)
        else:
            obelisk = self.loader.loadModel(getModelPath("other-obelisk.egg"))
        obelisk.reparentTo(self.render)
        obelisk.setPos(x, y, 2.5)

        self.obelisks[unitId] = obelisk

    # TODO[#34]: Replace with removeModel.
    def removeObelisk(self, unitId):
        log.info("Removing obelisk {}".format(unitId))
        obeliskActor = self.obelisks.pop(unitId)
        # TODO [#30]: The obelisk isn't actually an actor, so it doesn't
        # have a cleanup() method.
        try:
            obeliskActor.cleanup()
        except AttributeError:
            pass
        obeliskActor.removeNode()

    # TODO[#34]: Replace with moveModel. And figure out how animation factors
    # into that?
    def moveObelisk(self, unitId, pos):
        if unitId not in self.obelisks:
            raise RuntimeError("There is no obelisk with id {id}."
                               .format(id=unitId))
        log.debug("Moving obelisk {} to {}".format(unitId, pos))
        x,y = unitToGraphics(pos)
        obeliskActor = self.obelisks[unitId]
        oldX, oldY, oldZ = obeliskActor.getPos()
        z = oldZ
        moveInterval = obeliskActor.posInterval(config.TICK_LENGTH, (x, y, z))
        moveInterval.start()

        if unitToPlayer(unitId) == self.myId:
            # Ensure the panda is facing the right direction.
            heading = math.atan2(y - oldY, x - oldX)
            heading *= 180.0 / math.pi
            # Magic angle adjustment needed to stop the panda always facing
            # sideways.
            heading += 90.0
            obeliskActor.setHpr(heading, 0, 0)

            currFrame = obeliskActor.getCurrentFrame("walk")
            if currFrame is None:
                currFrame = 0
            # Supposedly, it's possible to pass a startFrame and a duration to
            # actorInterval, instead of calculating the endFrame ourself. But
            # for some reason, that doesn't seem to work; if I do that, then
            # the animation just keeps jumping around the early frames and
            # never gets past frame 5 or so. I'm not sure why. For now at
            # least, just calculate the endFrame ourselves to work around this.
            log.debug("Animating panda from frame {}/{}"
                      .format(currFrame, obeliskActor.getNumFrames("walk")))
            frameRate = obeliskActor.getAnimControl("walk").getFrameRate()
            endFrame = currFrame + int(math.ceil(frameRate *
                                                 config.TICK_LENGTH))
            animInterval = obeliskActor.actorInterval("walk", loop=1,
                startFrame=currFrame, endFrame=endFrame)
            animInterval.start()

    # TODO[#34]: Graphics probably shouldn't know about ground versus units.
    # Though it may be useful to distinguish fixtures (ground, trees) from
    # non-fixtures (units, structures). For now, let's just store a metadata
    # field with each model to prove we can. In short: this method should be
    # merged into addModel.
    def addGround(self, cPos, terrainType):
        modelName = None
        if terrainType == 0:
            modelName = "green-ground.egg"
        elif terrainType == 1:
            modelName = "red-ground.egg"
        else:
            # TODO: We're building a new message rather than using the old one
            # to avoid passing the message to this function. This is ugly, but
            # I think it's still slightly less bad than the other solution.
            invalidMessageArgument(messages.GroundInfo(cPos, terrainType), log,
                                   reason="Invalid terrain type")
            # Drop the message.
            return

        # Calculate opposite corners of the ground tile.
        gPos1 = unitToGraphics(chunkToUnit(cPos))
        gPos2 = unitToGraphics(chunkToUnit((coord + 1 for coord in cPos)))

        # TODO: Put most of the below in a common function, because it'll be
        # used for adding most models to the world.

        # Figure out where we want the tile.
        goalCenterX = 0.5 *    (gPos2[0] + gPos1[0])
        goalCenterY = 0.5 *    (gPos2[1] + gPos1[1])
        goalWidthX  = 0.5 * abs(gPos2[0] - gPos1[0])
        goalWidthY  = 0.5 * abs(gPos2[1] - gPos1[1])
        # For now, all models sit flush against the ground.
        goalBottomZ = 0.0

        # Put the model in the scene, but don't position it yet.
        groundTile = self.loader.loadModel(getModelPath(modelName))
        groundTile.reparentTo(self.render)

        # Calculate the footprint of the tile in its default position/scale.
        bound1, bound2 = groundTile.getTightBounds()
        modelCenterX = 0.5 *    (bound2[0] + bound1[0])
        modelCenterY = 0.5 *    (bound2[1] + bound1[1])
        modelWidthX  = 0.5 * abs(bound2[0] - bound1[0])
        modelWidthY  = 0.5 * abs(bound2[1] - bound1[1])
        modelBottomZ = min(bound2[2], bound1[2])

        # TODO: Give a graceful error if the tight bounds are zero on either
        # axis.

        # Scale it to the largest it can be while still fitting within the goal
        # rect. If the aspect ratio of the goal rect is different from that of
        # the model, then it'll only fill that rect in one dimension.
        scaleFactor = min(goalWidthX / modelWidthX, goalWidthY / modelWidthY)
        groundTile.setScale(scaleFactor)

        groundTile.setPos(goalCenterX - modelCenterX,
                          goalCenterY - modelCenterY,
                          goalBottomZ - modelBottomZ)

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

    # TODO[#34]: The core logic here belongs in graphicsInterface if anywhere.
    # The graphics shouldn't have any idea where it makes sense to center the
    # view on. It may make sense to have a message that means "move view to <x>
    # <y> coordinates", but figuring out <x> and <y> is up to the
    # graphicsInterface.
    def centerViewOnSelf(self):
        if self.myId not in self.obelisks:
            return

        # This code is commented out as we need to have a selection algorithm
        # of identifying the unit to focus the camera on
        pass

        ##_, _, z = self.cameraHolder.getPos()
        ##x, y, _ = self.obelisks[playerToUnit(self.myId)].getPos()

        # This is a hack.
        # The camera isn't aimed straight down; it's aimed at a slight angle
        # (to give some perspective to the scene). Therefore, we don't want to
        # put the camera directly above the obelisk; we want to put it up and
        # at an angle. We could (and eventually should) do some geometry on the
        # camera's HPR to correctly compute that position, but for now I'm just
        # hardcoding a roughly-correct offset, because it's easier.
        ##y -= 16

        ##self.cameraHolder.setPos(x, y, z)

    def handleMouseClick(self, button):
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
                            # TODO: This component should take care of decoding
                            # the click as far as "left" or "right"; we
                            # shouldn't send a numerical button id to the
                            # graphicsInterface.
                            message = messages.Click(button, (x, y))
                            self.graphicsInterface.graphicsMessage(
                                message.serialize())

    def handleWindowClose(self):
        log.info("Window close requested -- shutting down client.")
        message = messages.RequestQuit()
        self.graphicsInterface.graphicsMessage(message.serialize())

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

        # Center view.
        self.accept("space", self.centerViewOnSelf, [])

        # Handle mouse wheel.
        self.accept("wheel_up", self.zoomCamera, [True])
        self.accept("wheel_down", self.zoomCamera, [False])

        # Handle clicking.
        self.accept("mouse1", self.handleMouseClick, [1])
        # TODO: Make sure this is always the right mouse button.
        self.accept("mouse3", self.handleMouseClick, [3])

        # Handle window close request (clicking the X, Alt-F4, etc.)
        self.win.set_close_request_event("window-close")
        self.accept("window-close", self.handleWindowClose)

    # TODO [#34]: This really shouldn't happen here.
    def unitAt(self, pos):
        x, y = pos

        nearest = UnitSet()
        nearestDistance = float('inf')
        for unitId in self.obelisks:
            if unitToPlayer(unitId) != self.myId:
                continue

            unitX, unitY, unitZ = self.obelisks[unitId].getPos()
            distance = (unitX - x) ** 2 + (unitY - y) ** 2
            if distance < nearestDistance:
                nearest = UnitSet([unitId])
                nearestDistance = distance
        return nearest


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

