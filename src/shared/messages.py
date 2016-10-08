import math

from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, InvalidMessageError


###############################################################################
# Helper functions used by some of the argument specifications

def encodePos(pos):
    return map(str, pos)

def parsePos(descs):
    assert len(descs) == 2
    return tuple(map(parseFloat, descs))

def parseFloat(desc):
    try:
        val = float(desc)
        if not isfinite(val):
            raise ValueError
        return val
    except ValueError:
        # Convert any exceptions raised during parsing into
        # InvalidMessageErrors, so that we'll handle them correctly and not
        # crash due to an invalid external message.
        #
        # Note: this isn't really quite right -- the full message isn't desc,
        # but rather something like "set_pos 2 {desc} 1.6" -- but we don't have
        # access to the full message, so this is the best we can do.
        raise InvalidMessageError(desc, "Could not parse floating-point value")

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
