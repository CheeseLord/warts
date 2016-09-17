# TODO: parsePos and encodePos should probably just be moved into this
# module....
from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, parsePos, encodePos


# Types of arguments used by the messages.
idArg  = ArgumentSpecification(1, int)
# TODO: Distinguish screenPos from worldPos
posArg = ArgumentSpecification(2, parsePos, encodePos)


# The messages themselves.
Click         = defineMessageType("click", [("pos", posArg)])
DeleteObelisk = defineMessageType("delete_obelisk", [("playerId", idArg)])
NewObelisk    = defineMessageType("new_obelisk",
                                  [("playerId", idArg), ("pos", posArg)])
RequestQuit   = defineMessageType("request_quit", [])
SetPos        = defineMessageType("set_pos",
                                  [("playerId", idArg), ("pos", posArg)])
YourIdIs      = defineMessageType("your_id_is", [("playerId", idArg)])
