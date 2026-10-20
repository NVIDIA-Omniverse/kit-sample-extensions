# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import random
from typing import Optional

from omni import ui
from omni.kit.environment.core import (
    EnvironmentProperties,
    PropertyValueModel,
    ResetButton,
    UsdModelBuilder,
)
from pxr import Sdf

from .property_group import AbstractPropertyGroup


class WeatherGroup(AbstractPropertyGroup):
    def __init__(self):
        self._cloud_coverage_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.CLOUD_COVERAGE, value_type=Sdf.ValueTypeNames.Double, default=0.0, min=-0.5, max=0.5
        )

        self._haze_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.HAZE, value_type=Sdf.ValueTypeNames.Double, default=0.0, min=0.0, max=1.0
        )

        self._cumulus_enabled_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.CUMULUS_ENABLED, value_type=Sdf.ValueTypeNames.Bool, default=False
        )
        self._cumulus_enabled_model.add_value_changed_fn(self._on_cumulus_enabled_changed)

        self._randomize_button: Optional[ui.Button] = None
        self._cloud_coverage_slider: Optional[ui.FloatSlider] = None
        self._haze_slider: Optional[ui.FloatSlider] = None

        super().__init__("Weather", enable_model=self._cumulus_enabled_model)

    def _build_widgets(self):
        with ui.VStack(height=0, spacing=5):

            def _randomize_weather():
                self._cloud_coverage_model.set_value(random.random() - 0.5)
                self._haze_model.set_value(random.random())

            self._randomize_button = self._create_button(
                "Randomize", name="randomize", width=70, clicked_fn=_randomize_weather
            )

            with ui.HStack(spacing=5):
                self._create_label("Blue Sky", width=50, alignment=ui.Alignment.RIGHT_CENTER)
                self._cloud_coverage_slider = self._create_float_slider(self._cloud_coverage_model, name="weather")
                self._create_label("Overcast", width=50)
                ResetButton(self._cloud_coverage_model)

            with ui.HStack(spacing=5):
                self._create_label("Clear", width=50, alignment=ui.Alignment.RIGHT_CENTER)
                self._haze_slider = self._create_float_slider(self._haze_model, name="weather")
                self._create_label("Hazy", width=50)
                ResetButton(self._haze_model)

            self._on_cumulus_enabled_changed(self._cumulus_enabled_model)

    def _on_cumulus_enabled_changed(self, model: PropertyValueModel) -> None:
        if self._randomize_button:
            self._randomize_button.enabled = model.as_bool
        if self._cloud_coverage_slider:
            self._cloud_coverage_slider.enabled = model.as_bool
        if self._haze_slider:
            self._haze_slider.enabled = model.as_bool
