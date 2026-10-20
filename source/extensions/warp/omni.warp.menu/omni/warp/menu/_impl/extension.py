# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Entry point for the extension."""

import webbrowser
from contextlib import suppress

import carb
import omni.ext
import omni.kit.actions.core
import omni.kit.app

APP = omni.kit.app.get_app()
EXT_MANAGER = APP.get_extension_manager()

EXT_ID = "omni.warp.menu"

GETTING_STARTED_URL = "https://docs.omniverse.nvidia.com/extensions/latest/ext_warp.html"
DOCUMENTATION_URL = "https://nvidia.github.io/warp/"


with suppress(ImportError):
    import omni.ui


try:
    from omni.kit.menu.utils import MenuItemDescription

    HAS_KIT_MENU_UTILS_EXT = True
except ImportError:
    HAS_KIT_MENU_UTILS_EXT = False



if HAS_KIT_MENU_UTILS_EXT:

    def menu_create() -> MenuItemDescription:
        registry = omni.kit.actions.core.get_action_registry()
        tag = "Warp Actions"

        registry.register_action(
            EXT_ID,
            "getting_started",
            lambda: webbrowser.open(GETTING_STARTED_URL),
            display_name="Warp->Getting Started",
            tag=tag,
        )
        registry.register_action(
            EXT_ID,
            "documentation",
            lambda: webbrowser.open(DOCUMENTATION_URL),
            display_name="Warp->Documentation",
            tag=tag,
        )

        menu = MenuItemDescription(
            name="Warp",
            appear_after="USD Reference Guide",
            sub_menu=(
                MenuItemDescription(
                    name="Getting Started",
                    onclick_action=(EXT_ID, "getting_started"),
                ),
                MenuItemDescription(
                    name="Documentation",
                    onclick_action=(EXT_ID, "documentation"),
                ),
            ),
        )

        omni.kit.menu.utils.add_menu_items((menu,), "Help")
        return menu

    def menu_destroy(menu: MenuItemDescription) -> None:
        omni.kit.menu.utils.remove_menu_items((menu,), "Help")

        registry = omni.kit.actions.core.get_action_registry()
        registry.deregister_all_actions_for_extension(EXT_ID)


class Extension(omni.ext.IExt):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._menu = None

    def on_startup(self, ext_id):
        if HAS_KIT_MENU_UTILS_EXT:
            self._menu = menu_create()

    def on_shutdown(self):
        if self._menu is not None:
            menu_destroy(self._menu)
            self._menu = None
