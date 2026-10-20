from omni import ui
from omni.kit.widgets.custom import FontSize
from omni.ui import color as cl


class Colors:
    cl.shade(0xFFC0C0C0, light=0xFFC0C0C0, name="startup_background")
    cl.shade(0xFFDADADA, light=0xFF454545, name="startup_titlebar_text")
    cl.shade(0xFF444444, light=0xFFE2E2E2, name="startup_titlebar")
    cl.shade(0xFF444444, light=0xFF444444, name="startup_button_label")
    cl.shade(0xFF444444, light=0xFF444444, name="startup_file_bt_select")
    cl.shade(0xFF444444, light=0xFF777777, name="startup_body")
    cl.shade(0xFF444444, light=0xFF777777, name="startup_tab_unselect")
    cl.shade(0xFFDADADA, light=0xFFE8E8E8, name="startup_label_recent")
    cl.shade(0xFF24211F, light=0xFF636363, name="startup_file_background")
    cl.shade(0x88C2C2C2, light=0x88C2C2C2, name="startup_file_hovered")


WELCOME_WINDOW_STYLE = {
    "Rectangle::titlebar": {"background_color": cl.startup_titlebar},
    "Rectangle::main_body": {"background_color": cl.startup_body},
    "ImageButton": {"background_color": cl.startup_titlebar},
    "ImageButton:hovered": {"background_color": cl.startup_background},
    "Label::titlebar_dark": {"color": cl.startup_titlebar_text, "font_size": FontSize.XXLarge},
    "Label::recent_tab": {
        "color": cl.startup_label_recent,
        "background_color": 0x000000,
        "font_size": FontSize.XXLarge,
    },
    "Label": {"font_size": FontSize.Large},
    "Rectangle::content_body": {"background_color": cl.startup_body},
    "Rectangle::content_files_area": {"background_color": cl.startup_file_background},
    "Rectangle::file_list": {"color": cl.startup_button_label, "background_color": cl.startup_file_background},
    "Rectangle::file_list:hovered": {"color": cl.startup_button_label, "background_color": cl.startup_file_hovered},
}

ACTION_BUTTON_STYLE = {
    "Button": {
        "stack_direction": ui.Direction.TOP_TO_BOTTOM,
        "background_color": cl.startup_tab_unselect,
        "padding": 0,
        "margin": 0,
        "border_width": 0,
    },
    "Button.Image": {
        "alignment": ui.Alignment.CENTER,
        "fill_policy": ui.FillPolicy.PRESERVE_ASPECT_FIT,
        "padding": 0,
        "margin": 0,
    },
}

ACTION_LABEL_STYLE = {
    "Label": {
        "color": 0xFFE2E2E2,
        "background_color": 0x000000,
        "alignment": ui.Alignment.CENTER,
        "font_size": FontSize.XXLarge,
        "padding": 0,
        "margin": 0,
    }
}

FILE_BUTTON_STYLE = {
    "Card.Image": {
        "alignment": ui.Alignment.CENTER,
        "fill_policy": ui.FillPolicy.PRESERVE_ASPECT_FIT,
        "padding": 0,
        "margin": 5,
    },
    "Card": {"background_color": 0x000000, "margin": 0},
    "Card:hovered": {"background_color": cl.startup_file_hovered, "border_width": 0},
    "Card:selected": {"background_color": cl.startup_file_bt_select},
}

FILE_BUTTON_LABEL_STYLE = {
    "alignment": ui.Alignment.CENTER,
    "font_size": FontSize.XXLarge,
    "padding": 0,
    "margin": 0,
}
