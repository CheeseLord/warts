import math

from src.shared.unit_set import UnitSet
from src.shared.ident import encodeUnitId, parseUnitId
from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, InvalidMessageError


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
intArg       = ArgumentSpecification(1, int)
boolArg      = ArgumentSpecification(1, parseBool, encodeBool)
intPairArg   = ArgumentSpecification(2, parseIntPair, encodeIntPair)
floatPairArg = ArgumentSpecification(2, parseFloatPair, encodeFloatPair)

modelPathArg = ArgumentSpecification(1, str, unsafe=True)

playerIdArg  = intArg
unitSetArg   = ArgumentSpecification(1, UnitSet.deserialize, UnitSet.serialize)
unitIdArg    = ArgumentSpecification(2, parseUnitId, encodeUnitId)

# Different types of coordinates. For now at least, all bug graphics are
# encoded and parsed exactly the same way.
uPosArg = intPairArg    # Unit position  (unit movements)
bPosArg = intPairArg    # Build position (build grid)
cPosArg = intPairArg    # Chunk position (terrain tiles)
gPosArg = floatPairArg  # Graphics position (intra-client messages only)

# The type of ground on a certain chunk.
terrainTypeArg = intArg

graphicsIdArg = intArg


###############################################################################
# The messages themselves

# Messages that are sent between client and server.

DeleteObelisk = defineMessageType("delete_obelisk",
                                  [("unitId", unitIdArg)])
GroundInfo    = defineMessageType("ground_info",
                                  [("pos", cPosArg),
                                   ("terrainType", terrainTypeArg)])
NewObelisk    = defineMessageType("new_obelisk",
                                  [("unitId", unitIdArg),
                                   ("pos", uPosArg)])
OrderDel      = defineMessageType("order_del", [("unitId", unitIdArg)])
OrderMove     = defineMessageType("order_move", [("unitSet", unitSetArg),
                                                 ("dest", uPosArg)])
OrderNew      = defineMessageType("order_new", [("pos", uPosArg)])
SetPos        = defineMessageType("set_pos",
                                  [("unitId", unitIdArg),
                                   ("pos", uPosArg)])
YourIdIs      = defineMessageType("your_id_is", [("playerId", playerIdArg)])


# Purely intra-client messages.

# TODO[#9]: Get rid of isExample argument; replace with more generic isActor
# (or hasAnimations?).
AddEntity       = defineMessageType("add_entity",
                                    [("gid", graphicsIdArg),
                                     ("pos", gPosArg),
                                     ("isExample", boolArg),
                                     ("modelPath", modelPathArg)])
# TODO: This is getting out of hand. Now there are two of them.
AddScaledEntity = defineMessageType("add_scaled_entity",
                                    [("gid", graphicsIdArg),
                                     ("pos", gPosArg),
                                     ("isExample", boolArg),
                                     ("scaleTo", floatPairArg),
                                     ("modelPath", modelPathArg)])
Click           = defineMessageType("click",
                                    [("button", intArg),
                                     ("pos", gPosArg)])
MoveEntity      = defineMessageType("move_entity",
                                    [("gid", graphicsIdArg),
                                     ("pos", gPosArg)])
RemoveEntity    = defineMessageType("remove_entity", [("gid", graphicsIdArg)])
RequestQuit     = defineMessageType("request_quit", [])

