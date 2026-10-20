# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass

import omni.kit.test
from omni.asset_validator.core import Parameter, ParameterType
from omni.asset_validator.ui import (
    BoolUserParameterModel,
    EnumerationValueModel,
    EnumUserParameterModel,
    FloatUserParameterModel,
    IntUserParameterModel,
    ParametersModel,
    ParametersWidget,
)
from omni.kit import ui_test
from omni.ui import CheckBox, ComboBox, FloatField, IntField, Window


@dataclass(frozen=True)
class _Parameter(Parameter):
    display_name: str
    type: ParameterType
    assigned_value: int | bool | float | str | None
    enum_values: tuple[str, ...] | None = None


class IntUserParameterModelTest(omni.kit.test.AsyncTestCase):
    async def test_int_field_ok(self):
        parameter = _Parameter(
            display_name="test_int_param",
            type=ParameterType.INT,
            assigned_value=17,
            enum_values=None,
        )
        model = IntUserParameterModel(parameter=parameter)
        window = Window("TestIntUserParameterModelWindow")
        with window.frame:
            field = IntField(model)
            await ui_test.human_delay()
            self.assertEqual(field.model.as_int, model.assigned_value)

            field.model.as_int = 42
            await ui_test.human_delay()
            self.assertEqual(field.model.as_int, model.assigned_value)

            model.as_int = 123
            await ui_test.human_delay()
            self.assertEqual(field.model.as_int, model.assigned_value)


class FloatUserParameterModelTest(omni.kit.test.AsyncTestCase):
    async def test_float_field_ok(self):
        parameter = _Parameter(
            display_name="test_float_param",
            type=ParameterType.FLOAT,
            assigned_value=3.14,
            enum_values=None,
        )
        model = FloatUserParameterModel(parameter=parameter)
        window = Window("TestFloatUserParameterModelWindow")
        with window.frame:
            field = FloatField(model)
            await ui_test.human_delay()
            self.assertEqual(field.model.as_float, model.assigned_value)

            field.model.as_float = 2.71
            await ui_test.human_delay()
            self.assertEqual(field.model.as_float, model.assigned_value)

            model.as_float = 1.618
            await ui_test.human_delay()
            self.assertEqual(field.model.as_float, model.assigned_value)


class BoolUserParameterModelTest(omni.kit.test.AsyncTestCase):
    async def test_checkbox_ok(self):
        parameter = _Parameter(
            display_name="test_bool_param",
            type=ParameterType.BOOL,
            assigned_value=True,
            enum_values=None,
        )
        model = BoolUserParameterModel(parameter=parameter)
        window = Window("TestBoolUserParameterModelWindow")
        with window.frame:
            checkbox = CheckBox(model)
            await ui_test.human_delay()
            self.assertEqual(checkbox.model.as_bool, model.assigned_value)

            checkbox.model.as_bool = False
            await ui_test.human_delay()
            self.assertEqual(checkbox.model.as_bool, model.assigned_value)

            model.as_bool = True
            await ui_test.human_delay()
            self.assertEqual(checkbox.model.as_bool, model.assigned_value)


class EnumUserParameterModelTest(omni.kit.test.AsyncTestCase):
    async def test_combobox_ok(self):
        parameter = _Parameter(
            display_name="test_enum_param",
            type=ParameterType.ENUM,
            assigned_value="medium",
            enum_values=("small", "medium", "large"),
        )
        model = EnumUserParameterModel(parameter=parameter)
        enum_model = EnumerationValueModel(model)
        window = Window("TestEnumUserParameterModelWindow")
        with window.frame:
            ComboBox(enum_model)
            await ui_test.human_delay()
            self.assertEqual(model.assigned_value, "medium")

            model.set_value(2)
            await ui_test.human_delay()
            self.assertEqual(model.assigned_value, "large")

            model.set_value(0)
            await ui_test.human_delay()
            self.assertEqual(model.assigned_value, "small")


class ParametersModelTest(omni.kit.test.AsyncTestCase):

    async def test_init(self):
        model = ParametersModel()
        self.assertGreater(len(model), 0)

        for parameter in model:
            print(parameter.name)
            self.assertGreater(len(parameter), 0)


class ParametersWidgetTest(omni.kit.test.AsyncTestCase):

    async def test_widget_creation(self):
        model = ParametersModel()

        window = Window("TestParametersWindow")
        with window.frame:
            ParametersWidget(model)
            await ui_test.human_delay()
