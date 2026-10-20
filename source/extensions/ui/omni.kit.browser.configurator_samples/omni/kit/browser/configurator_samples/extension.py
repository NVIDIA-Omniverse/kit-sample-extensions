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

from .model import ConfiguratorSamplesBrowserModel
from .window import ConfiguratorSamplesBrowserWindow

BROWSER_MENU_ROOT = "Window"
FOLDERS_SETTING_NAME = "exts/omni.kit.browser.configurator_samples/folders"
CUSTOM_FOLDERS_SETTING_NAME = "/exts/omni.kit.browser.configurator_samples/custom_folders"
_extension_instance = None


class SampleBrowserExtension(omni.ext.IExt):
    """Browser Extension that can take paths from multiple extensions and use them together in one viewer."""

    def on_startup(self, ext_id):
        """Run once on startup of the extension.

        Initializes settings, creates the model, registers the UI window callback, and sets the global extension instance.

        Args:
            ext_id (str): Extension identifier.
        """
        self._settings = carb.settings.get_settings()
        self._model = ConfiguratorSamplesBrowserModel(
            custom_folders_setting=CUSTOM_FOLDERS_SETTING_NAME,
            run_warmup=self._settings.get("/app/warmupMode") or False,
        )

        self._window = None
        ui.Workspace.set_show_window_fn(
            ConfiguratorSamplesBrowserWindow.WINDOW_TITLE,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        global _extension_instance
        _extension_instance = self

        # load sample folders from setting
        # self._sample_folders = self._settings.get(FOLDERS_SETTING_NAME)

        # for folder in self._sample_folders:
        #    omni.kit.browser.configurator_samples.register_sample_folder(folder)  # Name is before the url with "::" separating them

    def on_shutdown(self):
        """Run once as the extension shuts down."""
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)

        # It's important that this all happens *after* all of the child exts unregister their folders.
        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    def get_model(self):
        """Get the model for the extension.

        Returns:
            ConfiguratorSamplesBrowserModel: The model managing sample browser data.
        """
        return self._model

    def get_window(self):
        """Get the window object for the extension.

        Returns:
            ConfiguratorSamplesBrowserWindow: The window instance if created; otherwise, None.
        """
        return self._window

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = ConfiguratorSamplesBrowserWindow(self._model)
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
                        name=ConfiguratorSamplesBrowserWindow.WINDOW_TITLE,
                        ticked=True,
                        ticked_fn=self._is_visible,
                        onclick_fn=self._toggle_window,
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
    """Get singleton instance of SampleBrowserExtension.

    Returns:
        SampleBrowserExtension: The singleton instance of SampleBrowserExtension.
    """
    return _extension_instance


def register_sample_folder(url: str, name: Optional[str] = None):
    """Register a folder with the Samples Browser.

    Args:
        url (str): Path for the Collection.
        name (Optional[str]): Name of the Collection; if None, uses the final folder name as the collection name.
    """
    get_instance().get_model().register_configurator_samples_folder(url, name)


def unregister_sample_folder(url: str):
    """Unregister a folder with the Samples Browser.

    Args:
        url (str): Path for the Collection.
    """
    get_instance().get_model().unregister_configurator_samples_folder(url)
