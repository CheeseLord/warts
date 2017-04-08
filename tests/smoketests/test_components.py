"""
Create an actual instance of one of the client/server components and make sure
we can talk to it.
"""

from twisted.internet import reactor, task
from twisted.internet.defer import Deferred

from src.client.backend import Backend as ClientBackend
from src.shared.message_infrastructure import deserializeMessage
from src.shared.messages import YourIdIs
from src.client.messages import RequestQuit

def test_backend_components():
    testDone = getMainDeferred()

    clientDone = Deferred()
    backend = ClientBackend(clientDone)

    # Give it some components.
    graphics_dummy = DummyComponent(backend.graphicsMessage)
    stdio_dummy    = DummyComponent(backend.stdioMessage)
    network_dummy  = DummyComponent(backend.networkMessage)

    # Tell it they're all ready. A fancier test might randomize the order of
    # these and insert some delays, but this is just a simple smoketest.
    backend.stdioReady(stdio_dummy)
    backend.networkReady(network_dummy)
    backend.graphicsInterfaceReady(graphics_dummy)

    def sendMessages():
        network_dummy.sendMessage(YourIdIs(42).serialize())
        graphics_dummy.sendMessage(RequestQuit().serialize())

    def finalChecks(x):
        # Check that the YourIdIs(42) was successfully forwarded to the
        # graphics interface.
        gotId = False
        for msgData in graphics_dummy.messageLog:
            msg = deserializeMessage(msgData)
            if isinstance(msg, YourIdIs):
                assert msg.playerId == 42
                gotId = True
        assert gotId

    clientDone.addCallback(finalChecks)
    clientDone.chainDeferred(testDone)

    # Make sure to chain the main Deferred's errback to that of this
    # deferLater, so that if something goes wrong in sendMessage then it will
    # be reported (rather than silently dropped).
    d = task.deferLater(reactor, 0.05, sendMessages)
    d.addErrback(testDone.errback)

    return testDone



# TODO: Move this to a shared file.
def getMainDeferred(timeout=1.0):
    """
    Create and return a Deferred object suitable for returning to
    pytest-twisted. Use this function instead of creating a Deferred directly,
    because this function does things like making sure the test will fail with
    a timeout if it doesn't otherwise finish quickly. Arguments:
        timeout -- duration until timeout, in seconds
    """

    mainDeferred = Deferred()

    # Schedule a timeout after 'timeout' seconds.
    timeoutError = RuntimeError("Test timed out after {} seconds."
                                .format(timeout))
    task.deferLater(reactor, timeout, mainDeferred.errback, timeoutError)

    return mainDeferred

class DummyComponent:
    def __init__(self, sendMessage):
        self.sendMessage = sendMessage
        self.messageLog  = []

    def backendMessage(self, msg):
        self.messageLog.append(msg)

    def cleanup(self):
        pass

