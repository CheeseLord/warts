import math
import os
import sys

from direct.task import Task  # This must be imported first.
from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from panda3d import core
from panda3d.core import Point3, Mat4, Filename, NodePath, LineSegs

from src.shared import config
from src.shared import messages
from src.shared.geometry import chunkToUnit
from src.shared.ident import unitToPlayer
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, invalidMessageArgument, \
    InvalidMessageError
from src.shared.unit_set import UnitSet
from src.shared.utils import minmax, thisShouldNeverHappen
from src.client.backend import unitToGraphics, GRAPHICS_SCALE
from src.client import messages as cmessages

log = newLogger(__name__)


# TODO[#34]: Read from a config file.
DESIRED_FPS = 60


class Entity(object):
    """
    Class to represent any sort of thing with a graphical presence in the
    world: ground, trees, units, structures.
    """

    def __init__(self, graphicId, model, rootNode, isActor):
        self.gid      = graphicId
        self.model    = model
        self.rootNode = rootNode
        self.isActor  = isActor

    def cleanup(self):
        if self.isActor:
            self.model.cleanup()
        self.model.removeNode()
        self.rootNode.removeNode()


class WartsApp(ShowBase):
    """
    The application running all the graphics.
    """

    def __init__(self, graphicsInterface):
        ShowBase.__init__(self)

        self.graphicsInterface = graphicsInterface

        # Mapping from gids to entities.
        self.entities = {}

        # Set up event handling.
        self.keys = {}
        self.setupEventHandlers()
        self.setupMouseHandler()

        # Set up camera control.
        self.cameraHolder = self.render.attachNewNode('CameraHolder')
        self.cameraHolder.setPos(0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.setCameraCustom()

        test = LineSegs("Steve")
        test.setThickness(3.0)
        test.setColor(0.0, 1.0, 0.25, 1.0)
        test.move_to(-0.20, 0,  0.20)
        test.draw_to( 0.20, 0,  0.20)
        test.draw_to( 0.20, 0, -0.20)
        test.draw_to(-0.20, 0, -0.20)
        test.draw_to(-0.20, 0,  0.20)
        testNode = test.create()
        render2d.attachNewNode(testNode)

        self.rectStartPos = None
        self.prevMousePos = None
        self.graphicsInterface.graphicsReady(self)

    def cleanup(self):
        pass

    def interfaceMessage(self, data):
        # Messages from GraphicsInterface to Graphics are always internal
        # client messages, so no need to catch InvalidMessageError.
        message = deserializeMessage(data)
        if isinstance(message, cmessages.AddEntity):
            self.addEntity(message.gid, message.pos, message.modelPath,
                           message.isExample, message.goalSize)
        elif isinstance(message, cmessages.RemoveEntity):
            self.removeEntity(message.gid)
        elif isinstance(message, cmessages.MoveEntity):
            self.moveEntity(message.gid, message.pos)
        elif isinstance(message, cmessages.MarkEntitySelected):
            self.markSelected(message.gid, message.isSelected)
        else:
            unhandledInternalMessage(message, log)

    def addEntity(self, gid, pos, modelPath, isExample, goalSize):
        """
        pos is given in graphics coordinates.

        goalSize, if specified, is a pair (width, height) -- the model will be
        scaled in the xy plane so that it's as large as possible while still
        fitting within that width and height. Don't pass 0 as the width or the
        height, because that's just not nice.
        """

        if gid in self.entities:
            raise RuntimeError("Already have entity with gid {gid}."
                               .format(gid=gid))

        log.debug("Adding graphical entity {} at {}".format(gid, pos))
        x, y = pos

        if isExample:
            # The example panda from the Panda3D "Hello world" tutorial.
            # TODO[#9]: Figure out a more general way of specifying animations.
            model = Actor(modelPath,
                          {"walk": "models/panda-walk4"})
        else:
            model = self.loader.loadModel(getModelPath(modelPath))

        # Put the model in the scene, but don't position it yet.
        rootNode = render.attachNewNode("")
        model.reparentTo(rootNode)

        # Rescale the model about its origin. The x and y coordinates of the
        # model's origin should be chosen as wherever it looks like the model's
        # center of mass is, so that rotation about the origin (in the xy
        # plane) feels natural.

        goalWidthX, goalWidthY = goalSize

        bound1, bound2 = model.getTightBounds()
        modelWidthX = abs(bound2[0] - bound1[0])
        modelWidthY = abs(bound2[1] - bound1[1])

        xScale = goalWidthX / modelWidthX
        yScale = goalWidthY / modelWidthY

        # Scale it to the largest it can be while still fitting within the goal
        # rect. If the aspect ratio of the goal rect is different from that of
        # the model, then it'll only fill that rect in one dimension.
        # altScaleFactor is used for sanity checks below.
        scaleFactor, altScaleFactor = minmax(goalWidthX / modelWidthX,
                                             goalWidthY / modelWidthY)

        # Sanity check the scale factor.
        if scaleFactor <= 0.0:
            if scaleFactor == 0.0:
                log.warn("Graphical entity {} will be scaled negatively!"
                         .format(gid))
            else:
                log.warn("Graphical entity {} will be scaled to zero size."
                         .format(gid))
        else:
            # TODO[#9]: Currently the example panda triggers this warning.
            # TODO[#3]: Magic numbers bad.
            if altScaleFactor / scaleFactor > 1.001:
                log.warn("Graphical entity {} has different aspect ratio "
                         "than its model: model of size {:.3g} x {:.3g} "
                         "being scaled into {:.3g} x {:.3g}."
                         .format(gid, modelWidthX, modelWidthY,
                                 goalWidthX, goalWidthY))

        model.setScale(scaleFactor)

        # Place the model at z=0. The model's origin should be placed so that
        # this looks natural -- for most units this means it should be right at
        # the bottom of the model, but if we add any units that are intended to
        # float above the ground, then this can be accomplished by just
        # positioning the model above its origin.
        rootNode.setPos(x, y, 0.0)

        entity = Entity(gid, model, rootNode, isExample)
        self.entities[gid] = entity

    def removeEntity(self, gid):
        log.debug("Removing graphical entity {}".format(gid))
        entity = self.entities.pop(gid)
        entity.cleanup()

    def moveEntity(self, gid, newPos):
        log.debug("Moving graphical entity {} to {}".format(gid, newPos))
        entity = self.entities[gid]

        x, y = newPos
        oldX, oldY, oldZ = entity.rootNode.getPos()
        z = oldZ

        # Ensure the entity is facing the right direction.
        heading = math.atan2(y - oldY, x - oldX)
        heading *= 180.0 / math.pi
        # Magic angle adjustment needed to stop the panda always facing
        # sideways.
        # TODO[#9]: Establish a convention about which way _our_ models face;
        # figure out whether we need something like this. (Hopefully not?)
        heading += 90.0
        entity.rootNode.setHpr(heading, 0, 0)

        moveInterval = entity.rootNode.posInterval(config.TICK_LENGTH,
                                                   (x, y, z))
        moveInterval.start()

        if entity.isActor and "walk" in entity.model.getAnimNames():
            currFrame = entity.model.getCurrentFrame("walk")
            if currFrame is None:
                currFrame = 0
            # Supposedly, it's possible to pass a startFrame and a duration to
            # actorInterval, instead of calculating the endFrame ourself. But
            # for some reason, that doesn't seem to work; if I do that, then
            # the animation just keeps jumping around the early frames and
            # never gets past frame 5 or so. I'm not sure why. For now at
            # least, just calculate the endFrame ourselves to work around this.
            log.debug("Animating entity {} from frame {}/{}"
                      .format(gid, currFrame,
                              entity.model.getNumFrames("walk")))
            frameRate = entity.model.getAnimControl("walk").getFrameRate()
            endFrame = currFrame + int(math.ceil(frameRate *
                                                 config.TICK_LENGTH))
            animInterval = entity.model.actorInterval("walk", loop=1,
                startFrame=currFrame, endFrame=endFrame)
            animInterval.start()

    def markSelected(self, gid, isSelected):
        log.debug("Marking graphical entity {} as {}selected" \
            .format(gid, "" if isSelected else "not "))
        entity = self.entities[gid]

        z = 5 if isSelected else 0
        entity.model.setPos(0, 0, z)

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

        # Need a task to handle mouse-dragging because there doesn't seem to be
        # a built-in mouseMove event.
        self.taskMgr.add(self.mouseMoveTask, "MouseMoveTask")

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
        # This code is commented out as we need to have a selection algorithm
        # of identifying the unit to focus the camera on
        pass

        # if self.myId not in self.obelisks:
        #     return

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

    def handleMouseClick(self, button, modifiers):
        # Make sure the mouse is inside the screen
        if self.mouseWatcherNode.hasMouse():
            # Get the screen coordinates of the mouse, normalized to [-1, 1].
            mousePoint = self.mouseWatcherNode.getMouse()
            # Set selection rectangle start position. Note that we need to
            # create a copy of mousePoint rather than storing a reference,
            # because the referenced object will be modified in place by Panda.
            self.rectStartPos = (mousePoint.getX(), mousePoint.getY())

            # Make the ray extend from the camera, in the direction of the
            # mouse.
            self.mouseClickRay.setFromLens(self.camNode, mousePoint)

            # Check each object in the node tree for collision with the mouse.
            self.mouseClickTraverser.traverse(self.render)
            for entry in self.mouseClickHandler.getEntries():
                if not entry.hasInto():
                    continue
                # Check if each intersection is with the ground.
                if entry.getIntoNodePath() != self.groundPlaneNodePath:
                    continue
                if not self.usingCustomCamera:
                    continue

                clickedPoint = entry.getSurfacePoint(self.render)
                x, y, z = clickedPoint

                if modifiers == []:
                    # TODO: This component should take care of decoding the
                    # click as far as "left" or "right"; we shouldn't send a
                    # numerical button id to the graphicsInterface.
                    message = cmessages.Click(button, (x, y))
                elif button == 1 and modifiers == ["shift"]:
                    message = cmessages.ShiftLClick((x, y))
                elif button == 1 and modifiers == ["control"]:
                    message = cmessages.ControlLClick((x, y))
                elif button == 3 and modifiers == ["shift"]:
                    message = cmessages.ShiftRClick((x, y))
                elif button == 3 and modifiers == ["control"]:
                    message = cmessages.ControlRClick((x, y))
                else:
                    thisShouldNeverHappen(
                        "Unhandled modifiers for click: {}".format(modifiers))

                self.graphicsInterface.graphicsMessage(message.serialize())

    def handleMouseUp(self, button, modifiers):
        self.rectStartPos = None

    def mouseMoveTask(self, task):
        """
        Handle mouse movement.
        """

        # Check if the mouse is over the window.
        if base.mouseWatcherNode.hasMouse():
            # Get the position.
            # Each coordinate is normalized to the interval [-1, 1].
            # Create a copy of mousePoint to ensure we don't set
            # self.prevMousePos to be a reference to it, mousePoint will be
            # modified in place by Panda.
            mousePoint = base.mouseWatcherNode.getMouse()
            mousePos = (mousePoint.getX(), mousePoint.getY())
            # Don't do anything unless the mouse position has actually changed.
            if self.prevMousePos is not None:
                if mousePos != self.prevMousePos:
                    # Log a click-and-drag if we're clicking and dragging.
                    if self.rectStartPos is not None:
                        log.debug("Dragging from {} to {}"
                            .format(self.rectStartPos, mousePos))
                    self.prevMousePos = mousePos
                # If prevMousePos is not None and mousePos == prevMousePos,
                # don't update it, because that's pointless.
            else:
                self.prevMousePos = mousePos
        else:
            self.prevMousePos = None

        return Task.cont

    def handleWindowClose(self):
        log.info("Window close requested -- shutting down client.")
        message = cmessages.RequestQuit()
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
        self.accept("mouse1", self.handleMouseClick, [1, []])
        self.accept("mouse1-up", self.handleMouseUp, [1,[]])
        # TODO: Make sure this is always the right mouse button.
        self.accept("mouse3", self.handleMouseClick, [3, []])

        # Handle clicking with modifier keys.
        self.accept("shift-mouse1",   self.handleMouseClick, [1, ["shift"]])
        self.accept("control-mouse1", self.handleMouseClick, [1, ["control"]])
        self.accept("shift-mouse3",   self.handleMouseClick, [3, ["shift"]])
        self.accept("control-mouse3", self.handleMouseClick, [3, ["control"]])

        # Handle window close request (clicking the X, Alt-F4, etc.)
        self.win.set_close_request_event("window-close")
        self.accept("window-close", self.handleWindowClose)

    def logEvent(self, eventName):
        log.info("Received event {0!r}".format(eventName))


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

