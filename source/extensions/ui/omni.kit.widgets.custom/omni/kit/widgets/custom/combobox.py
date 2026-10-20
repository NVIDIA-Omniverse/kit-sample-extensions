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

from .button import InvisibleButton
from .constant import DarkColors, LightColors
from .delegate import AbstractValueModeldelegate, ComboboxLabelDelegate
from .menu import CustomComboBoxDroplist, CustomMenu
from .model import IndexModelManager, SimpleComboboxModel
from .style import get_ui_style


class ComboBoxEx(ui.ComboBox, IndexModelManager):
    def __init__(self, *args, **kwargs):
        self._model = SimpleComboboxModel(*args, **kwargs)
        ui.ComboBox.__init__(self, self._model, **kwargs)
        IndexModelManager.__init__(self, self._model)

    def _create_value_model(self, value):
        return ui.SimpleStringModel(value)


class SpaceStringModel(ui.SimpleStringModel):
    """
    String Model allow to add prefix spaces
    """

    def __init__(self, value, num_spaces=2):
        self._num_spaces = num_spaces
        value = self._add_spaces(value)
        super().__init__(value)

    @property
    def real_value(self):
        value = self.get_value_as_string()
        return value[self._num_spaces :]

    def get_value_as_string(self):
        value = super().get_value_as_string()
        return value

    def set_value(self, value):
        super().set_value(self._add_spaces(value))

    def _add_spaces(self, value):
        return " " * self._num_spaces + value


class SpaceModelDelegate(AbstractValueModeldelegate):
    def __init__(self, num_spaces=2):
        self._num_spaces = num_spaces

    def get_value_model(self, value, value_type=None):
        if value_type is None:
            value_type = type(value)
        if value_type == str or value_type == "string":
            return SpaceStringModel(value, num_spaces=self._num_spaces)
        else:
            return super().get_value_model(value, value_type)


class SpaceComboBox(ComboBoxEx):
    def __init__(self, *args, **kwargs):
        self._delegate = SpaceModelDelegate(kwargs.get("num_spaces", 2))
        super().__init__(*args, delegate=self._delegate, **kwargs)

    @property
    def values(self):
        items = self.model.get_item_children()
        values = []
        for item in items:
            value_model = self.model.get_item_value_model(item)
            values.append(value_model.real_value)
        return values

    def _get_value(self, value_model):
        return value_model.get_value_as_string().lstrip()


class CustomWidgetComboBox(IndexModelManager):
    LIGHT_STYLE = {
        "Triangle": {"background_color": LightColors.Text},
        "Triangle:disabled": {"background_color": LightColors.TextDisabled},
    }
    DARK_STYLE = {
        "Triangle": {"background_color": DarkColors.Text},
        "Triangle:disabled": {"background_color": DarkColors.TextDisabled},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(self, *args, arrow_size=12, alignment=ui.Alignment.LEFT, **kwargs):
        self._model = SimpleComboboxModel(*args, **kwargs)
        super().__init__(self._model)

        self._menu = None
        self._delegate = kwargs.get("item_delegate", None)
        if self._delegate is None:
            carb.log_error("Delegate not defined!")
            return

        self._enabled = True
        self._alignment = alignment
        self._padding_x = kwargs.get("padding_x", 8)
        self._padding_y = kwargs.get("padding_y", 4)
        self._arrow_size = kwargs.get("arrow_size", 12)
        self._arrow_padding_x = kwargs.get("arrow_padding_x", 8)
        self._arrow_padding_y = kwargs.get("arrow_padding_y", 4)

        self._droplist_delegate = kwargs.get("droplist_delegate", ComboboxLabelDelegate())
        self._droplist_width = kwargs.get("droplist_width", None)
        self._droplist_style = kwargs.get("droplist_style", None)
        self._droplist_padding_x = kwargs.get("droplist_padding_x", self._padding_x)
        self._droplist_padding_y = kwargs.get("droplist_padding_y", self._padding_y)

        self._build_ui(**kwargs)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self._button.enabled = value
        self._arrow.enabled = value

    def _build_ui(self, **kwargs):
        self._value = self._model.current_model.as_string if self._model.current_model else ""
        width = kwargs.get("width", None)
        height = kwargs.get("height", None)
        stack_kwargs = {}
        if width is not None:
            stack_kwargs["width"] = width
        if height is not None:
            stack_kwargs["height"] = height

        style = self.UI_STYLES[get_ui_style()]
        with ui.ZStack(**stack_kwargs):
            self._background_rect = ui.Rectangle(style_type_name_override="ComboBox", **stack_kwargs)
            with ui.VStack(**stack_kwargs):
                ui.Spacer(height=self._padding_y)
                with ui.HStack(style=style):
                    ui.Spacer(width=self._padding_x)
                    self._delegate.create_widget(
                        self._value,
                        arrow_size=self._arrow_size,
                        arrow_padding_x=self._arrow_padding_x,
                        arrow_padding_y=self._arrow_padding_y,
                        style_type_name_override="ComboBox",
                        alignment=self._alignment,
                    )
                    with ui.HStack(width=self._arrow_size + self._arrow_padding_x):
                        ui.Spacer(width=self._arrow_padding_x)
                        with ui.VStack(width=self._arrow_size):
                            ui.Spacer()
                            self._arrow = ui.Triangle(
                                width=self._arrow_size, height=self._arrow_size, alignment=ui.Alignment.CENTER_BOTTOM
                            )
                            ui.Spacer()
                    ui.Spacer(width=self._padding_x)
                ui.Spacer(height=self._padding_y)
            self._button = InvisibleButton(clicked_fn=self._on_show_list)

    @IndexModelManager.current_index.setter
    def current_index(self, value):
        super(CustomWidgetComboBox, CustomWidgetComboBox).current_index.__set__(self, value)
        # Update combobox label
        self._on_selection_changed(self._model.current_index)

    def insert(self, value, value_type=None):
        super().insert(value, value_type=value_type)
        # Force to update droplist
        self._menu = None

    def remove(self, index=None):
        index = super().remove(index=index)
        # Update combobox label
        self._on_selection_changed(self._model.current_index)
        # Force to update droplist
        self._menu = None

        return index

    def clear(self):
        super().clear()
        # Update combobox label
        self._on_selection_changed(self._model.current_index)
        # Force to update droplist
        self._menu = None

    def _on_show_list(self):
        if self._menu is None:
            kwargs = {}
            if self._droplist_style is not None:
                kwargs["style"] = self._droplist_style
            self._menu = CustomComboBoxDroplist(
                self._model.string_values,
                width=(
                    self._background_rect.computed_content_width
                    if self._droplist_width is None
                    else self._droplist_width
                ),
                selection=self._model.current_index,
                on_selection_changed_fn=self._on_selection_changed,
                alignment=self._alignment,
                delegate=self._droplist_delegate,
                padding_x=self._droplist_padding_x,
                padding_y=self._droplist_padding_y,
                arrow_size=self._arrow_size,
                arrow_padding_x=self._arrow_padding_x,
                arrow_padding_y=self._arrow_padding_y,
                **kwargs,
            )
        else:
            self._menu.selection = self._model.current_index
            self._menu.width = self._background_rect.computed_content_width
        self._menu.show_at(self._background_rect, ui.Alignment.BOTTOM)
        return

    def _on_selection_changed(self, index):
        self._model.current_index = index
        self._delegate.set_value(self._model.current_model.as_string if self._model.current_model else "")
