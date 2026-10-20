## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import os

import carb
import omni.ui as ui
from omni.kit.test.async_unittest import AsyncTestCase
from omni.ramp import *


class TestRamp(AsyncTestCase):
    async def test_ramp(self):
        filepath = os.path.split(__file__)[0].replace("\\", "/") + "/test.usda"
        context = omni.usd.get_context()
        if not context.open_stage(filepath):
            raise Exception("File not found:", filepath)
        stage = context.get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")
        self.assertNotEqual(prim, None)

        ramp = acquire_interface()

        value = ramp.get_float_at_position(0.5, "/ramp.positions", "/ramp.values", "/ramp.interpolations")
        self.assertEqual(value, 0.5)

        ramp.add_float_key(0.25, 0.75, 0, "/ramp.positions", "/ramp.values", "/ramp.interpolations")
        value = ramp.get_float_at_position(0.25, "/ramp.positions", "/ramp.values", "/ramp.interpolations")
        self.assertEqual(value, 0.75)

        value = ramp.get_float3_at_position(0.5, "/ramp.positions3", "/ramp.values3", "/ramp.interpolations3")
        self.assertEqual(value[0], 0)
        self.assertEqual(value[1], 1)
        self.assertEqual(value[2], 0)

        rgb = (0.75, 0.65, 0.55)
        ramp.add_float3_key(0.25, rgb, 0, "/ramp.positions3", "/ramp.values3", "/ramp.interpolations3")
        value = ramp.get_float3_at_position(0.25, "/ramp.positions3", "/ramp.values3", "/ramp.interpolations3")
        self.assertEqual(round(value[0], 2), rgb[0])
        self.assertEqual(round(value[1], 2), rgb[1])
        self.assertEqual(round(value[2], 2), rgb[2])

        release_interface(ramp)

    async def checkKeyEquality(self, rampWidget, default_positions, default_values, default_interpolations):
        self.assertFalse(len(rampWidget.key_positions) == 0)
        self.assertFalse(len(rampWidget.key_values) == 0)
        self.assertFalse(len(rampWidget.key_interps) == 0)

        self.assertTrue(len(rampWidget.key_positions) == len(rampWidget.default_key_positions))
        self.assertTrue(len(rampWidget.key_positions) == len(default_positions))
        self.assertTrue(len(rampWidget.key_values) == len(rampWidget.default_key_values))
        self.assertTrue(len(rampWidget.key_values) == len(default_values))
        self.assertTrue(len(rampWidget.key_interps) == len(rampWidget.default_key_interpolations))
        self.assertTrue(len(rampWidget.key_interps) == len(default_interpolations))

        for ramp_position, ramp_default_position, default_position in zip(
            rampWidget.key_positions, rampWidget.default_key_positions, default_positions
        ):
            self.assertAlmostEqual(ramp_position, default_position)
            self.assertAlmostEqual(ramp_position, ramp_default_position)

        for ramp_value, ramp_default_value, default_value in zip(
            rampWidget.key_values, rampWidget.default_key_values, default_values
        ):
            self.assertAlmostEqual(ramp_value, default_value)
            self.assertAlmostEqual(ramp_value, ramp_default_value)

        for ramp_interpolation, ramp_default_interpolation, default_interpolation in zip(
            rampWidget.key_interps, rampWidget.default_key_interpolations, default_interpolations
        ):
            self.assertAlmostEqual(ramp_interpolation, default_interpolation)
            self.assertAlmostEqual(ramp_interpolation, ramp_default_interpolation)

    async def test_widget(self):
        filepath = os.path.split(__file__)[0].replace("\\", "/") + "/test.usda"
        context = omni.usd.get_context()
        if not context.open_stage(filepath):
            raise Exception("File not found:", filepath)
        stage = context.get_stage()

        prim = stage.GetPrimAtPath("/ramp")
        self.assertNotEqual(prim, None)
        ramp = acquire_interface()
        window = ui.Window(
            "ramp widget",
            width=425,
            height=0,
            menu_path="window/ramp",
            dock=ui.DockPreference.LEFT_BOTTOM,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        default_positions = [0, 0.2, 1]
        default_values = [0, 0.3, 1]
        default_interpolations = [1, 1, 1]
        rampWidget = RampWidget(
            ramp,
            window.frame,
            prim,
            attr_names=["positions_empty", "values_empty", "interpolations_empty"],
            default_keys=[default_positions, default_values, default_interpolations],
        )

        # make sure that default values are created
        await self.checkKeyEquality(rampWidget, default_positions, default_values, default_interpolations)

        release_interface(ramp)

    async def test_widget3(self):
        filepath = os.path.split(__file__)[0].replace("\\", "/") + "/test.usda"
        context = omni.usd.get_context()
        if not context.open_stage(filepath):
            raise Exception("File not found:", filepath)
        stage = context.get_stage()

        prim = stage.GetPrimAtPath("/ramp")
        self.assertNotEqual(prim, None)
        ramp = acquire_interface()
        window = ui.Window(
            "ramp widget",
            width=425,
            height=0,
            menu_path="window/ramp",
            dock=ui.DockPreference.LEFT_BOTTOM,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        default_positions = [0, 0.2, 1]
        default_values = [(1, 0.5, 0), (0.5, 1, 0), (0, 0.5, 1)]
        default_interpolations = [1, 1, 1]
        rampWidget = Ramp3Widget(
            ramp,
            window.frame,
            prim,
            attr_names=["positions_empty", "values3_empty", "interpolations_empty"],
            default_keys=[default_positions, default_values, default_interpolations],
        )

        # make sure that default values are created
        await self.checkKeyEquality(rampWidget, default_positions, default_values, default_interpolations)

        self.assertAlmostEqual(rampWidget.basic_clamp(-1), 0)
        self.assertAlmostEqual(rampWidget.basic_clamp(0.5), 0.5)
        self.assertAlmostEqual(rampWidget.basic_clamp(2), 1)

        release_interface(ramp)
