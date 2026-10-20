# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Optional

import carb
import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.browser.folder.core import BrowserFile

from .models import EnvBrowserModel, EnvDetailItem, EnvType
from .widgets import EnvDetailDelegate, EnvironmentBrowserWidget, EnvironmentOptionsMenu

SETTING_ROOT = "/exts/omni.kit.window.environment/"
SETTING_LOAD_AFTER_STARTUP = SETTING_ROOT + "load_after_startup"


class EnvironmentWindow(ui.Window):
    """
    Represent a window to show and edit environments.
    """

    WINDOW_TITLE = "Environments"

    def __init__(self, visible=True):
        super().__init__(self.WINDOW_TITLE, visible=visible)

        self._model = None
        self._widget = None

        self.frame.set_build_fn(self._build_ui)

        # Dock it to the same space where Stage is docked.
        self.deferred_dock_in("Content")

    def destroy(self) -> None:
        self.visible = False
        if self._widget is not None:
            self._widget.destroy()
            self._model.destroy()
            self._delegate.destroy()
        super().destroy()

    def navigate_to_dynamic_skies(self) -> None:
        if self._model is None:

            async def __delay_navigate():
                self.frame.call_build_fn()
                for i in range(2):
                    await omni.kit.app.get_app().next_update_async()

                self.__navigate_to_dynamic_skies()

            asyncio.ensure_future(__delay_navigate())
        else:
            self.__navigate_to_dynamic_skies()

    def __navigate_to_dynamic_skies(self) -> None:
        collection_items = self._model.get_item_children(None)
        category_items = self._model.get_item_children(collection_items[0])
        for category_item in category_items:
            if category_item.name_model.as_string.lower() in ["skies", "domelights"]:
                for child in category_item.children:
                    if child.name_model.as_string.lower() == "dynamic":
                        self._widget._browser_widget._category_view.set_expanded(category_item, True, True)
                        self._widget._browser_widget.category_selection = [child]
                        return
        else:
            carb.log_warn("Could not find dynamic skies!")

    def _build_ui(self):
        settings = carb.settings.get_settings()

        # Skies
        self._model = EnvBrowserModel()
        self._delegate = EnvDetailDelegate(self._model)

        self._options_menu = EnvironmentOptionsMenu(self._on_new_scene_template_saved)

        with self.frame:
            self._widget = EnvironmentBrowserWidget(
                model=self._model,
                delegate=self._delegate,
                options_menu=self._options_menu,
            )

        self.set_width_changed_fn(self._widget.on_window_width_changed)
        self.set_height_changed_fn(self._widget.on_window_height_changed)

    def _on_new_scene_template_saved(self, url: str) -> None:
        url = url.replace("\\", "/")

        for root_folder in self._model._root_folders:
            if url.startswith(root_folder.url):
                self._model.start_traverse(root_folder, force=True)
