# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import math

from omni import ui
from omni.kit.environment.core import (
    CityComboBox,
    EnvironmentProperties,
    ResetButton,
    UsdModelBuilder,
    get_sunstudy_player,
)
from pxr import Sdf

from .property_group import AbstractPropertyGroup


class LocationGroup(AbstractPropertyGroup):
    def __init__(self):
        self._city_combobox = None

        self._longitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LONGITUDE, value_type=Sdf.ValueTypeNames.Double, default=0.0, min=-180, max=180
        )

        self._latitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LATITUDE, value_type=Sdf.ValueTypeNames.Double, default=0.0, min=-90, max=90
        )

        self._longitude_model.add_value_changed_fn(self._reset_city)
        self._latitude_model.add_value_changed_fn(self._reset_city)

        self._north_orientation_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.NORTH_ORIENTATION, value_type=Sdf.ValueTypeNames.Double, default=0.0, min=0, max=360
        )

        self._player = get_sunstudy_player()

        super().__init__("Location")

    def _build_widgets(self):
        with ui.VStack(height=0, spacing=5):
            with ui.HStack():
                self._create_label("Preset")
                self._city_combobox = CityComboBox()
                ui.Spacer(width=100 + 15)
                # ResetButton(self._city_combobox.model._current_index)

            with ui.HStack():
                self._create_label("Latitude")
                self._create_float_drag(self._latitude_model, name="location")
                ui.Spacer(width=10)
                ResetButton(self._latitude_model)

            with ui.HStack():
                self._create_label("Longitude")
                self._create_float_drag(self._longitude_model, name="location")
                ui.Spacer(width=10)
                ResetButton(self._longitude_model)

            with ui.HStack():
                self._create_label("North Orientation")
                self._create_float_drag(self._north_orientation_model, name="location")
                ui.Spacer(width=10)
                ResetButton(self._north_orientation_model)

        self._city_combobox.model.set_location(self._longitude_model.as_float, self._latitude_model.as_float)
        self._city_combobox.model.add_item_changed_fn(self._on_city_changed)

    def _on_city_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem):
        idx = model.get_item_value_model().as_int
        if idx == 0:
            # Custom, keep longitude and latitude without changes
            if self._player is not None:
                self._player.update_fix_timezone(False)
            return

        location_item = model.get_item_children(item)[idx]
        longitude = model.get_item_value_model(location_item, column_id=1).as_float
        latitude = model.get_item_value_model(location_item, column_id=2).as_float

        if abs(latitude - self._latitude_model.as_float) >= 0.00001:
            self._latitude_model.set_value(latitude)
        if abs(longitude - self._longitude_model.as_float) >= 0.00001:
            self._longitude_model.set_value(longitude)

        if self._player is not None:
            self._player.update_fix_timezone(True)

    def _reset_city(self, *_):
        if self._city_combobox is not None:
            latitude = self._latitude_model.as_float
            longitude = self._longitude_model.as_float
            self._city_combobox.model.set_location(longitude, latitude)
