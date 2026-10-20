# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["AssetBrowserExtension"]

from typing import Optional

import carb.settings
import omni.ext
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.browser.folder.core import TreeFolderBrowserWidget

from .window import AssetBrowserWindow

_extension_instance = None
BROWSER_MENU_ROOT = "Window"
SETTING_ROOT = "/exts/omni.kit.browser.asset/"
SETTING_VISIBLE_AFTER_STARTUP = SETTING_ROOT + "visible_after_startup"


class AssetBrowserExtension(omni.ext.IExt):
    @property
    def window(self) -> Optional[AssetBrowserWindow]:
        return self._window

    @property
    def browser_widget(self) -> Optional[TreeFolderBrowserWidget]:
        return self._window._widget

    def on_startup(self, ext_id):
        self._window = None
        ui.Workspace.set_show_window_fn(
            AssetBrowserWindow.WINDOW_TITLE,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        visible = carb.settings.get_settings().get_as_bool(SETTING_VISIBLE_AFTER_STARTUP)
        if visible:
            self._show_window(True)
        else:
            # Warmup model
            warmup = carb.settings.get_settings().get("/app/warmupMode") or False
            if warmup:
                from .model import AssetBrowserModel

                self.__model = AssetBrowserModel(run_warmup=True)

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)

        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = AssetBrowserWindow(visible=True)
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
                        name="Assets", ticked=True, ticked_fn=self._is_visible, onclick_fn=self._toggle_window
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_entry, BROWSER_MENU_ROOT)

    def _is_visible(self):
        return self._window.visible if self._window else False

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items(BROWSER_MENU_ROOT)


def get_instance():
    return _extension_instance
