from pathlib import Path

from omni import ui  # type: ignore
from omni.kit.usd_explorer.tooltip import set_usd_explorer_tooltip
from omni.kit.widgets.custom import COLORS, DarkColors, MouseKey  # , LightColors, FontSize
from ui import color  # type: ignore

MENUBAR_HEIGHT = 24
CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")


class LabelButton:
    txt_color = color.shade(DarkColors.Text, light=DarkColors.TextDisabled)
    STYLE = {
        "Rectangle::label_button": {
            "background_color": COLORS.TRANSPARENT,
            "border_width": 1,
            "border_color": COLORS.TRANSPARENT,
            "border_radius": 3.0,
        },
        "Rectangle::label_button:hovered": {
            "background_color": COLORS.TRANSPARENT,
            "border_width": 1,
            "border_color": COLORS.TEXT_SELECTED,
            "border_radius": 3.0,
        },
        "Label::label_button": {"color": txt_color, "background_color": COLORS.TRANSPARENT},
        "Label::label_button:selected": {"color": COLORS.TEXT_SELECTED},
    }

    def __init__(self, name, text, width, height, on_clicked_fn: callable = None, tooltip=None):
        self._on_clicked_fn = on_clicked_fn
        self._id = name
        self._selected = False
        with ui.ZStack(width=0, height=0, spacing=0, style=self.STYLE):
            with ui.Placer(offset_x=0, offset_y=0):
                self._rect = ui.Rectangle(name="label_button", width=width, height=height)
            with ui.Placer(offset_x=0, offset_y=0):
                self._label = ui.Label(
                    text, name="label_button", width=width, height=height, alignment=ui.Alignment.CENTER
                )
            self._rect.set_mouse_pressed_fn(lambda x, y, btn, a: self._on_mouse_pressed())
            if tooltip:
                set_usd_explorer_tooltip(self._rect, tooltip)

    def set_mouse_pressed_fn(self, on_clicked_fn: callable):
        self._on_clicked_fn = on_clicked_fn

    def _on_mouse_pressed(self):
        if self._on_clicked_fn:
            self._on_clicked_fn(self._id)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        self._label.selected = value


class ImageButton:
    STYLE = {
        "Rectangle::image_button": {"background_color": COLORS.TRANSPARENT, "border_width": 0, "border_radius": 2.0},
        "Rectangle::image_button:hovered": {"background_color": COLORS.CLR_A, "border_width": 0, "border_radius": 2.0},
        "Rectangle::image_button:selected": {
            "background_color": COLORS.TRANSPARENT,
            "border_width": 1,
            "border_color": COLORS.TEXT_SELECTED,
            "border_radius": 2.0,
        },
    }

    def __init__(self, name, image, width, height, on_clicked_fn: callable = None, tooltip=None):
        self._on_clicked_fn = on_clicked_fn
        self._id = name
        self._selected = False
        with ui.ZStack(width=0, height=0, spacing=0, style=self.STYLE):
            with ui.Placer(offset_x=0, offset_y=0):
                self._rect = ui.Rectangle(name="image_button", width=width, height=height)
            with ui.Placer(offset_x=1, offset_y=1):
                ui.Image(
                    image, name="image_button", width=width - 2, height=height - 2, fill_policy=ui.FillPolicy.STRETCH
                )
            self._rect.set_mouse_pressed_fn(lambda x, y, btn, a: self._on_mouse_pressed(btn))
            if tooltip:
                set_usd_explorer_tooltip(self._rect, tooltip)

    def set_mouse_pressed_fn(self, on_clicked_fn: callable):
        self._on_clicked_fn = on_clicked_fn

    def _on_mouse_pressed(self, key):
        if key == MouseKey.LEFT and self._on_clicked_fn:
            self._on_clicked_fn(self._id)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        self._rect.selected = value


class TabedGroup:
    def __init__(self):
        self._selected = None
        self._list = {}

    def add_child(self, name, child, selected=False):
        self._list[name] = child
        if selected:
            self.select(name)
        else:
            child.selected = False

    def select(self, name):
        if self._selected:
            self._list[self._selected].selected = False
            self._selected = None
        if name and name in self._list:
            self._list[name].selected = True
            self._selected = name

    def get_selected(self):
        return self._selected


class ThickSeparator:
    STYLE = {"Line::separator": {"color": COLORS.LINE_SEPARATOR_THICK, "border_width": 1}}

    def __init__(self):
        with ui.VStack(width=0, height=24, style=self.STYLE):
            ui.Spacer(height=7)
            ui.Line(name="separator", width=1, height=12, alignment=ui.Alignment.LEFT)
            ui.Spacer()
