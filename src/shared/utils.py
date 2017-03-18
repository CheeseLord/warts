def minmax(a, b):
    "return (min(a, b), max(a, b))"
    if a <= b:
        return (a, b)
    else:
        return (b, a)

def thisShouldNeverHappen(reason=None):
    if reason == None:
        reason = "This should never happen"
    assert False, reason

