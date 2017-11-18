import math

from src.shared.geometry import Coord, Distance, Rect
from src.shared.ident import encodeUnitId, parseUnitId
from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, InvalidMessageError
from src.shared.unit_set import UnitSet


###############################################################################
# Helper functions used by some of the argument specifications

# Int pair

def encodeIntPair(pair):
    assert len(pair) == 2
    # For now, force to int before str()ing the coordinates so that if old code
    # is still using floats, it doesn't mess up the parser on the other end. We
    # may want to eventually remove that cast; I'm not sure.
    return [str(int(x)) for x in pair]

def parseIntPair(descs):
    assert len(descs) == 2
    return tuple(map(int, descs))


# Float pair

def encodeFloatPair(pair):
    assert len(pair) == 2
    # Not sure if the cast to float here is really needed...
    return [str(float(x)) for x in pair]

def parseFloatPair(descs):
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
        #
        # TODO: Is this right? We now do this at a higher level -- any
        # exceptions raised during deserializeMessage are converted to
        # InvalidMessageErrors in a standard way. Is this going to mess that
        # up?
        raise InvalidMessageError(desc, "Could not parse floating-point value")

def isfinite(x):
    return not math.isinf(x) and not math.isnan(x)


# Booleans -- encoded using T and F so they don't look like integers.

def encodeBool(b):
    return "T" if b else "F"

def parseBool(desc):
    if desc == "T":
        return True
    elif desc == "F":
        return False
    else:
        raise ValueError


###############################################################################
# Argument specifications

# Specifications based on the underlying types. Don't use these directly; use
# the better-named ones that are aliases of these. These exist so that (for
# example) the three different type of pos args that all boil down to "pair of
# ints" can be implemented as a single underlying specification.
INT_ARG        = ArgumentSpecification(1, int)
BOOL_ARG       = ArgumentSpecification(1, parseBool, encodeBool)
INT_PAIR_ARG   = ArgumentSpecification(2, parseIntPair, encodeIntPair)
FLOAT_PAIR_ARG = ArgumentSpecification(2, parseFloatPair, encodeFloatPair)

PLAYER_ID_ARG  = INT_ARG
UNIT_SET_ARG   = ArgumentSpecification(1,
                                       UnitSet.deserialize,
                                       UnitSet.serialize)
UNIT_ID_ARG    = ArgumentSpecification(2, parseUnitId, encodeUnitId)
UNIT_TYPE_ARG = INT_ARG

# World coordinates.
POS_ARG        = ArgumentSpecification(2, Coord.deserialize, Coord.serialize)
DIST_ARG       = ArgumentSpecification(2,
                                       Distance.deserialize,
                                       Distance.serialize)
RECT_ARG       = ArgumentSpecification(4, Rect.deserialize, Rect.serialize)

# The type of ground on a certain chunk.
TERRAIN_TYPE_ARG = INT_ARG


###############################################################################
# The messages themselves

# Messages that are sent between client and server.

DeleteObelisk = defineMessageType("delete_obelisk",
                                  [("unitId", UNIT_ID_ARG)])
GroundInfo    = defineMessageType("ground_info",
                                  [("pos", POS_ARG),
                                   ("terrainType", TERRAIN_TYPE_ARG)])
MapSize       = defineMessageType("map_size",
                                  [("size", INT_PAIR_ARG)])
NewObelisk    = defineMessageType("new_obelisk",
                                  [("unitId", UNIT_ID_ARG),
                                   ("pos", POS_ARG)])
OrderDel      = defineMessageType("order_del", [("unitSet", UNIT_SET_ARG)])
OrderMove     = defineMessageType("order_move", [("unitSet", UNIT_SET_ARG),
                                                 ("dest", POS_ARG)])
OrderNew      = defineMessageType("order_new", [("unitType", UNIT_TYPE_ARG),
                                                ("pos", POS_ARG)])
ResourceAmt   = defineMessageType("resource_amount", [("amount", INT_ARG)])
ResourceLoc   = defineMessageType("resource_loc", [("pos", POS_ARG)])
SetPos        = defineMessageType("set_pos",
                                  [("unitId", UNIT_ID_ARG),
                                   ("pos", POS_ARG)])
Tick          = defineMessageType("tick", [])
YourIdIs      = defineMessageType("your_id_is", [("playerId", PLAYER_ID_ARG)])

