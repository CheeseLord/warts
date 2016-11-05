import math

from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, InvalidMessageError


###############################################################################
# Helper functions used by some of the argument specifications

def encodePos(pos):
    assert len(pos) == 2
    # For now, force to int before str()ing the coordinates so that if old code
    # is still using floats, it doesn't mess up the parser on the other end. We
    # may want to eventually remove that cast; I'm not sure.
    return [str(int(x)) for x in pos]

def parsePos(descs):
    assert len(descs) == 2
    return tuple(map(int, descs))


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
