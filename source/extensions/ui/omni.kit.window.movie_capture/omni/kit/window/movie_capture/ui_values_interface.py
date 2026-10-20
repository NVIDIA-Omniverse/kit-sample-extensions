# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
"""This module defines a singleton interface that manages saving, retrieving, and applying UI settings for movie capture widgets—including capture, render, output, and farm settings—by persisting values to and from the current USD stage."""

import carb
import omni.usd

from . import base_widget, capture_settings_widget, farm_settings_widget, output_settings_widget, render_settings_widget
from .singleton import Singleton
from .ui_values_storage import UIValuesStorage


@Singleton
class UIValuesInterface:
    def __init__(self):
        self._internal_init()

    def _internal_init(self):
        self._ui_values = UIValuesStorage()

    def save_ui_values(
        self,
        capture_widget: capture_settings_widget.CaptureSettingsWidget,
        render_widget: render_settings_widget.RenderSettingsWidget,
        output_widget: output_settings_widget.OutputSettingsWidget,
        farm_widget: farm_settings_widget.FarmSettingsWidget,
    ):
        capture_widget.get_ui_values(self._ui_values)
        render_widget.get_ui_values(self._ui_values)
        output_widget.get_ui_values(self._ui_values)
        farm_widget.get_ui_values(self._ui_values)

        self._ui_values.save_to_current_stage()

    def try_update_ui_for_current_stage(
        self,
        capture_widget: capture_settings_widget.CaptureSettingsWidget,
        render_widget: render_settings_widget.RenderSettingsWidget,
        output_widget: output_settings_widget.OutputSettingsWidget,
        farm_widget: farm_settings_widget.FarmSettingsWidget,
    ):
        stage_url = omni.usd.get_context().get_stage_url()
        if self._ui_values.ui_values_available_in_current_stage():
            carb.log_info(f"Movie capture: UI settings found for {stage_url}")
            self._ui_values.read_from_current_stage()
            self.apply_ui_values(capture_widget, render_widget, output_widget, farm_widget)
        else:
            carb.log_info(f"Movie capture: no UI settings found for {stage_url}")

    def apply_ui_values(
        self,
        capture_widget: capture_settings_widget.CaptureSettingsWidget,
        render_widget: render_settings_widget.RenderSettingsWidget,
        output_widget: output_settings_widget.OutputSettingsWidget,
        farm_widget: farm_settings_widget.FarmSettingsWidget,
    ):
        capture_widget.apply_ui_values(self._ui_values)
        render_widget.apply_ui_values(self._ui_values)
        output_widget.apply_ui_values(self._ui_values)
        farm_widget.apply_ui_values(self._ui_values)
