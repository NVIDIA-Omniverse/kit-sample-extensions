# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from omni import ui

from .delegate import AbstractValueModeldelegate


class EditEventIntModel(ui.SimpleIntModel):
    """
    Int Model activate callback when editing is finished.
    """

    def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value=0):
        super().__init__(init_value)
        self._on_begin_edit_fn = on_begin_edit_fn
        self._on_end_edit_fn = on_end_edit_fn

    def begin_edit(self):
        if self._on_begin_edit_fn is not None:
            self._on_begin_edit_fn(self)

    def end_edit(self):
        if self._on_end_edit_fn is not None:
            self._on_end_edit_fn(self)


class EditEventFloatModel(ui.SimpleFloatModel):
    """
    Float Model activate callback when editing is started and finished.
    """

    def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value=0.0):
        super().__init__(init_value)
        self._on_begin_edit_fn = on_begin_edit_fn
        self._on_end_edit_fn = on_end_edit_fn

    def begin_edit(self):
        if self._on_begin_edit_fn is not None:
            self._on_begin_edit_fn(self)

    def end_edit(self):
        if self._on_end_edit_fn is not None:
            self._on_end_edit_fn(self)


class EditEventStringModel(ui.SimpleStringModel):
    """
    String Model activate callback when editing is started and finished.
    """

    def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value=""):
        super().__init__(init_value)
        self._on_begin_edit_fn = on_begin_edit_fn
        self._on_end_edit_fn = on_end_edit_fn

    def begin_edit(self):
        if self._on_begin_edit_fn is not None:
            self._on_begin_edit_fn(self)

    def end_edit(self):
        if self._on_end_edit_fn is not None:
            self._on_end_edit_fn(self)


class SimpleListItem(ui.AbstractItem):
    """Single item of list"""

    def __init__(self, values, delegate=None):
        super().__init__()

        if delegate is None:
            self._delegate = AbstractValueModeldelegate()
        else:
            self._delegate = delegate

        self._models = []

        if type(values) != list:
            values = [values]
        for value in values:
            data, data_type = self._get_data(value)
            value_model = self._delegate.get_value_model(data, data_type)
            if value_model:
                self._models.append(value_model)

    def get_value_model(self, index=0):
        if index >= len(self._models) or index < 0:
            return None
        return self._models[index]

    def _get_data(self, value):
        if type(value) == str:
            datas = value.split("##")
            if len(datas) == 2:
                return datas
            else:
                return (value, "string")
        else:
            return (value, None)

    def __repr__(self):
        return f'"{self._models[0].as_string}"'


class SimpleItemModel(ui.AbstractItemModel):
    """Represents item model"""

    def __init__(self, columns_count=1):
        self._columns_count = columns_count
        super().__init__()
        self._children = []

    @property
    def items(self):
        return self._children

    def insert_item(self, item, index=-1):
        """Insert item into list model"""
        if index < 0:
            self._children.append(item)
        else:
            self._children.insert(index, item)
        self._item_changed(None)

    def remove_item(self, item):
        index = self._children.index(item)
        self.remove_index(index)

    def remove_index(self, index):
        if index < 0 or index >= len(self._children):
            return

        del self._children[index]
        self._item_changed(None)

    def clear(self):
        """Clear all children"""
        self._children = []
        self._item_changed(None)

    def on_item_updated(self, item=None):
        self._item_changed(item)

    """Basic AbstractItemModel functions"""

    def get_item_children(self, item=None):
        """Returns all the children when the widget asks it."""
        if item is not None:
            return []

        return self._children

    def get_item_value_model_count(self, item=None):
        """The number of columns"""
        return self._columns_count

    def get_item_value_model(self, item=None, column_id=0):
        """Return value model for columns"""
        if item is None:
            return None
        return item.get_value_model(column_id)


