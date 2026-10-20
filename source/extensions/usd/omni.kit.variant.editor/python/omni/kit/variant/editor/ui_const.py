# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.app
import omni.ui as ui


class COLORS:
    CLR_0 = 0xFF080808
    CLR_1 = 0xFF181818
    CLR_2 = 0xFF282828
    CLR_3 = 0xFF383838
    CLR_4 = 0xFF484848
    CLR_5 = 0xFF585858
    CLR_6 = 0xFF686868
    CLR_7 = 0xFF787878
    CLR_8 = 0xFF888888
    CLR_9 = 0xFF989898
    CLR_A = 0xFFA8A8A8
    CLR_B = 0xFFB8B8B8
    CLR_C = 0xFFCCCCCC
    CLR_D = 0xFFE0E0E0
    CLR_E = 0xFFF4F4F4
    CLR_RED = 0xFF5555AA
    CLR_BRIGHT_RED = 0xFF6666EE
    CLR_GREEN = 0xFF76A371
    CLR_BRIGHT_GREEN = 0xFF87E782
    CLR_LIGHT_BLUE = 0xFFFFC110  # Closer match to designs
    CLR_BLUE = 0xFFFFC734  # World opinion color
    CLR_BRIGHT_BLUE = 0xFFF2D98B  # Highlighted World opinion
    CLR_ORANGE = 0xFF34B5FF  # Local opinion color
    CLR_BRIGHT_ORANGE = 0xFFACDCF9  # Highlighted Local opinion
    CLR_TRANSLUCENT_LIGHT_BLUE = 0x44FFC110

    LIGHTER_GRAY = 0xFF3D3B38
    GRAY = 0xFF282625
    DARKER_GREY = 0xFF23211F

    TRANSPARENT = 0x0000000

    BLACK = 0xFF000000
    WHITE = 0xFFFFFFFF

    TEXT_DISABLED_LIGHT = 0xFFA0A0A0
    TEXT_DISABLED_DARK = 0xFF8B8A8A
    TEXT_SELECTED = 0xFFC5911A

    WIDGET_BACKGROUND_LIGHT = 0xFF535354
    WIDGET_BACKGROUND_DARK = 0xFF23211F

    BUTTON_BACKGROUND_LIGHT = 0xFFD6D6D6


class LightColors:
    Background = COLORS.WIDGET_BACKGROUND_LIGHT
    BackgroundSelected = COLORS.CLR_4
    BackgroundHovered = COLORS.CLR_4
    Text = COLORS.CLR_D
    TextDisabled = COLORS.TEXT_DISABLED_LIGHT
    TextSelected = COLORS.TEXT_SELECTED
    Button = COLORS.BUTTON_BACKGROUND_LIGHT
    ButtonHovered = COLORS.CLR_B
    ButtonPressed = COLORS.CLR_A
    ButtonSelected = 0xFFCFCCBF
    WindowBackground = COLORS.CLR_D


class DarkColors:
    Background = COLORS.WIDGET_BACKGROUND_DARK
    BackgroundSelected = 0xFF7E7E7E
    BackgroundHovered = 0xFF6E6E6E
    Text = COLORS.CLR_C
    TextDisabled = COLORS.TEXT_DISABLED_DARK
    TextSelected = COLORS.TEXT_SELECTED
    Button = COLORS.WIDGET_BACKGROUND_DARK
    ButtonHovered = 0xFF9E9E9E
    ButtonPressed = 0xFF787569
    ButtonSelected = 0xFF4F383F
    WindowBackground = 0xFF454545


# Paths
PATH_EXTENSION = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
PATH_MENU_ENTRY = "Variant Editor"
PATH_NAME_TOOL = "Variant Editor"
PATH_ICON_ADD_DARK = "/data/plus_green.svg"
PATH_ICON_EXPAND = "/data/expand.svg"
PATH_ICON_COLLAPSE = "/data/collapse.svg"
PATH_ICON_REMOVE_DARK = "/data/remove_dark.svg"
PATH_ICON_PICK_PRIM = "/data/select.svg"
PATH_ICON_BROWSE = "/data/small_folder.png"
PATH_ICON_FIND = "/data/find.png"
PATH_ICON_THUMBNAIL = "/data/thumbnail_dark.svg"
PATH_ICON_XFORM_GNOMON = "/data/xform_gnomon.svg"
PATH_ICON_EYE = "/data/eye_dark.svg"
PATH_ICON_SPHERE = "/data/sphere_dark.png"
PATH_ICON_CUBE = "/data/cube_dark.svg"
PATH_ICON_VERT_LINES = "/data/vertical_lines.png"
PATH_ICON_CIRCLE_X = "/data/times_circle.svg"
PATH_ICON_REFRESH = "/data/sync.svg"
PATH_ICON_VARIANT_INHERITED = "/data/state_indicator_inherited.svg"
PATH_ICON_VARIANT_LOCAL = "/data/state_indicator_local.svg"
PATH_ICON_VARIANT_VARIANT = "/data/state_indicator_variant.svg"
PATH_ICON_CONTEXT_MENU = "/data/variant_icon_context_menu.png"
PATH_ICON_OPTIONS = "/data/options.svg"

