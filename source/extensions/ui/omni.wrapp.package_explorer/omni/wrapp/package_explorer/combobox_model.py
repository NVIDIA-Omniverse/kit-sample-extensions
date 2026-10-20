# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import weakref
from typing import Any, List, Optional

import omni.ui as ui


class ComboBoxItem(ui.AbstractItem):
    def __init__(self, text: str, value: Any) -> None:
        super().__init__()
        self.model = ui.SimpleStringModel(text)
        self.value = value


class ComboBoxModel(ui.AbstractItemModel):
    """
    The model used for combobox
    Args:
        texts (List[str]): Texts displayed in combobox
    kwargs:
        values (Optional[List[Any]]): Values for combobox list. Default None to use text as value
        current_value (Any): Current value displayed in combobox. Default None to use first one.
    """

    def __init__(self, texts: List[str], values: Optional[List[Any]] = None, current_value: Any = None):
        super().__init__()

        # List items
        self._items = []
        values_list = values or []
        for index, text in enumerate(texts):
            value = values_list[index] if index < len(values_list) else text
            self._items.append(ComboBoxItem(text, value))

        # Current value
        current = self._get_current_index_by_value(current_value)
        self.current_index = ui.SimpleIntModel(current)
        self._sub = self.current_index.subscribe_value_changed_fn(
            lambda _, this=weakref.proxy(self): this.on_current_changed()
        )

    def destroy(self):
        self._sub = None
        self.current_index = None
        self._items = []

    @property
    def current_value(self) -> Optional[Any]:
        if not self.current_index:
            return None
        items = self.get_item_children(None)
        if not items:
            return None
        current_index = self.current_index.as_int
        if current_index < 0 or current_index >= len(items):
            return None
        return items[current_index].value

    @current_value.setter
    def current_value(self, value: Any) -> None:
        if not self.current_index:
            return
        items = self.get_item_children(None)
        if not items:
            return
        index = self._get_current_index_by_value(value, default=self.current_index.as_int)
        self.current_index.set_value(index)

    def get_item_children(self, item) -> List[ComboBoxItem]:
        return self._items

    def get_item_value_model(self, item, column_id):
        if item is None:
            return self.current_index
        if isinstance(item, ComboBoxItem):
            return item.model
        else:
            return ui.SimpleStringModel("Unknown")

    def on_current_changed(self):
        current_index = self.current_index.as_int
        items = self.get_item_children(None)
        if not items or current_index < 0 or current_index >= len(items):
            return
        self._on_current_item_changed(items[current_index])

        self._item_changed(None)

    def _get_current_index_by_value(self, value: Any, default: int = 0) -> int:
        items = self.get_item_children(None)
        if not items:
            return default

        if default < 0 or default >= len(items):
            default = 0

        if value is None:
            return default

        def normalize_list(v: Any) -> Any:
            if isinstance(v, (list, tuple)):
                return tuple(v)
            return v

        def is_numeric(v: Any) -> bool:
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        value = normalize_list(value)

        if is_numeric(value):
            current = next(
                (i for i, item in enumerate(items) if is_numeric(item.value) and abs(item.value - value) < 0.0001),
                default,
            )
            return current

        current = next(
            (i for i, item in enumerate(items) if normalize_list(item.value) == value),
            default,
        )
        return current  # noqa: R504

    def _on_current_item_changed(self, item: ComboBoxItem) -> None:
        pass
