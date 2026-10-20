# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import pathlib

import omni.kit.app
import omni.ui as ui
from omni.kit.window.property.templates import LABEL_WIDTH
from omni.ui import color as cl
from omni.ui import url

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
ICON_SIZE = 18
PROPERTY_WIDGET_ALIGN_WIDTH = 13

# Pre-defined constants. It's possible to change them runtime.
cl.spawn_dark = cl("#262626")
cl.spawn_bg = cl("#383838")
cl.spawn_fg = cl("#646464")
cl.spawn_hovered = cl("#848484")
cl.spawn_icon = cl("#A8A8A8")
cl.spawn_changed_icon = cl("#4e7390")


url.resource_icon_add = "${glyphs}/menu_context.svg"
url.resource_icon_delete = "${glyphs}/trash.svg"
url.resource_icon_folder = "${glyphs}/folder.svg"
url.resource_icon_restore = "${glyphs}/thumbnail.svg"
url.spawn_icon_find = f"{EXTENSION_FOLDER_PATH}/data/icons/find.svg"
url.spawn_icon_changed = f"{EXTENSION_FOLDER_PATH}/data/icons/Changed value.svg"
url.spawn_icon_default = f"{EXTENSION_FOLDER_PATH}/data/icons/Default value.svg"

# The main style dict
spawn_property_style = {
    "CollapsableFrame::groupFrame": {"background_color": cl.spawn_dark, "secondary_color": cl.spawn_dark},
    "CollapsableFrame::subFrame": {"background_color": cl.spawn_bg, "secondary_color": cl.spawn_bg},
    "Button": {"margin_height": 0.5, "margin_width": 0.5, "background_color": cl.transparent},
    "Button:hovered": {"background_color": cl.spawn_hovered},
    "Button::string": {"background_color": cl.spawn_fg},
    "Button.Image::asset": {"image_url": url.resource_icon_folder, "color": cl.spawn_icon},
    "Button.Image::prim": {"image_url": url.resource_icon_restore, "color": cl.spawn_icon},
    "Button.Image::locate": {"image_url": url.spawn_icon_find, "color": cl.spawn_icon},
    "Button.Image::trash": {"image_url": url.resource_icon_delete, "color": cl.spawn_icon},
    "Button.Image::trash:disabled": {"color": cl.spawn_fg},
    "Label": {"font_size": 14, "color": cl.spawn_icon},
    "Image::default_value": {"image_url": url.spawn_icon_default, "background_color": cl.spawn_dark},
    "Image::changed_value": {"image_url": url.spawn_icon_changed, "background_color": cl.spawn_changed_icon},
}

# ui styles
w_drop_area_rect = {
    "border_radius": 5.0,
    "border_width": 2.0,
    "border_color": 0x33FFFFFF,
    "background_color": 0x0,
}

w_drop_area_label = {
    "color": 0x66FFFFFF,
}

w_drop_area = {
    "Rectangle": w_drop_area_rect,
    "Label": w_drop_area_label,
}

w_drop_area_highlight = {
    "Rectangle": w_drop_area_rect,
    "Label": w_drop_area_label,
    "background_color": 0xFFA07D4F,
    "color": 0xFFFFC77E,
}

w_clear_button = {"padding": 6}

w_vspacer_style = {"margin": 0, "padding": 0}

w_vstack_plain = {
    "margin": 0,
}

w_main_buttons = {"font_size": 16}

w_section_separator = {"color": 0x33FFFFFF}

w_section_title = {"font_size": 20, "alignment": ui.Alignment.LEFT_CENTER}

w_scrollingframe_border = {
    "margin": 0,
    "border_color": 0x33000000,
    "background_color": 0x0,
    "border_width": 1.5,
    "border_radius": 5,
}

w_scrollingframe_nosources = {"font_size": 12, "color": 0x66000000}

w_parameter_end_line = {"border_width": 1, "color": 0x22FFFFFF}

w_parameter_reset_button = {"border_radius": 1, "background_color": 0x44FFFFFF}

tooltip = {
    "color": 0xCC000000,
    "background_color": 0xFFAADDDD,
    "border_width": 0,
    "margin": -1,
    "border_width": 0,
    "padding": 0,
}

tooltip_text = {"margin": 6, "padding": 0, "font_size": 14}

button_reset_off = {"background_color": 0x33FFFFFF}
button_reset_on = {"background_color": 0xFFA07D4F, "border_radius": 2, "color": 0xFFFFFFFF}
