# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb.dictionary
import carb.settings
import carb.tokens
import omni.ext
import omni.ui as ui
from omni.kit.viewport.navigation.core import IMAGE_SIZE, ViewportNavigationButton, get_navigation_bar
from omni.kit.window.section import get_instance as get_section_instance

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.section/"


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        navigaiton_bar = get_navigation_bar()

        self._settings = carb.settings.get_settings()
        self._section_instance = get_section_instance()

        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")
        true_image = icon_path + "navSection_active_dark.svg"
        false_image = icon_path + "navSection_dark.svg"
        order_setting = SETTINGS_ROOT + "order"
        visible_setting = SETTINGS_ROOT + "visible"
        name = "section"
        style = {
            "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
        }
        with navigaiton_bar:
            self._button = ViewportNavigationButton(
                name,
                IMAGE_SIZE,
                visible_setting_path=visible_setting,
                order_setting_path=order_setting,
                clicked_fn=self._on_click,
                build_tooltip_fn=self._build_tooltip,
                style=style,
            )
            self._button.set_state(False)

        self._toggle_id = ui.Workspace.set_window_visibility_changed_callback(self._visibility_changed_fn)

    def _build_tooltip(self):
        TOOLTIP_SIDE_SPACE = 5
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Section", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (85, 32)

    def _on_click(self, *_):
        window = self._section_instance._window
        visible = window and window.visible
        self._button.set_state(not visible)
        self._section_instance.show_window(None, not visible)

    def _visibility_changed_fn(self, name: str, visible: bool):
        if name == "Section":
            self._button.set_state(visible)

    def on_shutdown(self):
        self._button.destroy()
        self._button = None
        self._section_instance = None
        ui.Workspace.remove_window_visibility_changed_callback(self._toggle_id)
