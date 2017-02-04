from twisted.internet import reactor, task
from twisted.internet.defer import Deferred, succeed
from twisted.python.failure import Failure


def test_deferred():
    return task.deferLater(reactor, 0.05, lambda: None)


def test_failure():
    """
    Test that we can check for a failure in an asynchronously-called function.
    """

    # Create one Deferred for the result of the test function.
    deferredThatFails = task.deferLater(reactor, 0.05, functionThatFails)

    # Create another Deferred, which will give the opposite result of
    # deferredThatFails (that is, which will succeed if deferredThatFails fails
    # and vice versa).
    deferredThatSucceeds = Deferred()

    # It's tempting to just write something like:
    #
    #     deferredThatFails.addCallback(deferredThatSucceeds.errback)
    #     deferredThatFails.addErrback (deferredThatSucceeds.callback)
    #
    # Unfortunately, that doesn't work. The problem is that each callback or
    # errback in a Deferred's callback/errback chain is passed the result of
    # the previous callback/errback, and execution switches between those
    # chains depending on whether that result is a failure or not. So if a
    # callback returns a failure, we switch to the errbacks, and if an errback
    # doesn't return a failure, we switch to the callbacks. If we use the
    # above, then when deferredThatFails fails, the following will happen:
    #
    #   - deferredThatFails' first (and only) errback is called: the function
    #     deferredThatSucceeds.callback. It is passed some sort of failure
    #     object.
    #   - This causes deferredThatSucceeds to fire. We start its callback
    #     chain, passing in that same failure object that was passed to
    #     deferredThatFails' errback chain.
    #   - Since this is a failure object, we switch to the errback chain of
    #     deferredThatSucceeds. I believe this happens before the first
    #     callback is executed, because that callback is probably something
    #     setup by pytest that would cause the test to pass. So it looks like
    #     what's happening is we're bypassing that function entirely, and going
    #     straight to the errback, which causes the test to fail.
    #
    # The solution is to instead create two functions of our own, which call
    # deferredThatSucceeds.callback and .errback but change whether the
    # argument is a failure so that it won't cause us to switch between the
    # callback and errback chains.

    def passTest(arg):
        # arg is a failure object of some sort. Don't pass it to callback
        # because otherwise it'll trigger the errback, which will cause the
        # test to fail.
        deferredThatSucceeds.callback(None)
    def failTest(arg):
        # Manufacture a failure to pass to errback because otherwise twisted
        # will switch to the callback chain, causing the test to pass.
        theFailure = Failure(AssertionError("functionThatFails didn't fail"))
        deferredThatSucceeds.errback(theFailure)

    deferredThatFails.addCallbacks(failTest, passTest)

    return deferredThatSucceeds

def functionThatFails():
    assert False

