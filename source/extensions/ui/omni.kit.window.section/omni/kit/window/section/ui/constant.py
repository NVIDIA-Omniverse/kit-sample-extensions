from pathlib import Path

from omni import ui
from omni.kit.widgets.custom import LightColors

from ..common import get_data_path

# UI layouts
CONTROL_HEIGHT = 24
SWITCH_HEIGHT = 28
SWITCH_WIDTH = 28
SPINNER_WIDTH = 150
PANEL_PADDING_X = 0
PANEL_SPACING_Y = 10
PANEL_PADDING_INNER_X = 40
ICON_SIZE = 40


class Colors:
    ButtonBackground = ui.color.shade(0xFF23211F, light=LightColors.Button)
    ButtonPressed = ui.color.shade(0xFF787569, light=0xFFA8A8A8)


CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data/icons")

UI_STYLE = {
    "Label": {"color": 0xFF9E9E9E},
    "Label::label": {"color": 0xFF9E9E9E},
    "Button": {"background_color": 0, "padding": 0},
    "Button:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Image::add": {"image_url": get_data_path("icons/Add.svg"), "color": 0xFFD9A223},
    "Button.Image::save": {"image_url": get_data_path("icons/save.svg")},
    "Button.Image::save_dirty": {"image_url": get_data_path("icons/save_dirty.svg")},
    "Button.Image::option": {"image_url": get_data_path("icons/settings.svg")},
    "Button::align_x": {"background_color": Colors.ButtonBackground},
    "Button::align_x:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Label::align_x": {"color": 0xFF6F6FB0},
    "Button::align_y": {"background_color": Colors.ButtonBackground},
    "Button::align_y:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Label::align_y": {"color": 0xFF8FB08B},
    "Button::align_z": {"background_color": Colors.ButtonBackground},
    "Button::align_z:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Label::align_z": {"color": 0xFFB49F82},
    "Button::counter_clockwise": {"background_color": Colors.ButtonBackground, "padding": 0},
    "Button::counter_clockwise:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Image::counter_clockwise": {
        "image_url": get_data_path("icons/Rotate_Counter_Clockwise.svg"),
        "color": 0xFFD6D6D6,
    },
    "Button::clockwise": {"background_color": Colors.ButtonBackground, "padding": 0},
    "Button.Image::clockwise": {"image_url": get_data_path("icons/Rotate_Clockwise.svg"), "color": 0xFFD6D6D6},
    "Button::clockwise:pressed": {"background_color": Colors.ButtonPressed},
    "Button::control": {"background_color": Colors.ButtonBackground},
    "Button::control:pressed": {"background_color": Colors.ButtonPressed},
    "Button.Label::control": {
        "color": 0xFF9E9E9E,
    },
    "Button.Label::control:hovered": {
        "color": 0xFFD6D6D6,
    },
    "Switch": {"image_url": f"{ICON_PATH}/switch_off_dark.svg"},
    "Switch:checked": {"image_url": f"{ICON_PATH}/switch_on_dark.svg"},
}
