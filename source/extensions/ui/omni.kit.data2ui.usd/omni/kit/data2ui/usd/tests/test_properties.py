# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.usd
from omni.ui.tests.test_base import OmniUiTest

from ..prims.prim_style_properties import prims_add_style_property, prims_remove_style_property
from ..properties.property_enums import valid_style_prim_properties

CURRENT_PATH = Path(__file__).parent.joinpath("data").absolute().resolve()


class TestData2UIUsdProperties(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()  # type: ignore

    async def test_prim_style_properties(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore

        w1, w2, w3, w4, w5 = (
            "/World/UI/Frame",
            "/World/UI/VStack",
            "/World/UI/Frame/Button",
            "/World/Styles/StyleContainer",
            "/World/Styles/StyleContainer/Style",
        )

        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Frame", prim_path=w1)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="VStack", prim_path=w2)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Button", prim_path=w3)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="StyleContainer", prim_path=w4)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Style", prim_path=w5)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        prims_add_style_property(stage, [w1, w2, w3, w4, w5], "color")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertEqual(stage.GetPrimAtPath(w1).HasAttribute("omni:ui:Style:color"), False)
        self.assertEqual(stage.GetPrimAtPath(w2).HasAttribute("omni:ui:Style:color"), False)
        self.assertEqual(stage.GetPrimAtPath(w3).HasAttribute("omni:ui:Style:color"), True)
        self.assertEqual(stage.GetPrimAtPath(w4).HasAttribute("omni:ui:Style:color"), False)
        self.assertEqual(stage.GetPrimAtPath(w5).HasAttribute("omni:ui:Style:color"), True)

        prims_remove_style_property(stage, [w1, w2, w3, w4, w5], "color")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertEqual(stage.GetPrimAtPath(w2).HasAttribute("omni:ui:Style:color"), False)
        self.assertEqual(stage.GetPrimAtPath(w4).HasAttribute("omni:ui:Style:color"), False)

    async def test_style_prim_properties(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore

        w1, w2 = (
            "/World/Styles/StyleContainer",
            "/World/Styles/StyleContainer/Style",
        )

        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="StyleContainer", prim_path=w1)
        omni.kit.commands.execute("CreateUIPrimCommand", prim_type="Style", prim_path=w2)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        style_prim = stage.GetPrimAtPath(w2)
        for style_prop in valid_style_prim_properties:
            prims_add_style_property(stage, [w2], style_prop)
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            self.assertEqual(style_prim.HasAttribute(f"omni:ui:Style:{style_prop}"), True)
            prims_remove_style_property(stage, [w2], style_prop)
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            self.assertEqual(style_prim.HasAttribute(f"omni:ui:Style:{style_prop}"), False)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
