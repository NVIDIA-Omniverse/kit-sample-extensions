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
import copy
import unittest
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.undo
import omni.ui as ui
from omni.kit import ui_test
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Tf, Trace, Usd, UsdGeom

from .. import extension
from ..viewport_markup import ViewportMarkup
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestMarkupCommands(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._setting = carb.settings.get_settings()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        await wait_for_viewport_frames()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()

    async def test_screenshot(self):
        omni.kit.commands.execute("TakeMarkupScreenshot")

    async def test_create_undo_fns(self):

        def _markup_created_test(log, markup):
            log.append(markup)

        def _on_undo_test(log, markup) -> None:
            log.append(markup)

        create_log = []
        undo_log = []
        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
            on_create_fn=lambda m: _markup_created_test(create_log, m),
            on_undo_fn=lambda m: _on_undo_test(undo_log, m),
        )

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))
        self.assertEqual(markup.name, "Markup_00")

        # _markup_created_test should get called after the thumnail is generated
        # so wait for that to happen:
        await ui_test.human_delay(30)

        # should have had the expected amount of function calls:
        self.assertEqual(len(create_log), 1)
        self.assertEqual(len(undo_log), 0)

        omni.kit.undo.undo()

        await ui_test.human_delay(30)

        # the undo callback should have been called once now:
        self.assertEqual(len(create_log), 1)
        self.assertEqual(len(undo_log), 1)

        result, markup = omni.kit.commands.execute("CreateMarkupEntry")

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))

        omni.kit.undo.undo()
        await ui_test.human_delay(30)

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_create_markup_entry(self):

        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
        )

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))
        self.assertEqual(markup.name, "Markup_00")

        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

        result, markup1 = omni.kit.commands.execute(
            "CreateMarkupEntry",
            entry_name="stuff",
        )
        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup1, ViewportMarkup))
        self.assertEqual(markup1.name, "stuff_01")

        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))
        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup1.name}"))

        omni.kit.undo.undo()

        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))
        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup1.name}"))

        omni.kit.undo.undo()

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))
        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup1.name}"))

    async def test_delete_markup(self):

        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
            entry_name="stuff",
        )

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))
        self.assertEqual(markup.name, "stuff")

        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

        omni.kit.commands.execute("DeleteMarkupEntry", entry_name="stuff")

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_delete_markup_undo(self):

        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
            entry_name="stuff",
        )

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))
        self.assertEqual(markup.name, "stuff")

        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

        omni.kit.commands.execute("DeleteMarkupEntry", entry_name="stuff")

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

        omni.kit.undo.undo()

        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

        omni.kit.undo.redo()

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/{markup.name}"))

    async def test_rename_markup(self):

        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
            entry_name="stuff",
        )
        await ui_test.human_delay(3)

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))

        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

        stage = self._context.get_stage()

        omni.kit.commands.execute("RenameMarkupEntry", entry_name="stuff", new_name="thingy")
        await ui_test.human_delay(3)

        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/thingy"))
        self.assertFalse(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_rename_markup_undo(self):

        result, markup = omni.kit.commands.execute(
            "CreateMarkupEntry",
            entry_name="stuff",
        )
        await ui_test.human_delay(3)

        self.assertEqual(result, True)
        self.assertTrue(isinstance(markup, ViewportMarkup))

        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

        stage = self._context.get_stage()

        omni.kit.commands.execute("RenameMarkupEntry", entry_name="stuff", new_name="thingy")
        await ui_test.human_delay(3)

        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/thingy"))
        self.assertFalse(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

        omni.kit.undo.undo()
        await ui_test.human_delay(3)

        self.assertFalse(stage.GetPrimAtPath("/Viewport_Markups/thingy"))
        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

        omni.kit.undo.redo()
        await ui_test.human_delay(3)

        self.assertTrue(stage.GetPrimAtPath("/Viewport_Markups/thingy"))
        self.assertFalse(stage.GetPrimAtPath("/Viewport_Markups/stuff"))

    async def test_update_markup_entry_command(self):
        """UpdateMarkupEntryCommand runs without an error"""
        import omni.kit.commands
        import omni.usd
        from omni.kit.markup.core.common import MARKUP_ROOT_PRIM_PATH
        from omni.kit.markup.core.viewport_markup import ViewportMarkup
        from pxr import Sdf

        # create test markup
        name = f"{MARKUP_ROOT_PRIM_PATH}/_test_markup_update"
        test_comment = "This is a markup"
        stage = omni.usd.get_context().get_stage()
        path = str(omni.usd.get_stage_next_free_path(stage, name, False))

        omni.kit.commands.execute("CreatePrimCommand", prim_type="omni:ignorePrimType", prim_path=path)
        prim = stage.GetPrimAtPath(path)
        markup = ViewportMarkup(prim.GetName(), sidecar_data=None)
        markup.create(None)
        await omni.kit.app.get_app().next_update_async()

        # runs test
        status, result = omni.kit.commands.execute(
            "UpdateMarkupEntry",
            entry_name=path,
            comment=(Sdf.ValueTypeNames.String, test_comment),
        )
        self.assertTrue(status)

        prim = stage.GetPrimAtPath(path)
        prop = prim.GetAttribute("comment")
        self.assertEqual(prop.Get(), test_comment)

    async def test_create_markup_element_command(self):
        """CreateMarkupElementCommand runs without an error"""
        import omni.kit.commands
        import omni.usd
        from omni.kit.markup.core.common import MARKUP_ROOT_PRIM_PATH
        from omni.kit.markup.core.viewport_markup import ViewportMarkup
        from pxr import Sdf

        # create test markup
        name = f"{MARKUP_ROOT_PRIM_PATH}/_test_markup_create_element"
        type_name = "_TestMarkup"
        stage = omni.usd.get_context().get_stage()
        path = str(omni.usd.get_stage_next_free_path(stage, name, False))

        # runs test
        status, (name, element_path) = omni.kit.commands.execute(
            "CreateMarkupElementCommand",
            markup=path,
            element_type=type_name,
            **{"_prop": (Sdf.ValueTypeNames.String, "_value")},  # data
        )
        self.assertTrue(status)
        prim = stage.GetPrimAtPath(f"{path}/{name}")
        self.assertTrue(prim.IsValid())
        self.assertEqual(prim.GetAttribute("_prop").Get(), "_value")

    async def test_delete_markup_element_command(self):
        """DeleteMarkupElementCommand runs without an error"""
        import omni.kit.commands
        import omni.usd
        from omni.kit.markup.core.common import MARKUP_ROOT_PRIM_PATH
        from omni.kit.markup.core.viewport_markup import ViewportMarkup
        from pxr import Sdf

        # create test markup
        name = f"{MARKUP_ROOT_PRIM_PATH}/_test_markup_update_element"
        stage = omni.usd.get_context().get_stage()
        path = str(omni.usd.get_stage_next_free_path(stage, name, False))

        omni.kit.commands.execute("CreatePrimCommand", prim_type="omni:ignorePrimType", prim_path=path)
        prim = stage.GetPrimAtPath(path)
        markup = ViewportMarkup(prim.GetName(), sidecar_data=None)
        markup.create(None)
        await omni.kit.app.get_app().next_update_async()

        # runs test
        status, result = omni.kit.commands.execute(
            "DeleteMarkupElementCommand",
            element_name=path,
        )
        new_prim = stage.GetPrimAtPath(path)
        self.assertTrue(status)
        self.assertFalse(new_prim.IsValid())

    async def test_update_markup_element_command(self):
        """UpdateMarkupElementCommand runs without an error"""
        import omni.kit.commands
        import omni.usd
        from omni.kit.markup.core.common import MARKUP_ROOT_PRIM_PATH
        from omni.kit.markup.core.viewport_markup import ViewportMarkup
        from pxr import Sdf

        # create test markup
        name = f"{MARKUP_ROOT_PRIM_PATH}/_test_markup_update_element"
        stage = omni.usd.get_context().get_stage()
        path = str(omni.usd.get_stage_next_free_path(stage, name, False))

        omni.kit.commands.execute("CreatePrimCommand", prim_type="omni:ignorePrimType", prim_path=path)
        prim = stage.GetPrimAtPath(path)
        markup = ViewportMarkup(prim.GetName(), sidecar_data=None)
        markup.create(None)
        await omni.kit.app.get_app().next_update_async()

        # runs test
        status, result = omni.kit.commands.execute(
            "UpdateMarkupElement",
            element=path,
            text=(Sdf.ValueTypeNames.String, "This is a markup"),
        )

        self.assertTrue(status)
        self.assertEqual(prim.GetAttribute("text").Get(), "This is a markup")
