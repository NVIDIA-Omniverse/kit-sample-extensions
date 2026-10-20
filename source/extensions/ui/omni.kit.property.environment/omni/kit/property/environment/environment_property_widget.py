# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

from omni import ui
from omni.kit.environment.core import ENVIRONMENT_PRIM_ROOT, PlaySettings, SettingModel
from omni.kit.property.usd import PrimSelectionPayload
from omni.kit.window.property import PropertyWidget

from .groups import DateTimeGroup, EnvironmentOptionsGroup, LocationGroup, NotificationGroup, WeatherGroup


class EnvironmentPropertyWidget(PropertyWidget):
    """EnvironmentPropertyWidget provides a UI widget to display and manage controls for environment properties in the omni.kit.property.environment extension. It aggregates multiple UI groups to allow users to adjust environment options, date and time settings, location information, weather parameters, and notification preferences.

    This widget processes payloads related to the environment prim selection. When a valid payload is received, it checks for the correct environment prim and updates the UI groups accordingly. It dynamically adapts the display based on the current environment type by toggling the visibility of groups related to date/time, location, weather, and notifications. The widget instantiates and manages separate control groups for each aspect of the environment to provide an integrated property editing experience.

    No arguments are required for initialization.
    """

    def __init__(self):
        super().__init__("Environment")
        self._payload: Optional[PrimSelectionPayload] = None
        self._env_group = None
        self._date_time_group = None
        self._location_group = None
        self._weather_group = None
        self._notification_group = NotificationGroup()

        self._env_group = EnvironmentOptionsGroup(self._payload)
        self._date_time_group = DateTimeGroup()
        self._location_group = LocationGroup()
        self._weather_group = WeatherGroup()

        self._current_sky_type_model = SettingModel(PlaySettings.CURRENT_SKY_TYPE)
        self._current_sky_type_model.add_value_changed_fn(self._on_sky_type_changed)

    def destroy(self):
        """Destroys widget groups by calling their destroy methods.

        Calls destroy on the environment options group, date time group, location group, weather group, and notification group.
        """
        self._env_group.destroy()
        self._date_time_group.destroy()
        self._location_group.destroy()
        self._weather_group.destroy()
        self._notification_group.destroy()

    def clean(self):
        """Performs cleanup actions for the widget.

        No operations are performed in this implementation.
        """
        pass

    def reset(self):
        """Resets the widget state to its initial configuration.

        No operations are performed in this implementation.
        """
        pass

    def on_new_payload(self, payload: PrimSelectionPayload) -> bool:
        """Updates the environment property widget with a new prim selection payload and displays the widget if only the environment prim is selected.

        Args:
            payload (PrimSelectionPayload): New prim selection payload to be processed.

        Returns:
            bool: True if the payload is valid and used, False otherwise.
        """
        self._payload = payload
        if not self._payload or len(self._payload) == 0:
            return False

        # Only Environment prim selected, show property widgets
        used = True
        for prim_path in self._payload:
            if prim_path != ENVIRONMENT_PRIM_ROOT:
                used = False

        if used:
            self._env_group.on_new_payload(self._payload)

        return used

    def build_impl(self) -> None:
        """Constructs the user interface layout for the environment property widget.

        Builds the widget groups in a vertical stack and updates visibility based on the current sky type.
        """
        with ui.VStack(height=0, spacing=10):
            # Called when creating prim property widgets
            self._env_group.build()
            self._date_time_group.build()
            self._location_group.build()
            self._weather_group.build()
            self._notification_group.build()

        self._on_sky_type_changed(self._current_sky_type_model)

    def _on_sky_type_changed(self, model: SettingModel) -> None:
        sky_type = model.as_string
        is_dynamic_sky = sky_type == "Dynamic"
        if self._date_time_group:
            self._date_time_group.visible = is_dynamic_sky
            self._location_group.visible = is_dynamic_sky
            self._weather_group.visible = is_dynamic_sky
            self._notification_group.visible = not is_dynamic_sky
