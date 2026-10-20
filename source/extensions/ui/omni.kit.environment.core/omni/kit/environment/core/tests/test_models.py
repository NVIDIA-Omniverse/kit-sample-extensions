# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import carb
import omni.kit.commands as cmd
import omni.kit.test
import omni.kit.undo
import omni.usd
from omni.kit.environment.core import ENVIRONMENT_PRIM_ROOT
from omni.kit.test import AsyncTestCase
from pxr import Sdf, UsdGeom

from ..models import CityModel, PropertyValueModel, SettingModel, UsdModelBuilder


class TestModels(AsyncTestCase):
    async def setUp(self):
        self.usd_context_name = ""
        self.usd_context = omni.usd.get_context(self.usd_context_name)
        await self.usd_context.new_stage_async()
        self.stage = self.usd_context.get_stage()

        self.stage.SetDefaultPrim(UsdGeom.Xform.Define(self.stage, "/World").GetPrim())

    async def tearDown(self):
        self.usd_context = None
        self.stage = None

    def get_setting_path(self, setting):
        return f"/app/test/omni.kit.viewport.menubar.core/test_root/{setting}"

    async def test_setting_model_bool(self):
        setting = self.get_setting_path("bool_value")
        settings = carb.settings.get_settings()
        settings.set(setting, True)
        model = SettingModel(setting)

        # Should start as None and False
        self.assertEqual(model.get_value_as_bool(), bool(settings.get(setting)))

        # Test model -> carb.setting
        model.set_value(True)
        self.assertEqual(model.get_value_as_bool(), settings.get(setting))

        model.set_value(False)
        self.assertEqual(model.get_value_as_bool(), settings.get(setting))

        # Test carb.setting -> model
        settings.set(setting, True)
        self.assertEqual(model.get_value_as_bool(), settings.get(setting))

        settings.set(setting, False)
        self.assertEqual(model.get_value_as_bool(), settings.get(setting))

    async def test_setting_model_int(self):
        setting = self.get_setting_path("int_value")
        settings = carb.settings.get_settings()
        model = SettingModel(setting)

        # Test model -> carb.setting
        model.set_value(1)
        self.assertEqual(model.get_value_as_int(), settings.get(setting))

        model.set_value(2)
        self.assertEqual(model.get_value_as_int(), settings.get(setting))

        # Test carb.setting -> model
        settings.set(setting, 3)
        self.assertEqual(model.get_value_as_int(), settings.get(setting))

        settings.set(setting, 4)
        self.assertEqual(model.get_value_as_int(), settings.get(setting))

    async def test_setting_model_float(self):
        setting = self.get_setting_path("float_value")
        settings = carb.settings.get_settings()
        model = SettingModel(setting)

        # Test model -> carb.setting
        model.set_value(123.0)
        self.assertEqual(model.get_value_as_float(), settings.get(setting))

        model.set_value(456.0)
        self.assertEqual(model.get_value_as_float(), settings.get(setting))

        # Test carb.setting -> model
        settings.set(setting, 789.0)
        self.assertEqual(model.get_value_as_float(), settings.get(setting))

        settings.set(setting, 101112.0)
        self.assertEqual(model.get_value_as_float(), settings.get(setting))

    async def test_setting_model_string(self):
        setting = self.get_setting_path("string_value")
        settings = carb.settings.get_settings()
        model = SettingModel(setting)

        # Test model -> carb.setting
        model.set_value("A")
        self.assertEqual(model.get_value_as_string(), settings.get(setting))

        model.set_value("B")
        self.assertEqual(model.get_value_as_string(), settings.get(setting))

        # Test carb.setting -> model
        settings.set(setting, "C")
        self.assertEqual(model.get_value_as_string(), settings.get(setting))

        settings.set(setting, "D")
        self.assertEqual(model.get_value_as_string(), settings.get(setting))

        self.assertFalse(model._editing)
        model.begin_edit()
        self.assertTrue(model._editing)
        model.end_edit()
        self.assertFalse(model._editing)

        def __on_value_changed(_):
            pass  # pragma: no cover

        sub = model.add_value_changed_fn(__on_value_changed)
        model.remove_value_changed_fn(sub)

    async def test_city_model(self):
        model = CityModel()
        model.current_index = 0
        self.assertEqual(model.current_index, 0)

        model.set_location(0, 0)
        self.assertEqual(model.current_index, 0)
        model.set_location(4.8901, 52.3611)
        self.assertEqual(model.current_index, 2)

        self.assertEqual(model.get_item_value_model_count(), 1)
        index_model = model.get_item_value_model(None)
        self.assertEqual(index_model.as_int, model.current_index)
        items = model.get_item_children(None)
        name = model.get_item_value_model(items[2], 0)
        self.assertEqual(name.as_string, "Amsterdam")
        long = model.get_item_value_model(items[2], 1)
        self.assertAlmostEqual(long.as_float, 4.8901)
        lat = model.get_item_value_model(items[2], 2)
        self.assertAlmostEqual(lat.as_float, 52.3611)

    async def test_prim_model(self):
        cube_path = "/World/Cube"
        model = UsdModelBuilder().create_prim_value_model(cube_path)
        self.assertFalse(model.as_bool)

        self.create_test_object(cube_path, position=(100, 0, 0))
        self.assertTrue(model.as_bool)

        model.on_prim_changed(None)
        self.assertFalse(model.as_bool)

    async def test_property_model_bool(self):
        property_path = "/World/Cube.singleSided"
        model = PropertyValueModel(property_path, self.stage, value_type=Sdf.ValueTypeNames.Bool, default=False)
        self.assertFalse(model.as_bool)
        model.set_value(True)
        property = self.stage.GetPropertyAtPath(property_path)
        self.assertTrue(property.Get())
        model.set_value(False)
        self.assertFalse(property.Get())

    async def test_property_model_int(self):
        property_path = f"{ENVIRONMENT_PRIM_ROOT}/Cube.testInt"
        model = PropertyValueModel(
            property_path, self.stage, value_type=Sdf.ValueTypeNames.Int, default=0, default_prim_type="Xform"
        )
        self.assertEqual(model.as_int, 0)
        model.set_value(1)
        property = self.stage.GetPropertyAtPath(property_path)
        self.assertEqual(property.Get(), 1)
        model.set_value(2)
        self.assertEqual(property.Get(), 2)

    async def test_property_model_float(self):
        property_path = f"{ENVIRONMENT_PRIM_ROOT}/Cube.testFloat"
        model = PropertyValueModel(
            property_path,
            self.stage,
            value_type=Sdf.ValueTypeNames.Float,
            default=5.0,
            min=-10,
            max=10,
            default_prim_type="Xform",
        )
        self.assertEqual(model.as_float, 5)
        model.set_value(15)
        property = self.stage.GetPropertyAtPath(property_path)
        self.assertEqual(property.Get(), 10)
        model.set_value(-20)
        self.assertEqual(property.Get(), -10)

    def create_test_object(self, prim_path, prim_type="Cube", position=(0, 0, 0)):
        kwargs = {"prim_type": prim_type, "prim_path": prim_path, "attributes": {"size": 100.0}}

        cmd.execute("CreatePrimWithDefaultXform", **kwargs)

        prim = self.stage.GetPrimAtPath(prim_path)
        prim.GetAttribute("xformOp:translate").Set(position)
