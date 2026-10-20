# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Any, Optional

import carb.settings
import omni.ext
import omni.kit.menu.utils
import omni.ui as ui
import wrapp
from omni.kit.browser.core import TreeBrowserWidget

from .actions import deregister_actions, register_actions
from .browser_model import WrappBrowserModel
from .consistents import WRAPP_EXPLORER_DRAG_PREFIX
from .empty_property_delegate import EmptyPropertyDelegate
from .multi_property_delegate import MultiPropertyDelegate
from .prop_property_delegate import PropWrappAssetPropertyDelegate
from .window import WRAPP_EXPLORER_NAME, WrappBrowserWindow

BROWSER_MENU_ROOT = "Window"
SETTINGS_ROOT = "/exts/omni.wrapp.package_explorer/"
SETTINGS_VISIBLE = SETTINGS_ROOT + "visible_after_startup"

_extension_instance = None


def register_stage_pane_drop_handler():
    def wrapp_filter(source: Any) -> bool:
        return isinstance(source, str) and source.startswith(WRAPP_EXPLORER_DRAG_PREFIX)

    def wrapp_handler(source: Any, target_item: Any) -> None:
        # Drop from Package Explorer
        try:
            import omni.kit.actions.core as actions_core
        except ImportError:
            carb.log_warn("omni.kit.actions.core not available; skipping Package Explorer drop action.")
            return

        action_registry = actions_core.get_action_registry()
        action = action_registry.get_action("omni.wrapp.package_explorer", "add_asset_from_drag")
        if action:
            if hasattr(target_item, "path"):
                path_to = target_item.path
            else:
                path_to = None
            action.execute(source, path_to=path_to)
            return

    try:
        from omni.kit.widget.stage import DragAndDropRegistry

        DragAndDropRegistry().register_drop_handler("Package Explorer", wrapp_filter, wrapp_handler)
    except ImportError:
        carb.log_info("omni.kit.widget.stage is not available. Skip stage pane drop handler registration.")


def deregister_stage_pane_drop_handler():
    try:
        from omni.kit.widget.stage import DragAndDropRegistry

        DragAndDropRegistry().deregister_drop_handler("Package Explorer")
    except ImportError:
        carb.log_info("omni.kit.widget.stage is not available. Skip stage pane drop handler deregistration.")


class WrappBrowserExtension(omni.ext.IExt):
    def __init__(self):
        self.__ext_id = None
        self._wrapp_context_manager = None
        self._window = None
        self._menu_entry = None
        self._empty_property_delegate = None
        self._propasset_property_delegate = None
        self._multi_property_delegate = None
        super().__init__()

    @property
    def window(self) -> Optional[WrappBrowserWindow]:
        return self._window

    @property
    def browser_widget(self) -> Optional[TreeBrowserWidget]:
        if self._window is None:
            return None
        return self._window._widget

    @property
    def browser_model(self) -> Optional[WrappBrowserModel]:
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

        wrapp.initialize(
            throttling_params=wrapp.ThrottlingParameters(
                jobs=200,
                tagging_jobs=50,
                file_transfer_jobs=50,
            )
        )

        self._auth_manager = wrapp.AuthManager(interactive_fallback=True)
        self._auth_manager.initialize()

        register_actions(self.__ext_id, self)

        self._window = None
        ui.Workspace.set_show_window_fn(
            WRAPP_EXPLORER_NAME,
            self._show_window,  # pylint: disable=unnecessary-lambda
        )
        self._register_menuitem()

        visible = carb.settings.get_settings().get_as_bool(SETTINGS_VISIBLE)
        if visible:
            self._show_window(True)

        # Instantiate the property delegates so they get registered with class BrowserPropertyDelegate
        self._empty_property_delegate = EmptyPropertyDelegate()
        self._propasset_property_delegate = PropWrappAssetPropertyDelegate()
        self._multi_property_delegate = MultiPropertyDelegate()

        global _extension_instance
        _extension_instance = self

        register_stage_pane_drop_handler()

    def on_shutdown(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=BROWSER_MENU_ROOT)
        if self._window is not None:
            self._window.destroy()
            self._window = None

        deregister_actions(self.__ext_id)
        deregister_stage_pane_drop_handler()

        self._auth_manager.shutdown()
        self._auth_manager = None

        wrapp.shutdown(shutdown_client_lib=False)

        self._window = None
        self._menu_entry = None
        self._empty_property_delegate = None
        self._propasset_property_delegate = None
        self._multi_property_delegate = None

        global _extension_instance
        _extension_instance = None

    def _show_window(self, visible) -> None:
        if visible:
            if self._window is None:
                self._window = WrappBrowserWindow(visible=True)
                self._window.set_visibility_changed_fn(self._on_visibility_changed)
            else:
                self._window.visible = True
        else:
            if self._window:
                self._window.visible = False

    def _toggle_window(self):
        self._show_window(not self._is_visible())

    def _register_menuitem(self):
        self._menu_entry = [
            omni.kit.menu.utils.MenuItemDescription(
                name="Browsers",
                sub_menu=[
                    omni.kit.menu.utils.MenuItemDescription(
                        name=WRAPP_EXPLORER_NAME,
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


def get_instance() -> Optional[WrappBrowserExtension]:
    return _extension_instance
