# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref
from functools import partial

import omni.ui
from omni.ui import color as cl
from omni.ui import constant as fl

from ..delegate import ToolBarIconMenuDelegate

try:  # pragma: no cover
    from omni.kit.widget.toolbar.hotkey import Hotkey
    from omni.kit.widget.toolbar.widget_group import WidgetGroup

    class ToolbarMenuButton(WidgetGroup):
        """
        A helper class to create simple WidgetGroup that contains only one ToolButton.

        Args:
            name: Name of the ToolButton.
            tooltip: Tooltip of the ToolButton.
            icon_path: The icon to be used when button is not checked.
            icon_checked_path: The icon to be used when button is checked.
            hotkey: HotKey to toggle the button (optional).
            toggled_fn: Callback function when button is toggled. Signature: on_toggled(checked) (optional).
            model: Model for the ToolButton (optional).
            additional_style: Additional styling to apply to the ToolButton (optional).
        """

        def __init__(
            self,
            name,
            tooltip,
            icon_path,
            icon_checked_path,
            build_menu_fn=None,
            hotkey=None,
            toggled_fn=None,
            model=None,
            additional_style=None,
        ):
            super().__init__()
            self._name = name
            self._delegate = ToolBarIconMenuDelegate("ToolBar")
            self._tooltip = tooltip
            self._icon_path = icon_path
            self._icon_checked_path = icon_checked_path
            self._hotkey = hotkey
            self._toggled_fn = toggled_fn
            self._model = model
            self._build_menu = build_menu_fn
            self._additional_style = additional_style
            self._hotkey = None
            self._width = 50

            if hotkey:
                self._select_hotkey = Hotkey(
                    f"{name}::hotkey",
                    hotkey,
                    lambda: self._on_hotkey(),
                    lambda: self._menu_button.enabled and self._is_in_context(),
                )

        def clean(self):
            super().clean()
            self._value_sub = None
            self._menu_button = None
            if self._select_hotkey:
                self._select_hotkey.clean()
                self._select_hotkey = None

        def get_style(self):
            style = {
                "Menu.Item.Icon::ToolBar": {"image_url": f"{self._icon_path}", "background_color": 0x0},
                "MenuBar.Item.Background": {
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
                "Menubar.Hover:hovered": {"background_color": 0xFF383838, "border_width": 1.5},
                "Menubar.Hover:pressed": {"background_color": 0xFF4B4B4B, "border_width": 1.5},
                "Menu.Window": {
                    "background_color": 0xA0000000,
                },
            }
            if self._additional_style:
                style.update(self._additional_style)

            return style

        def create(self, default_size):
            self._menu = omni.ui.Menu(
                "ToolBar",
                style=self.get_style(),
                delegate=self._delegate,
                on_build_fn=self._build_menu_fn,
                menu_compatibility=False,
                tearable=True,
                direction=omni.ui.Direction.TOP_TO_BOTTOM,
            )
            return {self._name: self._menu}

        def _build_menu_fn(self):
            # add a Rect to make the top bar of menu full fill
            omni.ui.Rectangle(name="background", width=self._width)
            self._build_menu()

        def set_title_visible(self, visible):
            self._menu.tearable = visible

        def invalidate(self, width):
            self._width = width
            self._menu.invalidate()

        def get_tool_button(self):
            return self._menu

        def _on_hotkey(self):
            self._menu_button.model.set_value(not self._menu_button.model.get_value_as_bool())

except:

    class ToolbarMenuButton:
        def __init__(self):
            pass
