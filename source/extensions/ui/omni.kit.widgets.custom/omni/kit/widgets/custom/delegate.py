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


class AbstractValueModeldelegate:
    def __init__(self):
        pass

    def get_value_model(self, value, value_type=None):
        if value_type is None:
            value_type = type(value)
        if value_type == str or value_type == "string":
            return ui.SimpleStringModel(value)
        elif value_type == int or value_type == "int":
            return ui.SimpleIntModel(int(value))
        elif value_type == float or value_type == "float":
            return ui.SimpleFloatModel(float(value))
        elif value_type == bool or value_type == "bool":
            return ui.SimpleBoolModel(float(value))
        else:
            carb.log_error("Unknow value type {value_type}!")
            return None


class AbstractWidgetDelegate:
    def __init__(self):
        pass

    def create_widget(self, value, *args, **kwargs):
        return None

    def set_value(self, value):
        pass

    def get_value(self):
        return None


class LabelDelegate(AbstractWidgetDelegate):
    def __init__(self, alignment=ui.Alignment.LEFT):
        self._alignment = alignment

    def create_widget(self, value, *args, **kwargs):
        self._label = ui.Label(value, *args, **kwargs)
        return self._label

    def set_value(self, value):
        self._label.text = value

    def get_value(self):
        return self._label.text


class ComboboxLabelDelegate(LabelDelegate):
    def __init__(self):
        pass

    def create_widget(self, value, *args, **kwargs):
        padding_y = kwargs.get("padding_y", 0)
        padding_x = kwargs.get("padding_x", 0)
        # Same value from CustomWidgetComboBox
        arrow_size = kwargs.get("arrow_size", 12)
        arrow_padding_x = kwargs.get("arrow_padding_x", 6)
        arrow_padding_y = kwargs.get("arrow_padding_y", 4)
        with ui.VStack():
            ui.Spacer(height=padding_y)
            with ui.HStack():
                ui.Spacer(width=padding_x)
                self._label = ui.Label(value, *args, **kwargs)
                ui.Spacer(width=arrow_size + arrow_padding_x + padding_x)
            ui.Spacer(height=padding_y)
        return self._label

    def set_value(self, value):
        self._label.text = value

    def get_value(self):
        return self._label.text
