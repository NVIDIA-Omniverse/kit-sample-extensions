from typing import List, Optional

from omni import ui

from ..models import StageMaterialModel


class PanelModes:
    LIBRARY = "Library"
    CURRENT_SCENE = "Current Stage"
    SELECTED = "Selected"


PANEL_MODES = [PanelModes.LIBRARY, PanelModes.CURRENT_SCENE, PanelModes.SELECTED]


class SelectedPanelMenu:
    """
    Represent the menu for selected mode.
    """

    def __init__(self, model: StageMaterialModel):
        self._model = model
        self._menu: Optional[ui.Menu] = None

    def destroy(self) -> None:
        self._menu = None

    def show(self) -> None:
        """
        Show menu.
        """
        if self._menu is None:
            self._menu = ui.Menu("Selected Panel Menu")
            with self._menu:
                ui.MenuItem(
                    "Include Children",
                    checkable=True,
                    checked=self._model.selection_include_children,
                    triggered_fn=self._on_triggered,
                )

        self._menu.show()

    def _on_triggered(self) -> None:
        self._model.selection_include_children = not self._model.selection_include_children


class PanelModeBar:
    """
    Represent a bar to swith different panel mode.
    Keyword args:
        modes (Optional[List[str]]): Panel modes string. None meanshide this bar.
        on_mode_changed_fn (callable): Function called when panel mode changed. Function signure:
            void on_mode_changed_fn(mode: str)
    """

    def __init__(self, model: StageMaterialModel, on_mode_changed_fn: callable = None):
        self._modes = PANEL_MODES
        self._mode_menus = [None, None, SelectedPanelMenu(model)]
        self._on_mode_changed_fn = on_mode_changed_fn
        self.widget: Optional[ui.HStack] = None

        if self._modes:
            self._build_ui()

    @property
    def width(self) -> float:
        return self.widget.computed_content_width if self.widget else 0

    @property
    def position_x(self) -> float:
        return self.widget.screen_position_x if self.widget else 0

    def _build_ui(self):
        collection = ui.RadioCollection()
        self.widget = ui.HStack(width=0, height=26)
        with self.widget:
            ui.Spacer()
            for index, mode in enumerate(self._modes):
                with ui.ZStack(width=30):
                    ui.RadioButton(
                        text=mode, radio_collection=collection, style_type_name_override="PanelModeBar.Button"
                    )
                    if self._mode_menus[index]:
                        with ui.HStack():
                            ui.Spacer()
                            with ui.VStack(width=0):
                                ui.Spacer()
                                self._tri = ui.Triangle(
                                    width=8,
                                    height=8,
                                    mouse_pressed_fn=lambda x, y, a, f, m=self._mode_menus[index]: m.show(),
                                    alignment=ui.Alignment.RIGHT_TOP,
                                    style_type_name_override="PanelModeBar.Triangle",
                                )
                                ui.Spacer(height=4)
                if index < len(self._modes) - 1:
                    with ui.VStack(width=1):
                        ui.Spacer()
                        ui.Line(
                            height=10, alignment=ui.Alignment.LEFT, style_type_name_override="PanelModeBar.Separator"
                        )
                        ui.Spacer()
            ui.Spacer()

        collection.model.add_value_changed_fn(self._on_mode_changed)

    def _on_mode_changed(self, model: ui.AbstractValueModel):
        if self._on_mode_changed_fn is not None:
            self._on_mode_changed_fn(self._modes[model.as_int])
