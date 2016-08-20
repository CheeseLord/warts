import math

def encodePosition(pos):
    x, y = pos
    return "{x} {y}".format(x=x, y=y)

def decodePosition(desc):
    """
    Parse a line of the form
        <x> <y>
    If successful, return (x, y), where x and y are floats.
    If not successful, return None.
    """

    parts = desc.split()
    try:
        pos = map(float, parts)
    except ValueError:
        return None

    if len(pos) != 2:
        return None
    x, y = pos
    if not (isfinite(x) and isfinite(y)):
        return None

    return pos

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)

