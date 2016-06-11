from math import pi, sin, cos
import sys
import os

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3, Mat4, Filename

def runPandaTest():
    app = MyApp()
    app.run()


class MyApp(ShowBase):
 
    def __init__(self):
        ShowBase.__init__(self)

        self.scene = self.loader.loadModel("environment")
        self.scene.reparentTo(self.render)
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)

        # Add a test model of our own creation, to check that we can use our
        # own models.
        self.testModel = self.loader.loadModel(getModelPath("test-model.egg"))
        self.testModel.reparentTo(self.render)
        self.testModel.setPos(-4, 0, 2.5)

        self.pandaActor = Actor("panda-model",
                                {"walk": "panda-walk4"})
        self.pandaActor.setScale(0.005, 0.005, 0.005)
        self.pandaActor.reparentTo(self.render)
        self.pandaActor.loop("walk")
 
        pandaPosInterval1 = self.pandaActor.posInterval(13,
                                                        Point3(0, -10, 0),
                                                        startPos=Point3(0, 10, 0))
        pandaPosInterval2 = self.pandaActor.posInterval(13,
                                                        Point3(0, 10, 0),
                                                        startPos=Point3(0, -10, 0))
        pandaHprInterval1 = self.pandaActor.hprInterval(3,
                                                        Point3(180, 0, 0),
                                                        startHpr=Point3(0, 0, 0))
        pandaHprInterval2 = self.pandaActor.hprInterval(3,
                                                        Point3(0, 0, 0),
                                                        startHpr=Point3(180, 0, 0))
 
        self.pandaPace = Sequence(pandaPosInterval1,
                                  pandaHprInterval1,
                                  pandaPosInterval2,
                                  pandaHprInterval2,
                                  name="pandaPace")
        self.pandaPace.loop()

        self.keys = {}
        self.setupKeyHandler()

        # Initialize camera control
        self.prevCameraPos = (0, 0, 100)
        self.prevCameraHpr = (0, -80, 0)
        self.setCameraCustom()

    def setCameraCustom(self):
        """
        Change to using our custom task to control the camera.
        """

        # Disable the default mouse-based camera control task, so we don't have
        # to fight with it for control of the camera.
        self.disableMouse()

        # Substitute our own camera control task.
        self.camera.setPos(self.prevCameraPos)
        self.camera.setHpr(self.prevCameraHpr)
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

    def spinCameraTask(self, task):
        """
        Spin the camera in a circle.
        """

        angleDegrees = task.time * 6.0
        angleRadians = angleDegrees * (pi / 180.0)
        self.camera.setPos(20 * sin(angleRadians), -20 * cos(angleRadians), 3)
        self.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont

    def updateCameraTask(self, task):
        """
        Move the camera sensibly.
        """

        # TODO: Find the right way to do this.
        self.camera.setHpr(0, 0, 0)

        speed = 1
        forward = speed * (self.keys["arrow_up"] - self.keys["arrow_down"])
        sideways = speed * (self.keys["arrow_right"] - self.keys["arrow_left"])
        self.camera.setPos(self.camera, sideways, forward, 0)

        self.camera.setHpr(0, -80, 0)

        return Task.cont

    def setupKeyHandler(self):
        def pushKey(key, value):
            self.keys[key] = value

        for key in ["arrow_up", "arrow_left", "arrow_right", "arrow_down",
                    "w", "a", "d", "s"]:
            self.keys[key] = False
            self.accept(key, pushKey, [key, True])
            self.accept("shift-%s" % key, pushKey, [key, True])
            self.accept("%s-up" % key, pushKey, [key, False])

        # Camera toggle
        self.accept("c",       self.toggleCameraStyle, [])
        self.accept("shift-c", self.toggleCameraStyle, [])


def getModelPath(modelname):
    """
    Return the Panda3D path for a model.
    """

    # https://www.panda3d.org/manual/index.php/Loading_Models
    mydir = os.path.abspath(sys.path[0])
    mydir = Filename.fromOsSpecific(mydir).getFullpath()

    # Can't use os.path.join here because mydir isn't an OS-specific path.
    if not mydir.endswith("/"):
        mydir += "/"
    return mydir + "assets/models/" + modelname
