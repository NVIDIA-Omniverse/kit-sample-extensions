# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path

import carb
import omni.kit
import omni.kit.test
from omni.kit import ui_test
from omni.ui.tests.test_base import OmniUiTest
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
EXT_ROOT_PATH = CURRENT_PATH.parent.parent.parent.parent.parent
TEST_DATA_PATH = EXT_ROOT_PATH.joinpath("data").joinpath("tests")
PRIM_PATH_CUBE = "/World/Cube"


class TestMarkupUsd(OmniUiTest):

    async def setUp(self):
        import omni.usd
        from omni.kit.markup.core.markup_usd import MarkupUsd

        await omni.usd.get_context().new_stage_async()
        await wait_for_viewport_frames()

        self.instance = MarkupUsd()

    async def tearDown(self):
        import omni.usd

        await omni.usd.get_context().close_stage_async()
        await super().tearDown()

    async def test_create_markupusd(self):
        """Create a MarkupUsd instance."""
        self.assertTrue(getattr(self.instance, "_stage"))
        self.assertTrue(getattr(self.instance, "_layer"))

    async def test_property_edit_context(self):
        """Get edit_context property from MarkupUsd"""
        from pxr import Usd

        context = self.instance.edit_context
        self.assertIsInstance(context, Usd.EditContext)

    async def test_update_stage(self):
        """Update stage information"""
        import omni.usd

        old_stage = self.instance._stage

        await omni.usd.get_context().new_stage_async()
        await wait_for_viewport_frames()
        context = omni.usd.get_context()

        new_stage = context.get_stage()
        self.instance.update_stage(new_stage)

        self.assertEqual(self.instance._stage, new_stage)

    async def test_update_stage_None(self):
        """Update stage to None"""
        old_stage = self.instance._stage

        self.instance.update_stage(None)
        self.assertEqual(self.instance._stage, None)
        self.assertEqual(self.instance._layer, old_stage.GetRootLayer())

    async def test_get_prim_empty_stage(self):
        """Get a prim from an empty stage."""
        prim = self.instance.get_prim(f"{PRIM_PATH_CUBE}_1", create=False)
        await omni.kit.app.get_app().next_update_async()
        self.assertIsNotNone(prim)  # invalid prim
        self.assertFalse(prim.IsValid())

    async def test_get_prim_create_without_type(self):
        """Get a non-existing prim and create a non-type"""
        prim = self.instance.get_prim(f"{PRIM_PATH_CUBE}_2", create=True, type_name=None)
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(prim.IsValid())
        # self.assertEqual(prim.GetTypeName(), 'omni:ignorePrimType')

    async def test_get_prim_create_with_type(self):
        """Get a non-existing prim and create a defined type"""
        prim = self.instance.get_prim(f"{PRIM_PATH_CUBE}_3", create=True, type_name="Test")
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(prim.IsValid())
        self.assertEqual(prim.GetTypeName(), "Test")

    async def test_get_prim_no_stage(self):
        """Get a prim when stage is None."""
        self.instance._stage = None
        self.assertIsNone(self.instance.get_prim(PRIM_PATH_CUBE))

    async def test_get_prim_no_path(self):
        """Get a prim without prim path."""
        prim = self.instance.get_prim(None, create=False)
        self.assertIsNone(prim)

    async def test_get_prim_from_usd(self):
        """Get a prim from the current stage."""
        import os

        import omni.usd

        context = omni.usd.get_context()

        usd_path = os.path.join(TEST_DATA_PATH.absolute(), "stage", "factory01.usda")
        await context.open_stage_async(usd_path)
        await omni.kit.app.get_app().next_update_async()

        stage = context.get_stage()
        prim = stage.GetPrimAtPath(PRIM_PATH_CUBE)

        self.instance.update_stage(stage)
        self.assertEqual(self.instance.get_prim(PRIM_PATH_CUBE), prim)

    async def test_remove_prim(self):
        """Remove a prim from the current stage."""
        import omni.usd

        context = omni.usd.get_context()
        stage = context.get_stage()

        prim = stage.DefinePrim(PRIM_PATH_CUBE, "Test")
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(prim.IsValid())

        self.instance.remove_prim(PRIM_PATH_CUBE)

        prim = stage.GetPrimAtPath(PRIM_PATH_CUBE)
        self.assertFalse(prim.IsValid())

    async def test_get_prim_attribute(self):
        """Get a prim attribute value."""
        import os

        import omni.usd
        from pxr import Sdf

        context = omni.usd.get_context()

        usd_path = os.path.join(TEST_DATA_PATH.absolute(), "stage", "factory01.usda")
        await context.open_stage_async(usd_path)
        await omni.kit.app.get_app().next_update_async()

        stage = context.get_stage()
        prim = stage.GetPrimAtPath(PRIM_PATH_CUBE)

        self.instance.update_stage(stage)

        attr_val = self.instance.get_prim_attribute(prim, "points", default=0)
        self.assertEqual(attr_val, prim.GetAttribute("points").Get())

    async def test_get_prim_attribute_default(self):
        """Get a non-existing attribute and returns the default value"""
        import omni.usd

        context = omni.usd.get_context()
        stage = context.get_stage()

        prim = stage.DefinePrim(PRIM_PATH_CUBE, "Test")
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(prim.IsValid())

        attr_val = self.instance.get_prim_attribute(prim, "_x", default=0)
        self.assertEqual(attr_val, 0)

    async def test_move_prim(self):
        """Make a prim clone and delete the original one."""
        import omni.usd

        context = omni.usd.get_context()
        stage = context.get_stage()

        prim = stage.DefinePrim(PRIM_PATH_CUBE, "Test")
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(prim.IsValid())

        destination = f"{PRIM_PATH_CUBE}_copy"
        self.instance.move_prim(PRIM_PATH_CUBE, destination)

        self.assertTrue(stage.GetPrimAtPath(destination).IsValid())
        self.assertFalse(stage.GetPrimAtPath(PRIM_PATH_CUBE).IsValid())
