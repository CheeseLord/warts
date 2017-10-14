from src.shared.message_infrastructure import defineMessageType, \
    ArgumentSpecification
from src.shared.messages import BOOL_ARG, INT_ARG, FLOAT_PAIR_ARG, UNIT_ID_ARG


###############################################################################
# Argument specifications

GRAPHICS_ID_ARG = INT_ARG
G_POS_ARG       = FLOAT_PAIR_ARG  # Graphics position

MODEL_PATH_ARG  = ArgumentSpecification(1, str, unsafe=True)


###############################################################################
# The messages themselves

# TODO[#9]: Get rid of isExample argument; replace with more generic isActor
# (or hasAnimations?).
AddEntity          = defineMessageType("add_entity",
                                       [("gid", GRAPHICS_ID_ARG),
                                        ("pos", G_POS_ARG),
                                        ("isExample", BOOL_ARG),
                                        ("isUnit", BOOL_ARG),
                                        ("goalSize", FLOAT_PAIR_ARG),
                                        ("modelPath", MODEL_PATH_ARG)])
CenterCamera       = defineMessageType("center_camera",
                                       [("pos", G_POS_ARG)])
Click              = defineMessageType("click",
                                       [("button", INT_ARG),
                                        ("pos", G_POS_ARG)])
ShiftLClick        = defineMessageType("shift_left_click",
                                       [("pos", G_POS_ARG)])
ControlLClick      = defineMessageType("control_left_click",
                                       [("pos", G_POS_ARG)])
ShiftRClick        = defineMessageType("shift_right_click",
                                       [("pos", G_POS_ARG)])
ControlRClick      = defineMessageType("control_right_click",
                                       [("pos", G_POS_ARG)])
DragBox            = defineMessageType("drag_box",
                                       [("corner1", G_POS_ARG),
                                        ("corner2", G_POS_ARG)])
DisplayResources   = defineMessageType("display_resources",
                                       [("resourceAmt", INT_ARG)])
MarkEntitySelected = defineMessageType("mark_entity_selected",
                                       [("gid", GRAPHICS_ID_ARG),
                                        ("isSelected", BOOL_ARG)])
MarkUnitSelected   = defineMessageType("mark_unit_selected",
                                       [("unitId", UNIT_ID_ARG),
                                        ("isSelected", BOOL_ARG)])
MoveEntity         = defineMessageType("move_entity",
                                       [("gid", GRAPHICS_ID_ARG),
                                        ("pos", G_POS_ARG)])
RemoveEntity       = defineMessageType("remove_entity",
                                       [("gid", GRAPHICS_ID_ARG)])
RequestCenter      = defineMessageType("request_center", [])
RequestQuit        = defineMessageType("request_quit", [])

