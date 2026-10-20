# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Dict

from omni import ui
from omni.kit.widget.sliderbar import ArrowAlignment, TimeSliderBar
from pxr import Sdf

from ..constants import EnvironmentProperties
from ..models import UsdModelBuilder
from .player import SunstudyPlayer


class SunstudyTimeSlider(TimeSliderBar):
    """
    Represent a slider bar to show sunstudy play times.
    User could view and set start time, stop time and current time.
    """

    def __init__(self, on_datetime_changed_fn: Callable[[str], None] = None, style: Dict = {}):
        self._on_datetime_changed_fn = on_datetime_changed_fn
        self._style = style

        self.start_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_START, value_type=Sdf.ValueTypeNames.Float, default=6.0
        )
        self.end_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_END, value_type=Sdf.ValueTypeNames.Float, default=18.0
        )
        self.current_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_CURRENT, value_type=Sdf.ValueTypeNames.Float, default=6.0
        )

        super().__init__(
            start=self.start_time_model.as_float,
            end=self.end_time_model.as_float,
            current=self.current_time_model.as_float,
            padding_width=30,
            slider_padding_width=30,
            style=self._style,
            arrow_height=10,
            start_arrow_alignment=ArrowAlignment.CENTER,
            end_arrow_alignment=ArrowAlignment.CENTER,
        )
        self.add_callback_fns(self._on_start_changed, self._on_end_changed, self._on_time_changed)
        self.start_time_model.add_value_changed_fn(self._on_start_time_model_changed)
        self.end_time_model.add_value_changed_fn(self._on_end_time_model_changed)
        self.current_time_model.add_value_changed_fn(self._on_current_time_model_changed)

    def destroy(self):
        """Calls the parent class's destroy method to cleanup slider resources."""
        super().destroy()

    def _on_start_time_model_changed(self, model: ui.AbstractValueModel):
        self.set_start(model.as_float)

    def _on_end_time_model_changed(self, model: ui.AbstractValueModel):
        self.set_end(model.as_float)

    def _on_current_time_model_changed(self, model: ui.AbstractValueModel):
        self.set_current(model.as_float)

    def _on_start_changed(self, value: float) -> None:
        self.start_time_model.set_value(value)

    def _on_end_changed(self, value: float) -> None:
        self.end_time_model.set_value(value)

    def _on_time_changed(self, value: float) -> None:
        if value != self.current_time_model.as_float:
            self.current_time_model.set_value(value)
