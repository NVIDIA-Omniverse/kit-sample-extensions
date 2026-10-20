# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.ext
import omni.kit.app
import omni.kit.menu.utils
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher

from .actions import deregister_actions, register_actions
from .models.stage_template import load_stage_templates
from .window import SETTING_ROOT, EnvironmentWindow

BROWSER_MENU_ROOT = "Window"
_extension_instance = None
SETTING_LOAD_AFTER_VISIBLE = SETTING_ROOT + "visible_after_startup"


class EnvironmentBrowserExtension(omni.ext.IExt):
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
        register_actions(self.__ext_id)

        self._window = None
        ui.Workspace.set_show_window_fn(
            EnvironmentWindow.WINDOW_TITLE,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        settings = carb.settings.get_settings()
        visible = settings.get_as_bool(SETTING_LOAD_AFTER_VISIBLE)
        if visible:
            self._show_window(True)
        else:
            # Warmup model
            warmup = carb.settings.get_settings().get("/app/warmupMode") or False
            if warmup:
                from .models import EnvBrowserModel

                self.__model = EnvBrowserModel(run_warmup=True)

        self._app_ready_sub = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_APP_READY,
            on_event=self.__on_app_ready,
            observer_name="omni.kit.window.environment.app_ready",
        )

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)
        self._app_ready_sub = None
        deregister_actions(self.__ext_id)

        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    def shonavigate_to_dynamic_skiesw_panel(self) -> None:
        self._window.navigate_to_dynamic_skies()

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = EnvironmentWindow(visible=True)
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
                        name="Environment", ticked=True, ticked_fn=self._is_visible, onclick_fn=self._toggle_window
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_entry, BROWSER_MENU_ROOT)

    def _is_visible(self):
        return self._window.visible if self._window else False

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items(BROWSER_MENU_ROOT)

    def __on_app_ready(self, *args, **kwargs):
        self._app_ready_sub = None
        load_stage_templates()


def get_instance():
    return _extension_instance
