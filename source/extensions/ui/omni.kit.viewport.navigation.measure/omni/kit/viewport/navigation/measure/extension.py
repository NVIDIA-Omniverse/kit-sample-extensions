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
from omni.kit.tool.measure import get_instance as get_measure_instance
from omni.kit.viewport.navigation.core import IMAGE_SIZE, ViewportNavigationButton, get_navigation_bar

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.measure/"
# Opt-in (default off): when enabled, toggling the Measure panel visibility also
# shows/hides the completed measurements in the viewport. Off by default so the
# button keeps its original panel-only behavior for clients that do not opt in.
MEASURE_VISIBILITY_SETTING = SETTINGS_ROOT + "toggle_measurement_visibility"


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        navigaiton_bar = get_navigation_bar()

        self._settings = carb.settings.get_settings()
        self._measure_instance = get_measure_instance()

        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")
        true_image = icon_path + "navMeasure_active_dark.svg"
        false_image = icon_path + "navMeasure_dark.svg"
        order_setting = SETTINGS_ROOT + "order"
        visible_setting = SETTINGS_ROOT + "visible"
        name = "measure"
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
                build_tooltip_fn=self._build_measure_tooltip,
                style=style,
            )
            self._button.set_state(False)

        self._toggle_id = ui.Workspace.set_window_visibility_changed_callback(self._visibility_changed_fn)

        # Opt-in: sync measurement visibility to the initial panel state.
        if self._measure_instance and self._measure_instance.panel:
            self._sync_measurement_visibility(self._measure_instance.panel.visible)

    def _build_measure_tooltip(self):
        TOOLTIP_SIDE_SPACE = 5
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Measure", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (85, 32)

    def _on_click(self, *_):
        self._button.set_state(not self._measure_instance.panel.visible)
        self._measure_instance._show_window(None, not self._measure_instance.panel.visible)

    def _visibility_changed_fn(self, name: str, visible: bool):
        if name == "Measure":
            self._button.set_state(visible)
            self._sync_measurement_visibility(visible)

    def _sync_measurement_visibility(self, visible: bool):
        """When opted in, couple measurement visibility to the Measure panel state.

        Off by default via MEASURE_VISIBILITY_SETTING so the button retains its
        original panel-only behavior. Drives the Measure tool's transient
        (non-persistent) visibility API, leaving the user's persistent Display-menu
        preference untouched.
        """
        if not self._settings.get_as_bool(MEASURE_VISIBILITY_SETTING):
            return
        if self._measure_instance and hasattr(self._measure_instance, "set_measurements_visible"):
            self._measure_instance.set_measurements_visible(visible)

    def on_shutdown(self):
        self._button.destroy()
        self._button = None

        self._measure_instance = None
        self._turntable_sub = None
        ui.Workspace.remove_window_visibility_changed_callback(self._toggle_id)
