# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import List, Optional

import carb.settings
import omni.ext
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.browser.core import TreeBrowserWidget

from .actions import deregister_actions, register_actions
from .browser_model import SimReadyBrowserModel
from .empty_property_delegate import EmptyPropertyDelegate
from .multi_property_delegate import MultiPropertyDelegate
from .prop_property_delegate import PropAssetPropertyDelegate
from .window import SIMREADY_EXPLORER_NAME, SimReadyBrowserWindow

BROWSER_MENU_ROOT = "Window"
SETTINGS_ROOT = "/exts/omni.simready.explorer/"
SETTIGNS_VISIBLE = SETTINGS_ROOT + "visible_after_startup"
_extension_instance = None


class SimReadyBrowserExtension(omni.ext.IExt):
    @property
    def window(self) -> Optional[SimReadyBrowserWindow]:
        return self._window

    @property
    def browser_widget(self) -> Optional[TreeBrowserWidget]:
        if self._window is None:
            return None
        return self._window._widget

    @property
    def browser_model(self) -> Optional[SimReadyBrowserModel]:
        if self._window is None:
            return None
        return self._window._browser_model

    def on_startup(self, ext_id):
        try:
            self.__ext_id = omni.ext.get_extension_name(ext_id)
        except AttributeError:

            def get_extension_name(ext_id: str) -> str:
                """Convert 'omni.foo-tag-1.2.3' to 'omni.foo-tag'"""
                a, b, *_ = ext_id.split("-") + [""]
                if b and not b[0:1].isdigit():
                    return f"{a}-{b}"
                return a

            self.__ext_id = get_extension_name(ext_id)
        register_actions(self.__ext_id, self)

        self._window = None
        ui.Workspace.set_show_window_fn(
            SIMREADY_EXPLORER_NAME,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        visible = carb.settings.get_settings().get_as_bool(SETTIGNS_VISIBLE)
        if visible:
            self._show_window(True)

        # Instantiate the property delegates so they get registered with class BrowserPropertyDelegate
        self.__empty_property_delegate = EmptyPropertyDelegate()
        self.__propasset_property_delegate = PropAssetPropertyDelegate()
        self.__multi_property_delegate = MultiPropertyDelegate()

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)
        if self._window is not None:
            self._window.destroy()
            self._window = None

        self.__empty_property_delegate = None
        self.__propasset_property_delegate = None
        deregister_actions(self.__ext_id)

        global _extension_instance
        _extension_instance = None

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = SimReadyBrowserWindow(visible=True)
                self._window.set_visibility_changed_fn(self._on_visibility_changed)
            else:
                self._window.visible = True
        else:
            self._window.visible = False

    def _toggle_window(self):
        self._show_window(not self._is_visible())

    def _register_menuitem(self):
        self._menu_entry = [
            omni.kit.menu.utils.MenuItemDescription(
                name="Browsers",
                sub_menu=[
                    omni.kit.menu.utils.MenuItemDescription(
                        name=SIMREADY_EXPLORER_NAME,
                        ticked=True,
                        ticked_fn=self._is_visible,
                        onclick_action=(self.__ext_id, "toggle_window"),
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_entry, BROWSER_MENU_ROOT)

    def _is_visible(self):
        return self._window.visible if self._window else False

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items(BROWSER_MENU_ROOT)


def get_instance() -> Optional[SimReadyBrowserExtension]:
    return _extension_instance
