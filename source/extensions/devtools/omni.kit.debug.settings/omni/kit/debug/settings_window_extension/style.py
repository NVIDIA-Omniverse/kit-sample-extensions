from omni import ui
from omni.ui import color as cl


class Colors:
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Scrollbar = ui.color.shade(0xFF808080, light=0xFF9E9E9E)
    Selected = ui.color.shade(0xFFFFC734, light=0xFFC5911A)
    Text = ui.color.shade(0xFFA1A1A1, light=0xFFE0E0E0)
    DarkText = ui.color.shade(0xFF504F50, light=0xFFA1A1A1)
    Image = ui.color.shade(0xFFA8A8A8)
    Branch = ui.color.shade(cl(0.36, 0.36, 0.36, 1.0))
    Expand = ui.color.shade(cl(0.65, 0.65, 0.65, 1.0))


UI_STYLE = {
    "Button.Image::refresh": {"image_url": "${glyphs}/menu_refresh.svg"},
    "TreeView.Frame": {
        "background_color": Colors.Background,
        "secondary_color": Colors.Scrollbar,
        "border_radius": 0,
        "scrollbar_size": 10,
    },
    # + and - signs
    "TreeView.Branch.Line": {
        "color": Colors.Branch,
        "background_color": Colors.Branch,
        "margin": 0,
    },
    "TreeView.Item": {
        "color": Colors.Expand,
        "border_width": 1.5,
        "border_color": Colors.Expand,
    },
    "TreeView.Item:selected": {"color": Colors.Expand},
}
