from pathlib import Path

from omni import ui

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")


class FullSwitch:
    TriangleSize = 12
    TrianglePadding = 4
    LineWidth = 2
    LinePadding = 4


class Colors:
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Scrollbar = ui.color.shade(0xFF808080, light=0xFF9E9E9E)
    Selected = ui.color.shade(0xFFFFC734, light=0xFFC5911A)
    Text = ui.color.shade(0xFFA1A1A1, light=0xFFE0E0E0)
    DarkText = ui.color.shade(0xFF504F50, light=0xFFA1A1A1)
    Image = ui.color.shade(0xFF6F6F6F)
    Hover = ui.color.shade(0xFFF4F9FE)


UI_STYLES = {
    "PanelModeBar.Button": {"background_color": 0x0, "color": Colors.Text},
    "PanelModeBar.Button.Label": {"color": Colors.Text},
    "PanelModeBar.Button.Label:checked": {"color": Colors.Selected},
    "PanelModeBar.Separator": {"color": Colors.Text, "border_width": 2},
    "PanelModeBar.Triangle": {"border_width": 0, "background_color": Colors.Text},
    "PanelModeBar.Triangle:hovered": {"background_color": Colors.Hover},
    "PanelModeBar.Triangle:pressed": {"background_color": Colors.Hover},
    "FullSwitch.Triangle": {"background_color": 0xFFADA89D},
    "FullSwitch.Triangle::hovered": {"background_color": Colors.Hover},
    "FullSwitch.Line": {"color": Colors.Hover, "border_width": FullSwitch.LineWidth},
    "SingleMaterial.Frame": {"background_color": 0xFF000000},
    "SingleMaterial.Image": {},
    "SingleMaterial.Label": {"color": Colors.Text},
    "ToolBar.Button": {"background_color": 0x0, "padding": 3, "margin": 0},
    "ToolBar.Button:selected": {"background_color": Colors.Background},
    "Splitter": {"background_color": 0x0, "margin_width": 0},
    "Splitter:hovered": {"background_color": 0xFFB0703B},
    "Splitter:pressed": {"background_color": 0xFFB0703B},
    "Property.Path": {"background_color": Colors.Background},
    "Property.Path::mixed": {"color": 0xFFCC9E61},
    "Property.Frame": {"padding": 0},
    "EmptyNotification.Frame": {"background_color": Colors.Background},
    "EmptyNotification.Label": {"background_color": Colors.Background, "color": 0xFF7C7C7C, "font_size": 20},
    "EmptyNotification.Image": {"background_color": Colors.Background, "color": 0xFF7C7C7C},
}
