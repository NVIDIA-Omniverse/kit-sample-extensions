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

import carb.dictionary
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni import ui

from .base_value_model import BaseValueModel


# Comes from omni.kit.widget.settings but remove the reset button
class SettingModel(BaseValueModel):
    """
    Model for simple scalar/POD carb.settings
    """

    def __init__(self, setting_path: str, draggable: bool = False):
        """
        Args:
            setting_path: setting_path carb setting to create a model for
            draggable: is it a numeric value you will drag in the UI?
        """
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._dictionary = carb.dictionary.get_dictionary()
        self._path = setting_path
        self.draggable = draggable
        self.initialValue = None
        self._editing = False

        self._update_setting = omni.kit.app.SettingChangeSubscription(self._path, self._on_change)

    def destroy(self):
        """Clean up resources by calling the parent destroy method and clearing the update subscription."""
        super().destroy()
        self._update_setting = None

    def _on_change(self, value, event_type) -> None:
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._on_dirty()

    def begin_edit(self) -> None:
        """Begin editing the setting value.

        Sets the editing state, invokes the parent begin_edit, and stores the initial value.
        """
        self._editing = True
        ui.AbstractValueModel.begin_edit(self)
        self.initialValue = self._settings.get(self._path)

    def end_edit(self) -> None:
        """End editing the setting value.

        Calls the parent end_edit, updates the setting, marks the USD stage as pending edit, and resets the editing state.
        """
        ui.AbstractValueModel.end_edit(self)
        self._settings.set(self._path, self._settings.get(self._path))
        # Marks stage dirty manually since settings change are not synced to USD until user saves.
        omni.usd.get_context().set_pending_edit(True)
        self._editing = False

    def get_value_as_string(self) -> str:
        """Return the current setting value as a string.

        Returns:
            str: The setting value in string format.
        """
        return self._settings.get(self._path)

    def get_value_as_float(self) -> float:
        """Return the current setting value as a float.

        Returns:
            float: The setting value as a float.
        """
        return self._settings.get(self._path)

    def get_value_as_bool(self) -> bool:
        """Return the current setting value as a bool.

        Returns:
            bool: The setting value as a boolean.
        """
        return self._settings.get(self._path)

    def get_value_as_int(self) -> int:
        """Return the current setting value as an int.

        Returns:
            int: The setting value as an integer.
        """
        return self._settings.get(self._path)

    def set_value(self, value: Any):
        """Set the setting to a new value.

        If the setting is not draggable, updates the setting, marks the USD stage as pending edit, and notifies changes. Otherwise, only updates the setting.

        Args:
            value (Any): The new value for the setting.
        """
        if not self.draggable:
            self._settings.set(self._path, value)
            # Marks stage dirty manually since settings change are not synced to USD until user saves.
            omni.usd.get_context().set_pending_edit(True)
            self._on_dirty()
        else:
            self._settings.set(self._path, value)

    def _on_dirty(self):
        # Tell the widgets that the model value has changed
        self._value_changed()
