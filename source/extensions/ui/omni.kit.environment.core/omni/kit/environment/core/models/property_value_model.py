# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Any, Callable, List, Optional, Union

import carb
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni import ui
from pxr import Sdf, Usd

from ..constants import ENVIRONMENT_PRIM_ROOT
from ..utils import get_environment_edit_context
from .base_value_model import BaseValueModel


class PropertyValueModel(BaseValueModel):
    """
    Model for simple usd property.
    Args:
        property_path (str): Property path in usd stage.
        stage (Usd.Stage): Usd stage that property belongs to.
    Keyword args:
        value_type (Sdf.ValueTypeName): Property value type. Used to create attribute if not exists, Default Sdf.ValueTypeNames.String.
        default (Any): Default property value.
        min (Union[int, float, None]): Min value. Default None.
        max (Union[int, float, None]): Max value. Default None.
        default_prim_type (Optional[str]): Prim type when creating if prim that propert belongs to does not exists. Default None to donot create.
    """

    def __init__(
        self,
        property_path: str,
        stage: Usd.Stage,
        value_type: Sdf.ValueTypeName = Sdf.ValueTypeNames.String,
        default: Any = "",
        min: Union[int, float, None] = None,
        max: Union[int, float, None] = None,
        default_prim_type: Optional[str] = None,
    ):
        super().__init__(default_value=default)
        self.property_path = property_path
        self._stage = stage
        self._value_type = value_type
        self._default_prim_type = default_prim_type
        self.min = min
        self.max = max

    def destroy(self):
        """Destroys the property value model by calling the base class destroy method."""
        super().destroy()

    def set_value(self, value: Any) -> None:
        """Sets the property value on the usd stage after validation and clamping.

        If the stage is not available or the value fails validation, no update is performed. Updates the pending edit flag when the value changes and creates an attribute if it does not exist.

        Args:
            value (Any): Value to set after validation and adjustment based on min and max constraints.
        """
        if not self._stage:
            return

        value = self._get_valid_value(value)
        if value is None:
            return

        if self.min is not None:
            value = max(value, self.min)
        if self.max is not None:
            value = min(value, self.max)

        if self.property_path.startswith(ENVIRONMENT_PRIM_ROOT):
            # OMPE-64890: the value itself needs a writable layer too, not only the prim creation
            with get_environment_edit_context(self._stage):
                self.__author_value(value)
        else:
            self.__author_value(value)

    def __author_value(self, value: Any) -> None:
        prop = self._stage.GetPropertyAtPath(self.property_path)
        if prop:
            old_value = prop.Get()
            if self._is_value_changed(value, old_value):
                # print(f"[{self.property_path}] Value changed from {old_value} to {value}")
                # Marks stage dirty manually since settings change are not synced to USD until user saves.
                omni.usd.get_context().set_pending_edit(True)
                prop.Set(value)
        else:
            # Create attribute
            prim_path, attr_name = self.property_path.split(".")
            prim = self._stage.GetPrimAtPath(prim_path)
            if not prim:
                if self._default_prim_type is not None:
                    prim = self._stage.DefinePrim(prim_path, self._default_prim_type)
                else:
                    prim = self._stage.DefinePrim(prim_path)

            if prim:
                prim.CreateAttribute(attr_name, self._value_type).Set(value)
            else:
                carb.log_info(f"[{self.property_path}] Cannot set value since prim does not exists!")

    def get_value_as_string(self) -> str:
        """Returns the usd property value as a string.

        Returns:
            str: Property value converted to a string.
        """
        return str(self._get_property_value())

    def get_value_as_float(self) -> float:
        """Returns the usd property value as a float.

        Returns:
            float: Property value converted to a float.
        """
        return float(self._get_property_value())

    def get_value_as_bool(self) -> bool:
        """Returns the usd property value as a bool.

        Returns:
            bool: Property value converted to a boolean.
        """
        return bool(self._get_property_value())

    def get_value_as_int(self) -> int:
        """Returns the usd property value as an int.

        Returns:
            int: Property value converted to an integer.
        """
        return int(self._get_property_value())

    def _get_property_value(self) -> Optional[Any]:
        if not self._stage:
            return self.default

        # TODO: cache the value to donot read property again without changing
        prop = self._stage.GetPropertyAtPath(self.property_path)
        if prop:
            if isinstance(prop, Usd.Relationship):
                # material:binding
                targets = prop.GetTargets()
                if targets:
                    paths = [path.pathString for path in targets]
                    return ",".join(paths)
                else:
                    return ""
            return prop.Get()
        else:
            # print(f"[{self.property_path}] Property not found, use default value {self.default}")
            return self.default

    def on_property_changed(self, stage: Usd.Stage):
        """Updates the model with the new usd stage and triggers a notification of the value change.

        Args:
            stage (Usd.Stage): Updated usd stage instance.
        """
        self._stage = stage
        # Only notify model value changed, read property when get model value
        self._value_changed()

    def _get_valid_value(self, value) -> Optional[Any]:
        if self._value_type == Sdf.ValueTypeNames.Float or self._value_type == Sdf.ValueTypeNames.Double:
            try:
                return float(value)
            except ValueError:
                return None
        elif self._value_type == Sdf.ValueTypeNames.Int:
            try:
                return int(value)
            except ValueError:
                return None
        return value

    def _is_value_changed(self, new_value: Any, old_value: Any) -> bool:
        return new_value != old_value
