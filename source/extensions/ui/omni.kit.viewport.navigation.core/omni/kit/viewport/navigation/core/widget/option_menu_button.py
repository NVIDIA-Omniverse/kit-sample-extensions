from enum import IntEnum
from functools import partial
from typing import Dict, Optional

import carb
import carb.input
import carb.settings
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportMenuDelegate

from ..constant import NAVIGATION_IS_LARGE, NAVIGATION_LARGE_SIZE, NAVIGATION_SMALL_SIZE
from ..delegate import NavigationIconMenuDelegate
from ..navigation_tooltip import ViewportNavigationTooltip
from ..style import TOOLTIP_STYLE
from .navigation_button import ViewportNavigationButton


class ViewportNavigationOptionMenuButton(ViewportNavigationButton):
    """
    Build a button in navigation menubar:
    """

    def __init__(
        self,
        name,
        image,
        size,
        visible_setting_path: Optional[str] = None,
        order_setting_path: Optional[str] = None,
        state=True,
        show_tip_fn=None,
        size_change_fn=None,
        direction_change_fn=None,
        auto_spin=True,
        build_tooltip_fn=lambda: (0, 0),
        show_label=True,
        direction=ui.Direction.LEFT_TO_RIGHT,
    ):

        self._size_change = size_change_fn
        self._direction_change = direction_change_fn
        self._show_tip = show_tip_fn
        self._direction = direction
        self._true_image = image
        super().__init__(
            name,
            size,
            visible_setting_path,
            order_setting_path,
            state,
            show_tip_fn,
            auto_spin,
            build_tooltip_fn,
            show_label,
        )

    def get_style(self):
        style = {
            "Menu.Item.Icon::Navigation": {"image_url": f"{self._true_image}", "background_color": 0x0},
            "Menu.Item.Background": {
                "background_color": 0x0,
                "border_radius": 6,
                "padding": 1,
                "margin": 2,
            },
            "Menubar.Hover": {
                "background_color": 0,
                "border_radius": 6,
                "padding": 1,
                "margin": 2,
            },
            "Menubar.Hover:hovered": {"background_color": 0x0, "border_width": 1.5},
            "Menubar.Hover:pressed": {"background_color": 0x0, "border_width": 1.5},
            "Menu.Window": {
                "background_color": 0xA0000000,
                "border_width": 0,
                "border_radius": 0,
                "background_selected_color": 0x0,
                "secondary_padding": 1,
                "secondary_selected_color": 0x0,
                "margin": 2,
            },
        }
        return style

    def build_fn(self, factory: Dict):
        self._is_large = carb.settings.get_settings().get(NAVIGATION_IS_LARGE)
        if self._is_large:
            self._size = carb.settings.get_settings().get(NAVIGATION_LARGE_SIZE)
        else:
            self._size = carb.settings.get_settings().get(NAVIGATION_SMALL_SIZE)
        self._delegate = NavigationIconMenuDelegate("Navigation", width=self._size, height=self._size)
        with ui.VStack():
            self._menu = ui.Menu(
                "Navigation",
                name=self._name,
                delegate=self._delegate,
                menu_compatibility=False,
                style=self.get_style(),
                on_build_fn=self._build_menu_items,
                tearable=True,
                direction=ui.Direction.TOP_TO_BOTTOM,
            )
            ui.Spacer(height=0)
            if self._is_large:
                ui.Label("Option")

    def _change_to_horizontal(self):
        if self._direction_change:
            self._direction_change(ui.Direction.LEFT_TO_RIGHT)
            self._direction = ui.Direction.LEFT_TO_RIGHT

    def _change_to_vertical(self):
        if self._direction_change:
            self._direction_change(ui.Direction.TOP_TO_BOTTOM)
            self._direction = ui.Direction.TOP_TO_BOTTOM

    def _build_menu_items(self):
        # add a Rect to make the top bar of menu full fill
        ui.Rectangle(name="background", width=60)
        with ui.MenuItemCollection():
            ui.MenuItem(
                "Small",
                checkable=True,
                enabled=True,
                checked=not self._is_large,
                delegate=ViewportMenuDelegate(),
                hide_on_click=True,
                triggered_fn=partial(self._size_change, False),
            )
            ui.MenuItem(
                "Large",
                checkable=True,
                enabled=True,
                checked=self._is_large,
                delegate=ViewportMenuDelegate(),
                hide_on_click=True,
                triggered_fn=partial(self._size_change, True),
            )
        ui.Separator()
        with ui.MenuItemCollection():
            ui.MenuItem(
                "Horizontal",
                checkable=True,
                checked=(self._direction == ui.Direction.LEFT_TO_RIGHT),
                enabled=True,
                delegate=ViewportMenuDelegate(),
                hide_on_click=True,
                triggered_fn=self._change_to_horizontal,
            )
            ui.MenuItem(
                "Vertical",
                checkable=True,
                checked=(self._direction != ui.Direction.LEFT_TO_RIGHT),
                enabled=True,
                delegate=ViewportMenuDelegate(),
                hide_on_click=True,
                triggered_fn=self._change_to_vertical,
            )
        ui.Separator()
        ui.MenuItem(
            "ShowTips",
            checkable=True,
            enabled=True,
            # checked=ViewportNavigationTooltip.show_tooltip(),
            delegate=ViewportMenuDelegate(),
            hide_on_click=True,
            triggered_fn=self._show_tip,
        )
