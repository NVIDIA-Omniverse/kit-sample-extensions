import carb.tokens
from omni import ui
from omni.kit.markup.core import MARKUP_BROWSER_WIDGET_STYLES
from omni.ui import color as cl


class Colors:
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)


ICON_PATH = carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.markup}/data/icons")

LIST_WINDOW_STYLES = {
    "Window": {"background_color": Colors.Background, "padding": 0, "margin": 0},
    "Button": {"background_color": Colors.Background},
    "Separator": {"color": 0xFF535354, "border_width": 2},
    "Warning": {"background_color": Colors.Background, "color": 0xFF7C7C7C, "font_size": 20},
    "GridView.Image:selected": {"border_width": 0, "border_color": 0, "border_radius": 3.0},
    "Button.Close": {
        "stack_direction": ui.Direction.BACK_TO_FRONT,
        "background_color": cl.transparent,
        "border_width": 1,
        "border_radius": 2,
        "border_color": cl.transparent,
    },
    "Button.Close:hovered": {"border_color": 0xFF535354},
    "Button.Close.Image": {"image_url": f"{ICON_PATH}/close.svg"},
}

POSITIONER_STYLE = {"Rectangle": {"background_color": 0, "border_width": 0}}

EDIT_WINDOW_STYLES = {
    "Window": {"background_color": Colors.Background, "padding": 0, "margin": 0},
    **MARKUP_BROWSER_WIDGET_STYLES,
}
# Hard coding the upper left corner where we'd like the window to appear
# this decision is in flux, so minimum effort was expended. -Bob
# Totally subject to change - per Brian.
UPPER_LEFT_OFFSET = (60, 62)
