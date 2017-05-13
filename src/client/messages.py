from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification, InvalidMessageError
from src.shared.messages import boolArg, intArg, floatPairArg, unitIdArg


###############################################################################
# Argument specifications

graphicsIdArg = intArg
gPosArg       = floatPairArg  # Graphics position

modelPathArg  = ArgumentSpecification(1, str, unsafe=True)


###############################################################################
# The messages themselves

# TODO[#9]: Get rid of isExample argument; replace with more generic isActor
# (or hasAnimations?).
AddEntity          = defineMessageType("add_entity",
                                       [("gid", graphicsIdArg),
                                        ("pos", gPosArg),
                                        ("isExample", boolArg),
                                        ("goalSize", floatPairArg),
                                        ("modelPath", modelPathArg)])
CenterCamera       = defineMessageType("center_camera",
                                       [("pos", gPosArg)])
Click              = defineMessageType("click",
                                       [("button", intArg),
                                        ("pos", gPosArg)])
ShiftLClick        = defineMessageType("shift_left_click",
                                       [("pos", gPosArg)])
ControlLClick      = defineMessageType("control_left_click",
                                       [("pos", gPosArg)])
ShiftRClick        = defineMessageType("shift_right_click",
                                       [("pos", gPosArg)])
ControlRClick      = defineMessageType("control_right_click",
                                       [("pos", gPosArg)])
DragBox            = defineMessageType("drag_box",
                                       [("corner1", gPosArg),
                                        ("corner2", gPosArg)])
MarkEntitySelected = defineMessageType("mark_entity_selected",
                                       [("gid", graphicsIdArg),
                                        ("isSelected", boolArg)])
MarkUnitSelected   = defineMessageType("mark_unit_selected",
                                       [("unitId", unitIdArg),
                                        ("isSelected", boolArg)])
MoveEntity         = defineMessageType("move_entity",
                                       [("gid", graphicsIdArg),
                                        ("pos", gPosArg)])
RemoveEntity       = defineMessageType("remove_entity",
                                       [("gid", graphicsIdArg)])
RequestCenter      = defineMessageType("request_center", [])
RequestQuit        = defineMessageType("request_quit", [])

