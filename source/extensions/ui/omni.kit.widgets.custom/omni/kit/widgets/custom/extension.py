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
import omni
from omni import ui

from .window import WindowMenuHelper


def has_extension(ext_name):
    ext_manager = omni.kit.app.get_app_interface().get_extension_manager()
    extension = next(
        (ext for ext in ext_manager.get_extensions() if ext["id"].startswith(ext_name) and ext["enabled"]), None
    )
    return extension is not None


def get_ext_instance(ext_name):
    from omni.ext import _internal as g_extension_20

    exts = g_extension_20._extensions
    for ext in exts:
        if ext_name in ext:
            # print(f"Matched: {ext}")
            ext_instance, _ = exts[ext]._started_extensions[0]
            return ext_instance
    carb.log_error(f"Extension ({ext_name}) is not loaded")
    return None


class WindowExtension:
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(
        self,
        menu_path=None,
        hotkey=None,
        appear_after="",
        use_editor_menu=False,
        on_visibility_changed_fn: callable = None,
    ):
        self._window = self._create_window()
        if self._window is None:
            carb.log_error(
                "Failed to create extension window! Please make sure _create_window is defined in extension!"
            )

        if menu_path is None:
            self._menu = None
        else:
            self._menu = WindowMenuHelper(
                self._window,
                menu_path,
                hotkey=hotkey,
                appear_after=appear_after,
                use_editor_menu=use_editor_menu,
                on_visibility_changed_fn=on_visibility_changed_fn,
            )

    def on_shutdown(self):
        if self._menu is not None:
            self._menu.destroy()
            self._menu = None
        self._window.destroy()
        self._window = None

    def is_visible(self):
        return self._window.is_visible()

    def show(self, visible=True):
        if self._window is not None:
            self._window.show(visible)

    def hide(self):
        if self._window is not None:
            self._window.show(False)

    @property
    def active(self):
        if self._window is not None:
            return self._window.get_active()
        else:
            return False

    @active.setter
    def active(self, value):
        if self._window is not None:
            self._window.set_active(value)

    def dock(self, target, position=ui.DockPosition.RIGHT):
        if self._window is not None:
            self._window.dock(target, 0.311, position)

    def _create_window(self):  # pragma: no cover
        # create window
        print("should NOT be here!!")
        return None