# Tooltips
TOOLTIP_TEST = """Test Tooltip
"""
TOOLTIP_SELECT_PRIM = """Select a new target prim
"""
TOOLTIP_BUTTON_ADD_VARIANT = """Add a Variant to this Variant Set
"""
TOOLTIP_BUTTON_ADD_VARIANT_SET = """Add Variant Set to the target prim
"""
TOOLTIP_BUTTON_ADD_PROPERTY = """Add one or more properties to the variant
"""
TOOLTIP_LABEL_REFERENCES = """All information for the references
"""
TOOLTIP_LABEL_PAYLOADS = """All information for the payloads
"""
TOOLTIP_BUTTON_VARIANTSET_PROPERTY = """Variant Selections can be modified by other Variants.  Choose which Variant should be selected.
"""
TOOLTIP_BUTTON_OPINION_AUDITOR = """One or more opinions are overriding your variant opinion
"""
TOOLTIP_BUTTON_VARIANT_OPTIONS = """Variant Editor Options
"""
TOOLTIP_BUTTON_CREATE_VISIBILITY_BY_DEFAULT = """Drag and drop will create visibility variants by default if enabled.  If disabled, drag and drop will create payload or reference variants instead
"""

# Guide Text
GUIDE_TEXT_NO_PRIM = """No valid prim is selected.

Please select a valid prim to begin creating or editing variants.
"""
GUIDE_TEXT_NO_SETS = """There are no variants to edit on this prim.

Click the "Add New Variant Set" button to add a variant set.

You can also drag and drop assets from the content browser into the left column to create a reference variant.
"""
GUIDE_TEXT_NO_SELECTION = """Please select a variant to edit
"""

# Options Text
ADD_PROP_TO_ALL_VARIANTS_TEXT = """Add Prims/Properties to All Variants"""
CREATE_VISIBILITY_BY_DEFAULT_TEXT = """Drag and Drop Mode - Visibility"""


# Defaults
DEFAULT_WIDGET_VALUE = True
DEFAULT_OTHER_WIDGET_VALUE = 1
DEFAULT_REFERENCE_STRING = "<Default Value>"

# Width & Height
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 680
VARIANT_SET_CARD_HEIGHT = 20
PROPERTY_WINDOW_WIDTH = 300
PROPERTY_WINDOW_HEIGHT = 500

# Property Widgets
PROPERTY_LABEL_WIDTH = 150
PROPERTY_LABEL_WIDTH_LIGHT = 150
PROPERTY_LABEL_HEIGHT = 18
PROPERTY_HORIZONTAL_SPACING = 4

# Global Stylings
BUTTON_BORDER_RADIUS = 2

# Window Style
WINDOW_STYLE = {
    "margin": 2,
}

STYLE_TOOLTIP = {
    "color": 0xCC000000,
    "background_color": 0xFFAADDDD,
    "border_width": 0,
    "margin": -1,
    "border_width": 0,
}

STYLE_TOOLTIP_TEXT = {"margin": 3}

# Button styling for: Add Variant Set, Add Prim, Done
STYLE_BUTTON = {
    "color": COLORS.CLR_C,
    "background_color": DarkColors.Button,
    "border_radius": BUTTON_BORDER_RADIUS,
    ":hovered": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonHovered},
    ":pressed": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonPressed},
}

# Pick prim button at the end of Variant Set Prim Location text field
STYLE_PICK_PRIM_BUTTON = {
    "margin": 2,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_PICK_PRIM}",
    "background_color": COLORS.CLR_3,
    "color": COLORS.CLR_C,
    "padding": 2,
    ":hovered": {"color": COLORS.CLR_E, "background_color": COLORS.CLR_8},
    ":pressed": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonPressed},
}

STYLE_MENU_BUTTON = {
    "color": COLORS.CLR_C,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_OPTIONS}",
    "background_color": DarkColors.Button,
    "border_radius": BUTTON_BORDER_RADIUS,
    ":hovered": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonHovered},
    ":pressed": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonPressed},
}

STYLE_TEXT_LABEL = {"color": COLORS.CLR_C}  # General text labels

# The entire variant set list view
STYLE_VARIANT_SET_LIST = {
    "background_color": COLORS.GRAY,
    "margin": 0,
}

