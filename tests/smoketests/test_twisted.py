from twisted.internet import reactor, task


def test_deferred():
    return task.deferLater(reactor, 0.05, lambda: None)

