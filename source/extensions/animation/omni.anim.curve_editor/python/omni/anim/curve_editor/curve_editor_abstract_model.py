import weakref

import omni.usd
from omni import ui


class SelectionKeyValueModel(ui.AbstractValueModel):
    def __init__(self, parent_view):
        super().__init__()
        self._parent_view_wp = weakref.ref(parent_view)
        self._value = 0.0
        self._edit_value = 0.0
        self._selected = False

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_selection_value(self._value)

    def _get_curve_editor_view(self):
        return self._parent_view_wp()

    def set_selected_value(self, s: bool, value: float):
        self._selected = s
        self._value = value
        # Tell the widget that the model is changed
        self._value_changed()

    ## AbstractValueModel interfaces
    #

    def get_value_as_string(self):
        if self._selected:
            return str("{:.2f}".format(self._value))
        else:
            return ""

    def get_value_as_float(self):
        return self._value

    def begin_edit(self):
        self._edit_value = self._value

    def set_value(self, value):
        try:
            v = float(value)
        except ValueError:
            v = self._value
        self._edit_value = v

    def end_edit(self):
        if self._value != self._edit_value:
            self._value = self._edit_value
            self.update_ui()
            # Tell the widget that the model is changed
            self._value_changed()


class SelectionKeyTimeModel(ui.AbstractValueModel):
    def __init__(self, parent_view):
        super().__init__()
        self._parent_view_wp = weakref.ref(parent_view)
        self._time = 0.0
        self._edit_time = 0.0
        self._selected = False

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_selection_time(self._time)

    def _get_curve_editor_view(self):
        return self._parent_view_wp()

    def set_selected_time(self, s: bool, time: float):
        self._selected = s
        self._time = time
        # Tell the widget that the model is changed
        self._value_changed()

    ## AbstractValueModel interfaces
    #

    def get_value_as_string(self):
        if self._selected:
            return str("{:.2f}".format(self._time))
        else:
            return ""

    def get_value_as_float(self):
        return self._time

    def begin_edit(self):
        self._edit_time = self._time

    def set_value(self, time):
        try:
            t = float(time)
        except ValueError:
            t = self._time
        self._edit_time = t

    def end_edit(self):
        if self._time != self._edit_time:
            self._time = self._edit_time
            self.update_ui()
            # Tell the widget that the model is changed
            self._value_changed()


class RadioButtonSelectionModel(ui.SimpleIntModel):
    def __init__(self, parent_view):
        super().__init__()
        self._parent_view_wp = weakref.ref(parent_view)

        self.set_value_none()

    def _get_curve_editor_view(self):
        return self._parent_view_wp()

    def set_value_none(self):
        self.set_value(-1)

    # change the widget value, then update curve tangent type.
    def command_set_value(self, value):
        if self.get_value_as_int() == -1:
            # here, in the no_selection status. It is conceptually hidden, so skip.
            return
        else:
            self.set_value(value)
            self.update_ui()


class RadioButtonInTangentTypeModel(RadioButtonSelectionModel):
    def __init__(self, parent_view):
        super().__init__(parent_view)

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_in_tangent_type(self.get_value_as_int())


class RadioButtonOutTangentTypeModel(RadioButtonSelectionModel):
    def __init__(self, parent_view):
        super().__init__(parent_view)

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_out_tangent_type(self.get_value_as_int())


class RadioButtonTangentBrokenModel(RadioButtonSelectionModel):
    def __init__(self, parent_view):
        super().__init__(parent_view)

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_tangent_broken(self.get_value_as_int() != 0)


class RadioButtonTangentWeightedModel(RadioButtonSelectionModel):
    def __init__(self, parent_view):
        super().__init__(parent_view)

    def update_ui(self):
        if self._get_curve_editor_view():
            self._get_curve_editor_view().command_set_tangent_weighted(self.get_value_as_int() != 0)


class KeyMovementDirectionItem(ui.AbstractItem):
    def __init__(self, text: str):
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class KeyMovementDirectionModel(ui.AbstractItemModel):
    def __init__(self, parent_view):
        super().__init__()
        self._parent_view_wp = weakref.ref(parent_view)
        self._items = [KeyMovementDirectionItem(text) for text in ["Free", "Vertical", "Horizontal"]]
        self._init_current_index()
        self.add_item_changed_fn(self._on_key_movement_direction_change)

    def update_ui(self):
        if self._get_curve_editor_view():
            index = self.get_item_value_model().get_value_as_int()
            self._get_curve_editor_view().command_set_key_movement_direction(index)

    def _on_key_movement_direction_change(self, model, item):
        # model is equal to self
        # it seems that item is not usable and always is None

        self.update_ui()

    # standard routine to make combo work
    def _init_current_index(self):
        self._current_index = ui.SimpleIntModel(0)
        self._current_index.add_value_changed_fn(lambda a: self._item_changed(None))

    def _get_curve_editor_view(self):
        return self._parent_view_wp()

    ## AbstractItemModel interfaces
    #

    def get_item_value_model(self, item=None, column_id=0):
        if item is None:
            return self._current_index
        return item.model

    def get_item_children(self, item):
        return self._items
