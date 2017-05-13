import math
import os
import sys

from direct.task import Task  # This must be imported first.
from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from panda3d import core
from panda3d.core import Point2, Point3, Mat4, Filename, NodePath, LineSegs

from src.shared import config
from src.shared import messages
from src.shared.geometry import chunkToUnit
from src.shared.ident import unitToPlayer
from src.shared.logconfig import newLogger
from src.shared.message_infrastructure import deserializeMessage, \
    illFormedMessage, unhandledMessageCommand, invalidMessageArgument, \
    InvalidMessageError
from src.shared.unit_set import UnitSet
from src.shared.utils import minmax, thisShouldNeverHappen, thisIsNotHandled
from src.client.backend import unitToGraphics, GRAPHICS_SCALE
from src.client import messages as cmessages

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

        # Mapping from gids to entities.
        self.entities = {}

        # Set up event handling.
        self.mouseState = {}
        self.keys = {}
        self.setupEventHandlers()

        # Set up camera control.
        self.cameraHolder = self.render.attachNewNode('CameraHolder')
        self.cameraHolder.setPos(0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.setCameraCustom()

        self.prevMousePos = None
        self.selectionBox = None
        self.selectionBoxNode = None
        self.selectionBoxOrigin = None

        # Define the ground plane by a normal (+z) and a point (the origin).
        self.groundPlane = core.Plane(core.Vec3(0, 0, 1), core.Point3(0, 0, 0))

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

    def createSelectionBox(self, corner1, corner2):
        """
        Create a selection "box" given the coordinates of two opposite corners.
        The corners are given in world coordinates (well, 3d graphics
        coordinates).
        """

        assert self.selectionBox is None

        p1, p2, p3, p4 = self.convert3dBoxToScreen(corner1, corner2)
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        # TODO[#3]: Magic numbers bad.
        self.selectionBox = LineSegs("SelectionBox")
        self.selectionBox.setThickness(3.0)
        self.selectionBox.setColor(0.0, 1.0, 0.25, 1.0)
        self.selectionBox.move_to(x1, 0, y1)
        self.selectionBox.draw_to(x2, 0, y2)
        self.selectionBox.draw_to(x3, 0, y3)
        self.selectionBox.draw_to(x4, 0, y4)
        self.selectionBox.draw_to(x1, 0, y1)

        self.selectionBoxNode = render2d.attachNewNode(
            self.selectionBox.create())

    def moveSelectionBox(self, corner1, corner2):
        assert self.selectionBox is not None

        p1, p2, p3, p4 = self.convert3dBoxToScreen(corner1, corner2)
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        self.selectionBox.setVertex(0, x1, 0, y1)
        self.selectionBox.setVertex(1, x2, 0, y2)
        self.selectionBox.setVertex(2, x3, 0, y3)
        self.selectionBox.setVertex(3, x4, 0, y4)
        self.selectionBox.setVertex(4, x1, 0, y1)

    def removeSelectionBox(self):
        self.selectionBoxNode.removeNode()
        self.selectionBox     = None
        self.selectionBoxNode = None

    def convert3dBoxToScreen(self, corner1, corner3):
        """
        Return screen coordinates of the 4 corners of a box, given in 3d
        coordinates. The box is specified using 2 opposite corners.
        """

        wx1, wy1, wz1 = corner1
        wx3, wy3, wz3 = corner3

        wx2, wy2 = (wx1, wy3)
        wx4, wy4 = (wx3, wy1)

        # Note: corner1 and corner2 could have nonzero z because floating-point
        # calculations, but they should at least be close. We'll just average
        # their z and not worry about it.
        wz2 = wz4 = 0.5 * (wz1 + wz3)

        p1 = self.coord3dToScreen((wx1, wy1, wz1))
        p2 = self.coord3dToScreen((wx2, wy2, wz2))
        p3 = self.coord3dToScreen((wx3, wy3, wz3))
        p4 = self.coord3dToScreen((wx4, wy4, wz4))

        return (p1, p2, p3, p4)

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

        if sideways != 0 or forward != 0:
            self.updateSelectionBox()

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

    def centerView(self):
        """
        Center the view sensibly.
        """

        message = cmessages.RequestCenter()
        self.graphicsInterface.graphicsMessage(message.serialize())

    def mouseMoveTask(self, task):
        """
        Handle mouse movement.
        """

        mousePos = self.getMousePos()

        # NOTE: We don't handle clicking and dragging at the same time.
        if mousePos is not None and mousePos != self.prevMousePos:
            for (buttonId, state) in self.mouseState.iteritems():
                if state.hasMoved:
                    self.handleMouseDragMove(buttonId, state.modifiers,
                                             state.pos, mousePos)
                else:
                    startX, startY = state.pos
                    mouseX, mouseY = mousePos
                    distance = math.hypot(mouseX - startX, mouseY - startY)
                    # TODO[#3]: Magic numbers bad.
                    # Check if the mouse has moved outside the dead zone.
                    if distance > 0.0314:
                        self.handleMouseDragStart(buttonId, state.modifiers,
                                                  state.pos, mousePos)
                        state.hasMoved = True

        if mousePos != self.prevMousePos:
            self.prevMousePos = mousePos

        return Task.cont

    def pandaEventMouseDown(self, buttonId, modifiers):
        if buttonId in self.mouseState:
            # Call pandaEventMouseUp just to clear any state related to the
            # button being down, so we can handle this buttonDown event as if
            # it were a fresh press of the button.
            log.warn("Mouse button {} is already down.".format(buttonId))
            self.pandaEventMouseUp(buttonId)

        assert buttonId not in self.mouseState

        state = MouseButtonState(modifiers[:], self.getMousePos(), False)
        self.mouseState[buttonId] = state

    def pandaEventMouseUp(self, buttonId):
        if buttonId not in self.mouseState:
            # Drop the event, since there's nothing to do.
            log.warn("Mouse button {} is already up.".format(buttonId))
            return

        state = self.mouseState[buttonId]

        if state.hasMoved:
            self.handleMouseDragEnd(buttonId, state.modifiers,
                                    state.pos, self.getMousePos())
        else:
            self.handleMouseClick(buttonId, state.modifiers, state.pos)

        del self.mouseState[buttonId]

    def handleMouseClick(self, button, modifiers, pos):
        # Make sure the mouse is inside the screen
        # TODO: Move this check to pandaEventMouseUp?
        if self.mouseWatcherNode.hasMouse() and self.usingCustomCamera:
            x, y, z = self.coordScreenTo3d(pos)

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

    def handleMouseDragStart(self, buttonId, modifiers, startPos, endPos):
        log.debug("Start dragging from {} to {}".format(startPos, endPos))

        if buttonId == 1 and modifiers == []:
            assert self.selectionBoxOrigin is None
            self.selectionBoxOrigin = self.coordScreenTo3d(startPos)
            endPos = self.coordScreenTo3d(endPos)
            self.createSelectionBox(self.selectionBoxOrigin, endPos)

    def handleMouseDragMove(self, buttonId, modifiers, startPos, endPos):
        log.debug("Continue dragging from {} to {}".format(startPos, endPos))

        if buttonId == 1 and modifiers == []:
            assert self.selectionBoxOrigin is not None
            endPos = self.coordScreenTo3d(endPos)
            self.moveSelectionBox(self.selectionBoxOrigin, endPos)

    def handleMouseDragEnd(self, buttonId, modifiers, startPos, endPos):
        log.debug("End dragging from {} to {}".format(startPos, endPos))

        if buttonId == 1 and modifiers == []:
            # Actually select the units.
            endPos = self.coordScreenTo3d(endPos)
            # TODO[#55]: Use 3d graphics coords in messages so we don't have to
            # remove the z coordinates everywhere.
            message = cmessages.DragBox(self.selectionBoxOrigin[:2],
                                        endPos[:2])
            self.graphicsInterface.graphicsMessage(message.serialize())
            # Clear the selection box; we're done dragging.
            self.selectionBoxOrigin = None
            self.removeSelectionBox()

    def updateSelectionBox(self):
        if self.selectionBoxOrigin is not None:
            mousePos = self.getMousePos()
            if mousePos is not None:
                endPos = self.coordScreenTo3d(mousePos)
                self.moveSelectionBox(self.selectionBoxOrigin, endPos)

    def getMousePos(self):
        # Check if the mouse is over the window.
        if base.mouseWatcherNode.hasMouse():
            # Get the position.
            # Each coordinate is normalized to the interval [-1, 1].
            mousePoint = base.mouseWatcherNode.getMouse()
            # Create a copy of mousePoint rather than returning a reference to
            # it, because mousePoint will be modified in place by Panda.
            return (mousePoint.getX(), mousePoint.getY())
        else:
            log.debug("getMousePos() called but mouse is not over window.")
            return None

    def handleWindowClose(self):
        log.info("Window close requested -- shutting down client.")
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
        self.accept("space", self.centerView, [])

        # Handle mouse wheel.
        self.accept("wheel_up", self.zoomCamera, [True])
        self.accept("wheel_down", self.zoomCamera, [False])

        # Handle clicking.
        self.accept("mouse1",    self.pandaEventMouseDown, [1, []])
        self.accept("mouse1-up", self.pandaEventMouseUp,   [1])
        # TODO: Make sure this is always the right mouse button.
        self.accept("mouse3",    self.pandaEventMouseDown, [3, []])
        self.accept("mouse3-up", self.pandaEventMouseUp,   [3])

        # Handle clicking with modifier keys.
        self.accept("shift-mouse1",   self.pandaEventMouseDown,
                    [1, ["shift"]])
        self.accept("control-mouse1", self.pandaEventMouseDown,
                    [1, ["control"]])
        self.accept("shift-mouse3",   self.pandaEventMouseDown,
                    [3, ["shift"]])
        self.accept("control-mouse3", self.pandaEventMouseDown,
                    [3, ["control"]])

        # Handle window close request (clicking the X, Alt-F4, etc.)
        self.win.set_close_request_event("window-close")
        self.accept("window-close", self.handleWindowClose)

    def logEvent(self, eventName):
        log.info("Received event {0!r}".format(eventName))

    def coord3dToScreen(self, coord3d):
        # Empirically, Lens.project takes coordinates in the *camera*'s
        # coordinate system, not its parent or the render. This was not very
        # clear from the documentation, and you'd be surprised how long it took
        # us to figure this out. Anyway, we need to convert the point to be
        # relative to self.camera here; otherwise we'll get bizarre,
        # nonsensical, and hard-to-debug results.
        coord3d = self.camera.getRelativePoint(self.render, coord3d)
        screenCoord = Point2()
        if not self.camLens.project(coord3d, screenCoord):
            log.debug("Attempting 3d-to-screen conversion on point outside of "
                      "camera's viewing frustum.")

        # Convert to a tuple to ensure no one else is keeping a reference
        # around.
        x, y = screenCoord
        return (x, y)

    def coordScreenTo3d(self, screenCoord):
        x, y = screenCoord
        screenPoint = Point2(x, y)

        # Do this calculation using simple geometry, rather than the absurd
        # collision-traversal nonsense we used to use. Thanks to
        #     https://www.panda3d.org/forums/viewtopic.php?t=5409
        # for pointing us at the right methods to make this work.

        # Get two points along the ray extending from the camera, in the
        # direction of the mouse click.
        nearPoint = Point3()
        farPoint = Point3()
        self.camLens.extrude(screenPoint, nearPoint, farPoint)

        # These points are relative to the camera, so need to be converted to
        # be relative to the render. Thanks to the example code (see link
        # above) for saving us probably some hours of debugging figuring that
        # one out again :)
        nearPoint = self.render.getRelativePoint(self.camera, nearPoint)
        farPoint  = self.render.getRelativePoint(self.camera, farPoint)

        intersection = Point3()
        if self.groundPlane.intersectsLine(intersection, nearPoint, farPoint):
            # Convert to a tuple to ensure no one else is keeping a reference
            # around.
            x, y, z = intersection
            return (x, y, z)

        # The ray didn't intersect the ground. This is almost certainly going
        # to happen at some point; all you have to do is find a way to aim the
        # camera (or manipulate the screen coordinate) so that the ray points
        # horizontally. But we don't have code to handle it, so for now just
        # abort.
        thisIsNotHandled()


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


class MouseButtonState(object):
    def __init__(self, modifiers, pos, hasMoved):
        super(MouseButtonState, self).__init__()
        self.modifiers = modifiers
        self.pos       = pos
        self.hasMoved  = hasMoved


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

