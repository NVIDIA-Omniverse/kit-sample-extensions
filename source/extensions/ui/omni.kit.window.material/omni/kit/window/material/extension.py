# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

import carb
import omni.ext
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.browser.core import OptionsMenu

from .window import SETTING_ROOT, MaterialWindow

_extension_instance = None
BROWSER_MENU_ROOT = "Window"
SETTING_VISIBLE_AFTER_STARTUP = SETTING_ROOT + "visible_after_startup"


class MaterialBrowserExtension(omni.ext.IExt):
    """A class for providing an interactive material browser window interface in Omniverse applications.

    This extension integrates a material browser window with menu actions that allow toggling its visibility directly from the user interface. It registers a menu item under the designated browser menu root, facilitating easy access to material browsing features. The extension offers properties to retrieve the library and stage options menus, which enable users to manage material libraries and stage-related material settings.

    Properties:
        library_options_menu (Optional[OptionsMenu]): Retrieves the options menu for managing material libraries if available.
        stage_options_menu (Optional[OptionsMenu]): Retrieves the options menu for managing stage-related materials if available.
    """

    def on_startup(self, ext_id):
        """Initializes the material browser extension and configures the window.

        Sets the window show function and registers menu items. Reads the setting for window visibility and displays the window if True. Stores the extension instance in a global variable.

        Args:
            ext_id (str): Identifier for the extension.
        """
        self._window = None
        ui.Workspace.set_show_window_fn(
            MaterialWindow.WINDOW_TITLE,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        visible = carb.settings.get_settings().get_as_bool(SETTING_VISIBLE_AFTER_STARTUP)
        if visible:
            self._show_window(True)

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        """Performs cleanup for the material browser extension.

        Deregisters all associated actions, removes menu items, destroys the window if present, and resets the global extension instance.
        """
        # unregister actions
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension("omni.kit.window.material")

        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)

        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    @property
    def library_options_menu(self) -> Optional[OptionsMenu]:
        """Gets the library options menu widget.

        Returns:
            Optional[OptionsMenu]: Instance of the library OptionsMenu if available; otherwise None.
        """
        return self._window._widget.library_options_menu if self._window and self._window._widget else None

    @property
    def stage_options_menu(self) -> Optional[OptionsMenu]:
        """Gets the stage options menu widget.

        Returns:
            Optional[OptionsMenu]: Instance of the stage OptionsMenu if available; otherwise None.
        """
        return self._window._widget.stage_options_menu if self._window and self._window._widget else None

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = MaterialWindow(visible=True)
                self._window.set_visibility_changed_fn(self._on_visibility_changed)
            else:
                self._window.visible = True
        else:
            self._window.visible = False

    def _toggle_window(self):
        self._show_window(not self._is_visible())

    def _register_menuitem(self):
        # register actions
        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Window Material Actions"

        # actions
        action_registry.register_action(
            "omni.kit.window.material",
            "toggle_window",
            self._toggle_window,
            display_name="toggle_window",
            description="toggle_window",
            tag=actions_tag,
        )

        self._menu_entry = [
            omni.kit.menu.utils.MenuItemDescription(
                name="Browsers",
                sub_menu=[
                    omni.kit.menu.utils.MenuItemDescription(
                        name=MaterialWindow.WINDOW_TITLE,
                        ticked=True,
                        ticked_fn=self._is_visible,
                        onclick_action=("omni.kit.window.material", "toggle_window"),
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
    """Return the current instance of the omni.kit.window.material extension.

    Returns:
        MaterialBrowserExtension: The current extension instance or None if the extension is not initialized.
    """
    return _extension_instance
