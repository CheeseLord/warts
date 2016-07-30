import math

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)


def parseFloatTuple(line, number=None):
    try:
        floatList = map(float, line.split())
        assert number == len(floatList)
    except:
        # FIXME: Don't just do except: return None
        return None
    else:
        if False not in map(isfinite, floatList):
            return floatList
