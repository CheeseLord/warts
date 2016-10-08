import math

from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification


###############################################################################
# Helper functions used by some of the argument specifications

def encodePos(pos):
    return map(str, pos)

def parsePos(descs):
    assert len(descs) == 2
    return tuple(map(parseFloat, descs))

def parseFloat(desc):
    val = float(desc)
    if not isfinite(val):
        # FIXME: Can't crash while handling external messages.
        raise ValueError("Floating-point value {0!r} ({1!r}) is not finite." \
            .format(desc, val))
    return val

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)


###############################################################################
# Argument specifications

idArg  = ArgumentSpecification(1, int)
# TODO: Distinguish screenPos from worldPos
posArg = ArgumentSpecification(2, parsePos, encodePos)


###############################################################################
# The messages themselves

Click         = defineMessageType("click", [("pos", posArg)])
DeleteObelisk = defineMessageType("delete_obelisk", [("playerId", idArg)])
MoveTo        = defineMessageType("move_to", [("dest", posArg)])
NewObelisk    = defineMessageType("new_obelisk",
                                  [("playerId", idArg), ("pos", posArg)])
RequestQuit   = defineMessageType("request_quit", [])
SetPos        = defineMessageType("set_pos",
                                  [("playerId", idArg), ("pos", posArg)])
YourIdIs      = defineMessageType("your_id_is", [("playerId", idArg)])
