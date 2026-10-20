from omni import ui
from omni.ui import color as cl


class Colors:
    window = cl.shade(0xA0000000, light=0xA0000000)
    transparent = cl.shade(0x0, light=0x0)
    line = cl.shade(0xFF9E9E9E, light=0xFF9E9E9E)
    tooltip = cl.shade(0xFFA5C5CA, light=0xFFA5C5CA)
    shortcut = cl.shade(0xFF444444, light=0xFF444444)
    shortcut_white = cl.shade(0xFFCCCCCC, light=0xFFCCCCCC)


FONT_SIZE = 14

BOTTOMBAR_STYLE = {
    "MenuBar.Item.Background": {
        "background_color": 0x0,
        "border_radius": 2,
        "padding": 0,
        "margin": 0,
    }
}

TOOLTIP_STYLE = {
    "Triangle::tooltip": {
        "background_color": Colors.tooltip,
        "border_width": 0,
        "border_radius": 1,
        "margin": 0.0,
        "margin_height": 0,
        "margin_width": 0,
        "padding": 0,
    },
    "Rectangle::tooltip": {
        "background_color": Colors.tooltip,
        "border_width": 0,
        "border_radius": 2,
        "margin": 0.0,
        "margin_height": 0,
        "margin_width": 0,
        "padding": 0,
    },
    "Label::shortcut": {"color": Colors.shortcut, "font_size": FONT_SIZE},
    "Label::shortcut_white": {"color": Colors.shortcut_white, "font_size": FONT_SIZE},
    "Image::tooltip": {"margin": 0, "padding": 0},
    "Tooltip": {"background_color": Colors.transparent, "border_width": 0, "border_radius": 0},
}


WINDOW_STYLE = {
    "Window": {"background_color": Colors.window, "margin": 0.0, "margin_height": 0, "margin_width": 0, "padding": 0},
    "ImageButton": {"background_color": Colors.transparent, "border_width": 0, "border_radius": 2.0},
    "Line": {"color": Colors.line},
    "Rectangle::background": {"background_color": 0xA0000000, "border_width": 0},
    "Rectangle::background:hovered": {"background_color": 0xA0000000, "border_width": 1, "border_color": 0x30808080},
    "Rectangle::window_dimension": {"background_color": 0x00000000, "border_width": 0, "border_radius": 0},
    "Navigation.Button": {
        "color": 0x0,
        "background_color": 0,
        "padding": 0,
        "margin_width": 2,
        "margin_height": 2,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
}

BUTTON_RECT_STYLE = {
    "Rectangle::nv_button": {"background_color": 0x00000000, "border_width": 0},
    "Rectangle::nv_button:hovered": {
        "background_color": 0x40000000,
        "border_width": 1,
        "border_color": 0x30808080,
    },
    "Rectangle::nv_highlight": {"background_color": 0x00000000, "border_width": 0},
    "Rectangle::nv_highlight:checked": {
        "background_color": 0x00000000,
        "border_width": 3,
        "border_color": 0x00000000,
    },
}
