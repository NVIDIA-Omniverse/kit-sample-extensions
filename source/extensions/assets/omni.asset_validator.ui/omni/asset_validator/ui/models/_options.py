# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections import defaultdict
from enum import IntEnum
from typing import Any

from omni.ui import AbstractItem, AbstractItemModel, AbstractValueModel, SimpleStringModel

__all__ = [
    "OptionGroup",
    "OptionItem",
    "OptionMode",
    "OptionModeModel",
    "OptionModel",
    "OptionsItemModel",
    "OptionsModel",
]


class OptionMode(IntEnum):
    CATEGORIES = 0
    """
    View categories to perform validation.
    """
    CAPABILITIES = 1
    """
    View capabilities to perform validation.
    """
    FEATURES = 2
    """
    View features to perform validation.
    """
    PARAMETERS = 3
    """
    View parameters to perform validation.
    """
    PROFILES = 4
    """
    View profiles to perform validation.
    """


class OptionModeModel(SimpleStringModel):
    def __init__(self) -> None:
        super().__init__(OptionMode.CATEGORIES.name)

    @property
    def mode(self) -> OptionMode:
        return OptionMode[self.get_value_as_string()]

    @mode.setter
    def mode(self, mode: OptionMode) -> None:
        self.set_value(mode.name)


class OptionModel(AbstractValueModel):
    """
    Option model. Consist of value and its properties.
    """

    def __init__(
        self,
        value: Any,
        name: str,
        description: str | None = None,
        url: str | None = None,
        selected: bool | None = False,
        enabled: bool | None = True,
    ):
        super().__init__()
        self._value = value
        self._name = name
        self._description = description or ""
        self._url = url or ""
        self._selected = selected
        self._enabled = enabled

    @property
    def value(self) -> Any:
        return self._value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def url(self) -> str:
        return self._url

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value) -> None:
        if self.enabled:
            self._selected = value
            self._value_changed()

    def set_value(self, value: bool) -> None:
        self.selected = value

    def get_value_as_bool(self) -> bool:
        return self.selected


class OptionGroup:
    def __init__(self, name: str, url: str | None = None, options: list[OptionModel] | None = None):
        self._name = name
        self._url = url
        self._options = options or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def url(self) -> str | None:
        return self._url

    def __len__(self):
        return len(self._options)

    def __getitem__(self, item):
        return self._options[item]

    def append(self, option: OptionModel) -> None:
        self._options.append(option)

    def get(self, value) -> OptionModel | None:
        for option in self:
            if option.value == value:
                return option
        return None


class OptionsModel:
    def __init__(self, groups: list[OptionGroup] | None = None):
        self._groups = groups or []
        self.initialize()

    def initialize(self) -> None: ...

    def reset(self) -> None: ...

    def __len__(self):
        return len(self._groups)

    def __getitem__(self, item):
        return self._groups[item]

    def clear(self) -> None:
        self._groups.clear()

    def append(self, group: OptionGroup) -> None:
        self._groups.append(group)

    def get(self, value) -> OptionModel | None:
        for group in self:
            if option := group.get(value):
                return option
        return None


class OptionItem(AbstractItem):
    """
    An item with OptionModel.
    """

    def __init__(self, model: OptionModel | OptionGroup):
        super().__init__()
        self._model = model

    @property
    def model(self) -> OptionModel | OptionGroup:
        return self._model


class OptionsItemModel(AbstractItemModel):
    """
    The model for OptionsWidget. The input is a generic data tree.
    """

    def __init__(self, model: OptionsModel):
        super().__init__()

        self._item_to_children = defaultdict(list)
        for value in model:
            item = OptionItem(value)
            self._item_to_children[None].append(item)
            for child in value:
                child_item = OptionItem(child)
                self._item_to_children[item].append(child_item)

    def get_item_children(self, item: AbstractItem | None) -> list[AbstractItem]:
        """Override"""
        return self._item_to_children[item]

    def get_item_value_model(self, item: AbstractItem | None, *_):
        """Override"""
        return item.model
