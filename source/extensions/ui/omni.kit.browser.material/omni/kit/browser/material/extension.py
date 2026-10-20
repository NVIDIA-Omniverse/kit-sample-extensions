# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Any

import carb.settings
import omni
import omni.ext
import omni.ui as ui

from .actions import deregister_actions, register_actions
from .delegate import MATERIAL_DRAG_PAYLOAD_PREFIX
from .usd_reader import shutdown_usd_readers, start_usd_readers
from .window import MaterialBrowserWindow

BROWSER_MENU_ROOT = "Window"
MATERIAL_BROWSER_MENU_PATH = "Window/Browsers/Material Browser"
ENABLE_SETTING_PATH = "/exts/omni.kit.browser.material/enabled"
_extension_instance = None


class MaterialBrowserExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        start_usd_readers()
        self.__ext_id = omni.ext.get_extension_name(ext_id)
        settings = carb.settings.get_settings()

        self._menu_entry = None
        self._window = None

        # Warmup model
        warmup = settings.get("/app/warmupMode") or False
        if warmup:
            from .model import MaterialBrowserModel

            self.__model = MaterialBrowserModel(run_warmup=True)

        register_actions(self.__ext_id)
        self._register_stage_drop_handler()

        # subscribe to value changes, returned object is subscription holder. To unsubscribe - destroy it.
        self._sub_enabled = omni.kit.app.SettingChangeSubscription(ENABLE_SETTING_PATH, self._on_enable_change)

        enabled = settings.get(ENABLE_SETTING_PATH)
        self._enabled(enabled)

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        # Stop accepting stage reads before anything else is torn down. Does not wait: a reader
        # holds no model reference, so one still running is harmless.
        shutdown_usd_readers()
        self._enabled(False)

        deregister_actions(self.__ext_id)
        self._deregister_stage_drop_handler()

        global _extension_instance
        _extension_instance = None

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = MaterialBrowserWindow()
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
                        name=MaterialBrowserWindow.WINDOW_TITLE,
                        ticked=True,
                        ticked_fn=self._is_visible,
                        onclick_fn=self._toggle_window,
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_entry, BROWSER_MENU_ROOT)

    def _deregister_menuitem(self):
        if self._menu_entry:
            omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)

    def _is_visible(self):
        return self._window.visible if self._window else False

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items(BROWSER_MENU_ROOT)

    def _register_stage_drop_handler(self):
        try:
            import omni.kit.actions.core
            from omni.kit.widget.stage import DragAndDropRegistry as MaterialDragAndDropRegistry

            def filter(source: Any) -> bool:
                return isinstance(source, str) and source.startswith(MATERIAL_DRAG_PAYLOAD_PREFIX)

            def drop_handler(source: Any, target_item: Any) -> None:
                # Drop from environment window
                action_registry = omni.kit.actions.core.get_action_registry()
                action = action_registry.get_action("omni.kit.browser.material", "drop")
                material_path = None
                if action:
                    material_path = action.execute(source)

                # Bind created material to the target prim
                # Special case: don't bind it to /World and to /World/Looks
                if material_path and target_item:
                    target_path = target_item.path
                    if omni.usd.is_prim_material_supported(target_item.prim) and target_path not in ["/World"]:
                        omni.kit.commands.execute(
                            "BindMaterial", prim_path=target_path, material_path=material_path, strength=None
                        )

            MaterialDragAndDropRegistry().register_drop_handler("material", filter, drop_handler)
        except:
            pass

    def _deregister_stage_drop_handler(self):
        try:
            import omni.kit.actions.core
            from omni.kit.widget.stage import DragAndDropRegistry as MaterialDragAndDropRegistry

            MaterialDragAndDropRegistry().deregister_drop_handler("material")
        except:
            pass

    def _on_enable_change(self, value, change_type: carb.settings.ChangeEventType):
        if change_type == carb.settings.ChangeEventType.CHANGED:
            enabled = carb.settings.get_settings().get(ENABLE_SETTING_PATH)
            self._enabled(enabled)

    def _enabled(self, enabled: bool):
        if enabled:
            ui.Workspace.set_show_window_fn(
                MaterialBrowserWindow.WINDOW_TITLE,
                self._show_window,  # pylint: disable=unnecessary-lambda
            )
            if self._menu_entry is None:
                self._register_menuitem()
        else:
            self._deregister_menuitem()
            ui.Workspace.set_show_window_fn(MaterialBrowserWindow.WINDOW_TITLE, None)

            if self._window is not None:
                self._window.destroy()
                self._window = None


def get_instance():
    return _extension_instance