# Variant Set Card Header
STYLE_VARIANT_SET_CARD = {
    "font_size": 14,
    "margin": 0,
    "padding": 2,
    "color": COLORS.CLR_C,
    "background_color": COLORS.GRAY,
}

# The individual variant lists
STYLE_VARIANT_LIST = {
    "background_color": 0xAA282625,
    "margin": 0,
    "padding": 0,
}

# Variant item card (Item in Set list)
STYLE_VARIANT_CARD = {
    "font_size": 14,
    "margin": 1,
    "padding": 2,
    "color": COLORS.CLR_B,
}

STYLE_VARIANT_CARD_ACTIVATED = {
    "font_size": 14,
    "margin": 1,
    "padding": 2,
    "color": COLORS.CLR_LIGHT_BLUE,
}

STYLE_VARIANT_RECT = {"border_radius": 1, "background_color": COLORS.TRANSPARENT}

STYLE_ACTIVE_VARIANT_RECT = {
    "border_radius": 1,
    "background_color": COLORS.CLR_LIGHT_BLUE,
}

# Variant Set Prim Location ui.StringField
STYLE_STRING_FIELD = {
    "color": COLORS.CLR_A,
    "border_radius": 1,
    "font_size": 14,
    "padding": 5,
}

# Prim String next to "Target Prim" in the header of a prim list
STYLE_PRIM_STRING = {"font_size": 14, "color": COLORS.WHITE}

# Property list view
STYLE_PROPERTY_LIST = {
    "color": COLORS.CLR_C,
    "background_color": COLORS.CLR_2,
}

# Individual prim card label
STYLE_PROPERTY_CARD = {
    "font_size": 14,
    "color": COLORS.CLR_C,
}

# Property card contents
STYLE_PROPERTY_CONTENTS = {
    "font_size": 14,
    "color": COLORS.CLR_C,
}

STYLE_PROPERTY_SELECTION_LIST = {
    "TreeView.HoveredIcon": {"background_color": 0xFFFF0000},
    "margin": 1,
}

STYLE_PROPERTY_SELECTION_CARD = {
    "font_size": 14,
    "margin": 1,
    "padding": 2,
    "color": COLORS.CLR_B,
}  # Property selection card in the window that opens when "Add Properties is clicked"

STYLE_ADD_BUTTON = {
    "color": COLORS.CLR_D,
    "background_color": DarkColors.Button,
    "border_radius": BUTTON_BORDER_RADIUS,
    ":hovered": {"color": COLORS.CLR_E, "background_color": COLORS.CLR_6},
    ":pressed": {"color": COLORS.CLR_E, "background_color": DarkColors.ButtonPressed},
}

STYLE_ICON_NO_HOVER = {
    "color": COLORS.CLR_D,
}

STYLE_EXPAND_BUTTON = {
    "color": COLORS.CLR_C,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_COLLAPSE}",
}

STYLE_COLLAPSE_BUTTON = {
    "color": COLORS.CLR_C,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_EXPAND}",
}

STYLE_REMOVE_BUTTON = {
    "color": COLORS.CLR_D,
    "background_color": COLORS.CLR_2,
    "border_radius": BUTTON_BORDER_RADIUS,
    "margin": 1,
    ":hovered": {"color": COLORS.CLR_E, "background_color": COLORS.CLR_6},
}

STYLE_ROUND_REMOVE_BUTTON = {
    "color": COLORS.CLR_6,
    "background_color": COLORS.TRANSPARENT,
    ":hovered": {"color": COLORS.CLR_RED},
}

STYLE_THUMBNAIL = {
    "color": COLORS.CLR_C,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_THUMBNAIL}",
}

STYLE_VERTICAL_LINES = {
    "color": COLORS.CLR_4,
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_VERT_LINES}",
}

STYLE_PROPERTY_LABEL = {"HighlightLabel::highlight": {"color": ui.color.shade("#DFCB4A")}}

STYLE_PROP_LOCAL_OPINION = {
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_VARIANT_LOCAL}",
    "color": COLORS.CLR_ORANGE,
    "background_color": COLORS.TRANSPARENT,
    ":hovered": {"color": COLORS.CLR_BRIGHT_ORANGE},
}

STYLE_PROP_LAYER_OPINION = {
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_VARIANT_INHERITED}",
    "color": COLORS.CLR_BLUE,
    "background_color": COLORS.TRANSPARENT,
    ":hovered": {"color": COLORS.CLR_BRIGHT_BLUE},
}

STYLE_PROP_VARIANT_OPINION = {
    "image_url": f"{PATH_EXTENSION}{PATH_ICON_VARIANT_VARIANT}",
    "color": COLORS.CLR_5,
    "background_color": COLORS.TRANSPARENT,
    ":hovered": {"color": COLORS.CLR_A},
}
