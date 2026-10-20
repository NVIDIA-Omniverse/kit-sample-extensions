from pathlib import Path

from omni.ui import color as cl
from omni.ui import constant as fl

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("icons")

UI_STYLE = {
    "Menu.Item.Icon::Screenshot": {"image_url": f"{ICON_PATH}/screenshot_viewport.svg"},
    "Menu.Button.Image::Screenshot": {"image_url": f"{ICON_PATH}/screenshot_viewport.svg"},
}

MENU_ITEM_STYLE = {
    "MenuItem": {
        "background_selected_color": cl.viewport_menubar_selection,
        "secondary_padding": 1,
        "secondary_selected_color": cl.viewport_menubar_selection_border,
    },
    "MenuBar.Item": {
        "color": cl.viewport_menubar_light,
        "padding": 0,
        "margin_width": fl.viewport_menubar_item_margin,
        "margin_height": fl.viewport_menubar_item_margin,
    },
    "MenuBar.Item::menubar": {
        "color": cl.viewport_menubar_light,
        "padding": 0,
        "margin_width": 0,
        "margin_height": 0,
    },
    "MenuBar.Item.Background": {
        "background_color": cl.viewport_menubar_background,
        "border_radius": 6,
        "padding": 1,
        "margin": 2,
    },
    "Menubar.Hover": {
        "background_color": 0,
        "padding": 1,
        "margin": 1,
    },
    "Menubar.Hover:hovered": {
        "background_color": cl.viewport_menubar_selection,
        "border_color": cl.viewport_menubar_selection_border_button,
        "border_width": 1.5,
    },
    "Menubar.Hover:pressed": {
        "background_color": cl.viewport_menubar_selection,
        "border_color": cl.viewport_menubar_selection_border_button,
        "border_width": 1.5,
    },
}