class SimpleListModel(SimpleItemModel):
    """Represents lists"""

    def __init__(self, columns_count=1, enable_drag_drop=True):
        super().__init__(columns_count=columns_count)
        self._enable_drag_drop = enable_drag_drop

    """Enable drag and drop"""

    def get_drag_mime_data(self, item):
        """Returns Multipurpose Internet Mail Extensions (MIME) data for be able to drop this item somewhere"""
        # As we don't do Drag and Drop to the operating system, we return the string.
        return item.get_value_model(0).as_string

    def drop_accepted(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called to highlight target when drag and drop."""
        if not self._enable_drag_drop:
            return False
        else:
            # If target_item is None, it's the drop to root. Since it's
            # list model, we support reorganizetion of root only and we
            # don't want to create tree.
            return not target_item and drop_location >= 0

    def drop(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called when dropping something to the item."""
        try:
            source_id = self._children.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return

        if source_id == drop_location:
            # Nothing to do
            return

        self.remove_item(source)

        if drop_location > len(self._children):
            # Drop it to the end
            self.insert_item(source)
        else:
            if source_id < drop_location:
                # Becase when we removed source, the array became shorter
                drop_location = drop_location - 1

            self.insert_item(source, drop_location)

        self._item_changed(None)


class SimpleComboboxItem(ui.AbstractItem):
    def __init__(self, text):
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class SimpleComboboxModel(SimpleItemModel):
    """Represents combobox"""

    def __init__(self, *args, **kwargs):
        super().__init__(columns_count=1)

        current_index = -1
        if len(args) > 0:
            if type(args[0]) == int:
                current_index = args[0]
                args = args[1:]

        self._current_index = ui.SimpleIntModel(current_index)
        self._current_index.add_value_changed_fn(lambda a: self._item_changed(None))

        self._delegate = kwargs.get("delegate", None)
        for value in args:
            self.insert_value(value)

    def insert_value(self, value, value_type=None):
        self.insert_item(SimpleListItem(value, delegate=self._delegate))

    def get_item_value_model(self, item=None, column_id=0):
        if item is None:
            return self._current_index
        return item.get_value_model(column_id)

    @property
    def current_index(self):
        return self._current_index.as_int

    @current_index.setter
    def current_index(self, index):
        self._current_index.set_value(index)

    @property
    def current_model(self):
        children = self.get_item_children(None)
        if self.current_index < 0:
            return None
        else:
            return self.get_item_value_model(children[self.current_index])

    @property
    def string_values(self):
        children = self.get_item_children(None)
        values = []
        for child in children:
            values.append(child.get_value_model().as_string)
        return values


class ModelManager:
    def __init__(self, model):
        self.model = model

    @property
    def values(self):
        items = self.model.get_item_children()
        values = []
        for item in items:
            value_model = self.model.get_item_value_model(item)
            values.append(value_model.as_string)
        return values

    @property
    def values_count(self):
        return len(self.model.get_item_children())

    def reset(self, *args):
        self.clear()
        self._add_values(*args)

    def clear(self):
        self.current_index = -1
        while self.values_count > 0:
            self.model.remove_item(self.model.get_item_children()[0])

    def remove(self, index=None):
        if index is None:
            # remove current
            index = self.current_index
        if index >= 0:
            items = self.model.get_item_children()
            if index < len(items):
                self.model.remove_item(items[index])
                if index == self.current_index:
                    # Change current index
                    self.current_index = self.current_index - 1
                return index
        return -1

    def remove_selected(self):
        return self.remove(index=None)

    def insert(self, value, value_type=None):
        self.model.insert_value(value, value_type=value_type)

    def append(self, *args):
        self._add_values(*args)

    def _add_values(self, *args):
        for value in args:
            if isinstance(value, list):
                self._add_values(*value)
            else:
                self.insert(value)


class IndexModelManager(ModelManager):
    @property
    def current(self):
        return self.current_index

    @current.setter
    def current(self, value):
        self.current_index = value

    @property
    def current_index(self):
        current_index = self.model.get_item_value_model()
        return current_index.as_int

    @current_index.setter
    def current_index(self, value):
        current_index = self.model.get_item_value_model()
        current_index.set_value(value)

    @property
    def current_value(self):
        index = self.current_index
        if index < 0:
            return None

        values = self.values
        if index < len(values):
            return values[index]
        else:
            return None

    @current_value.setter
    def current_value(self, value):
        self.current_index = self.values.index(value)
