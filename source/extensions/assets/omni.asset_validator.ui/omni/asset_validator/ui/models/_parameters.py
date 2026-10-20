# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from contextlib import suppress
from typing import TypeVar

from omni.asset_validator.core import (
    Parameter,
    ParameterType,
    Requirement,
    RequirementsRegistry,
    UserParameter,
    add_registry_requirement_callback,
)
from omni.ui import AbstractItem, AbstractItemModel, AbstractValueModel, SimpleStringModel

from ._options import OptionGroup, OptionsModel

T = TypeVar("T", int, bool, float, str)


__all__ = [
    "BoolUserParameterModel",
    "EnumUserParameterModel",
    "EnumerationItem",
    "EnumerationValueModel",
    "FloatUserParameterModel",
    "IntUserParameterModel",
    "ParametersModel",
    "UserParameterGroupModel",
    "UserParameterModel",
]


class UserParameterModel(AbstractValueModel):
    def __init__(self, parameter: Parameter):
        super().__init__()
        self._parameter = parameter
        self._value = None

    @property
    def parameter(self) -> Parameter:
        return self._parameter

    @property
    def display_name(self) -> str:
        return self._parameter.display_name

    @property
    def default_value(self) -> T:
        return self._parameter.assigned_value

    @property
    def assigned_value(self) -> T:
        return self._value if self._value is not None else self.default_value

    @property
    def enum_values(self) -> tuple[str, ...] | None:
        return self._parameter.enum_values

    @property
    def updated(self) -> bool:
        return self.assigned_value != self.default_value

    @property
    def override(self) -> Parameter:
        return UserParameter(parameter=self.parameter, assigned_value=self.assigned_value)

    @assigned_value.setter
    def assigned_value(self, value: T) -> None:
        if value != self._value:
            self._value = value
            self._value_changed()


class IntUserParameterModel(UserParameterModel):
    @property
    def type(self) -> ParameterType:
        return ParameterType.INT

    def set_value(self, value: str) -> None:
        with suppress(ValueError):
            self.assigned_value = int(value)

    def get_value_as_int(self) -> int:
        return self.assigned_value


class FloatUserParameterModel(UserParameterModel):
    @property
    def type(self) -> ParameterType:
        return ParameterType.FLOAT

    def set_value(self, value: str) -> None:
        with suppress(ValueError):
            self.assigned_value = float(value)

    def get_value_as_float(self) -> float:
        return self.assigned_value


class EnumUserParameterModel(UserParameterModel):
    @property
    def type(self) -> ParameterType:
        return ParameterType.ENUM

    def set_value(self, value: int) -> None:
        try:
            self.assigned_value = self.enum_values[value]
        except IndexError:
            self.assigned_value = self.default_value

    def get_value_as_int(self) -> int:
        try:
            return self.enum_values.index(self.assigned_value)
        except ValueError:
            return self.enum_values.index(self.default_value)


class BoolUserParameterModel(UserParameterModel):
    @property
    def type(self) -> ParameterType:
        return ParameterType.BOOL

    def set_value(self, value: bool) -> None:
        self.assigned_value = value

    def get_value_as_bool(self) -> bool:
        return self.assigned_value


class EnumerationItem(AbstractItem):
    def __init__(self, value: str):
        super().__init__()
        self.model = SimpleStringModel(value)


class EnumerationValueModel(AbstractItemModel):
    def __init__(self, model: UserParameterModel):
        super().__init__()
        self._model = model
        self._subscription = self._model.subscribe_value_changed_fn(lambda _: self._item_changed(None))
        self._items = [EnumerationItem(value) for value in self._model.enum_values]

    def get_item_children(self, item):
        if item is None:
            return self._items
        return []

    def get_item_value_model(self, item, _):
        if item is None:
            return self._model
        return item.model


class UserParameterGroupModel(OptionGroup):
    def __init__(self, requirement: Requirement):
        super().__init__(
            f"{requirement.display_name or requirement.code}@{requirement.version}",
        )


class ParametersModel(OptionsModel):

    def __init__(self):
        super().__init__()
        self._subscription = add_registry_requirement_callback(self.initialize)

    def initialize(self) -> None:
        self.clear()
        for requirement in RequirementsRegistry():
            if len(getattr(requirement, "parameters", [])) == 0:
                continue
            parameter_group_model = UserParameterGroupModel(requirement)
            for parameter in requirement.parameters:
                parameter_model: UserParameterModel
                match parameter.type:
                    case ParameterType.INT:
                        parameter_model = IntUserParameterModel(parameter)
                    case ParameterType.FLOAT:
                        parameter_model = FloatUserParameterModel(parameter)
                    case ParameterType.BOOL:
                        parameter_model = BoolUserParameterModel(parameter)
                    case ParameterType.ENUM:
                        parameter_model = EnumUserParameterModel(parameter)
                    case _:
                        continue
                parameter_group_model.append(parameter_model)
            self.append(parameter_group_model)
