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
import os
import unittest
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.undo
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.markup.core.widgets.list_window import MarkupListWindow
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf

from .. import extension
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestMarkupToolExtension(OmniUiTest):

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
        await ui_test.human_delay(15)

    # After running each test
    async def tearDown(self):
        await ui_test.human_delay(15)
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_ext_create_markup(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup("/Viewport_Markups/TestMarkup")
        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = list(ext_instance.get_markups())[0]
        self.assertEqual(ext_instance.get_markup("TestMarkup"), markup)
        prim = markup.usd_prim

        self.assertEqual(markup.path, "/Viewport_Markups/TestMarkup")
        self.assertEqual(prim.GetAttribute("approval").Get(), markup.approval_type.value)
        self.assertEqual(
            "/Viewport_Markups/TestMarkup" + prim.GetAttribute("camera:path").Get(), markup.camera_prim.GetPath()
        )
        self.assertEqual(prim.GetAttribute("comment").Get(), markup.comment)
        self.assertEqual(prim.GetAttribute("created").Get(), markup.create_time)
        self.assertEqual(prim.GetAttribute("created_by").Get(), markup.created_by)
        self.assertEqual(prim.GetAttribute("frame").Get(), markup.frame)
        stage = omni.usd.get_context().get_stage()
        cameraPrim = stage.GetPrimAtPath(prim.GetAttribute("camera:path").Get())
        self.assertEqual(
            prim.GetAttribute("icon_position").Get(),
            omni.usd.get_world_transform_matrix(cameraPrim).ExtractTranslation(),
        )
        self.assertEqual(prim.GetAttribute("omni:LiveEditLock").Get(), True)

        omni.kit.undo.undo()

        self.assertEqual(len(ext_instance.get_markups()), 0)

        omni.kit.undo.redo()

        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = list(ext_instance.get_markups())[0]
        self.assertEqual(ext_instance.get_markup("TestMarkup").name, "TestMarkup")

        self.assertEqual(prim.GetAttribute("approval").Get(), markup.approval_type.value)
        self.assertEqual(
            "/Viewport_Markups/TestMarkup" + prim.GetAttribute("camera:path").Get(), markup.camera_prim.GetPath()
        )
        self.assertEqual(prim.GetAttribute("comment").Get(), markup.comment)
        self.assertEqual(prim.GetAttribute("created").Get(), markup.create_time)
        self.assertEqual(prim.GetAttribute("created_by").Get(), markup.created_by)
        self.assertEqual(prim.GetAttribute("frame").Get(), markup.frame)
        stage = omni.usd.get_context().get_stage()
        cameraPrim = stage.GetPrimAtPath(prim.GetAttribute("camera:path").Get())
        self.assertEqual(
            prim.GetAttribute("icon_position").Get(),
            omni.usd.get_world_transform_matrix(cameraPrim).ExtractTranslation(),
        )
        self.assertEqual(prim.GetAttribute("omni:LiveEditLock").Get(), True)

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_ext_delete_markup(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup("/Viewport_Markups/TestMarkup")
        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = ext_instance.get_markup("TestMarkup")
        self.assertEqual(markup.name, "TestMarkup")

        ext_instance.delete_markup(markup)

        self.assertEqual(len(ext_instance.get_markups()), 0)

        omni.kit.undo.undo()

        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = ext_instance.get_markup("TestMarkup")
        self.assertEqual(markup.name, "TestMarkup")

        omni.kit.undo.redo()

        self.assertEqual(len(ext_instance.get_markups()), 0)

    async def test_ext_rename_markup(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup("/Viewport_Markups/TestMarkup")
        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = ext_instance.get_markup("TestMarkup")
        ext_instance.create_markup("/Viewport_Markups/TestMarkup2")
        ext_instance.end_edit_markup(ext_instance.get_markup("TestMarkup2"), save=True)
        self.assertEqual(len(ext_instance.get_markups()), 2)
        self.assertEqual(markup.name, "TestMarkup")

        self.assertEqual(ext_instance.rename_markup(markup, "TestMarkup"), True)
        self.assertEqual(markup.name, "TestMarkup")

        # try renaming to an existing markup and WITNESS FAILURE
        self.assertEqual(ext_instance.rename_markup(markup, "TestMarkup2"), False)
        self.assertEqual(markup.name, "TestMarkup")

        ext_instance.rename_markup(markup, "RenamedMarkup")
        self.assertEqual(ext_instance.get_markup("TestMarkup"), None)
        self.assertEqual(ext_instance.get_markup("RenamedMarkup").name, "RenamedMarkup")

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_ext_rename_markup_undo(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup("/Viewport_Markups/TestMarkup")
        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = ext_instance.get_markup("TestMarkup")
        ext_instance.create_markup("/Viewport_Markups/TestMarkup2")
        ext_instance.end_edit_markup(ext_instance.get_markup("TestMarkup2"), save=True)
        self.assertEqual(len(ext_instance.get_markups()), 2)
        self.assertEqual(markup.name, "TestMarkup")

        self.assertEqual(ext_instance.rename_markup(markup, "TestMarkup"), True)
        self.assertEqual(markup.name, "TestMarkup")

        # try renaming to an existing markup and WITNESS FAILURE
        self.assertEqual(ext_instance.rename_markup(markup, "TestMarkup2"), False)
        self.assertEqual(markup.name, "TestMarkup")

        ext_instance.rename_markup(markup, "RenamedMarkup")
        self.assertEqual(ext_instance.get_markup("TestMarkup"), None)
        self.assertEqual(ext_instance.get_markup("RenamedMarkup").name, "RenamedMarkup")

        omni.kit.undo.undo()

        self.assertEqual(len(ext_instance.get_markups()), 2)
        self.assertEqual(ext_instance.get_markup("TestMarkup").name, "TestMarkup")
        self.assertEqual(ext_instance.get_markup("RenamedMarkup"), None)

        omni.kit.undo.redo()

        self.assertEqual(len(ext_instance.get_markups()), 2)
        self.assertEqual(ext_instance.get_markup("TestMarkup"), None)
        self.assertEqual(ext_instance.get_markup("RenamedMarkup").name, "RenamedMarkup")

    @unittest.skipIf(True, "Undo queue is currently broken")
    async def test_ext_edit_markup(self):
        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup_00 = ext_instance.get_markup("Markup_00")
        self.assertEqual(ext_instance.editing_markup, markup_00)
        ext_instance.end_edit_markup(markup_00, save=False)

        # exiting edit mode without a save should have blown this markup away:
        self.assertEqual(ext_instance.get_markup("Markup_00"), None)

        # this just fails silently:
        ext_instance.end_edit_markup(markup_00, save=False)

        ext_instance.create_markup()
        markup_00 = ext_instance.get_markup("Markup_00")
        ext_instance.end_edit_markup(markup_00, save=True)

        ext_instance.create_markup()

        markup_01 = ext_instance.get_markup("Markup_01")
        self.assertEqual(ext_instance.editing_markup, markup_01)

        # this should also fail silently:
        ext_instance.end_edit_markup(markup_00, save=True)

        ext_instance.end_edit_markup(markup_01, save=True)

        self.assertEqual(ext_instance.get_markup("Markup_00"), markup_00)
        self.assertEqual(ext_instance.get_markup("Markup_01"), markup_01)

        self.assertEqual(ext_instance.can_edit_markup(markup_00), True)
        self.assertEqual(ext_instance.can_edit_markup(markup_01), True)

        ext_instance.begin_edit_markup(markup_00)

        self.assertEqual(ext_instance.can_edit_markup(markup_00), True)
        self.assertEqual(ext_instance.can_edit_markup(markup_01), False)

        raise NotImplementedError("How should undo work with this feature?")

    async def test_ext_can_edit_markup(self):
        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup_00 = ext_instance.get_markup("Markup_00")
        self.assertEqual(ext_instance.editing_markup, markup_00)
        ext_instance.end_edit_markup(markup_00, save=False)

        # exiting edit mode without a save should have blown this markup away:
        self.assertEqual(ext_instance.get_markup("Markup_00"), None)

        # this just fails silently:
        ext_instance.end_edit_markup(markup_00, save=False)

        ext_instance.create_markup()
        markup_00 = ext_instance.get_markup("Markup_00")
        ext_instance.end_edit_markup(markup_00, save=True)

        ext_instance.create_markup()

        markup_01 = ext_instance.get_markup("Markup_01")
        self.assertEqual(ext_instance.editing_markup, markup_01)

        # this should also fail silently:
        ext_instance.end_edit_markup(markup_00, save=True)

        ext_instance.end_edit_markup(markup_01, save=True)

        self.assertEqual(ext_instance.get_markup("Markup_00"), markup_00)
        self.assertEqual(ext_instance.get_markup("Markup_01"), markup_01)

        self.assertEqual(ext_instance.can_edit_markup(markup_00), True)
        self.assertEqual(ext_instance.can_edit_markup(markup_01), True)

        ext_instance.begin_edit_markup(markup_00)

        self.assertEqual(ext_instance.can_edit_markup(markup_00), True)
        self.assertEqual(ext_instance.can_edit_markup(markup_01), False)

    async def test_sublayer_can_edit_markup(self):
        # This is to test OMFP-3846

        stage_path = str(TEST_DATA_PATH.absolute().joinpath("stage/missing_layer.usda").absolute())
        success = omni.usd.get_context().open_stage(stage_path)
        self.assertTrue(success)

        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage)

        root_layer = stage.GetRootLayer()
        self.assertIsNotNone(root_layer)

        layer = Sdf.Layer.FindRelativeToLayer(root_layer, "./existing_layer.usda")
        self.assertIsNotNone(layer)

        stage.SetEditTarget(layer)

        ext_instance = extension.get_instance()
        ext_instance.create_markup("/Viewport_Markups/TestMarkup")

        markup = ext_instance.get_markup("TestMarkup")
        self.assertIsNotNone(markup)
        ext_instance.end_edit_markup(markup, save=True)

        self.assertEqual(ext_instance.can_edit_markup(markup), True)

    async def test_edit_end_fn(self):
        ext_instance = extension.get_instance()
        try:
            call_list = []

            def edit_end_fn(call_list):
                call_list.append(True)

            ext_instance.edit_end_fn = lambda: edit_end_fn(call_list)

            ext_instance.create_markup()
            await ui_test.human_delay(3)
            self.assertEqual(len(call_list), 0)

            ext_instance.delete_markup(list(ext_instance.get_markups())[0])
            await ui_test.human_delay(3)
            self.assertEqual(len(call_list), 1)

            await self._context.new_stage_async()
            await wait_for_viewport_frames()
            await ui_test.human_delay(15)
            self.assertTrue(len(call_list) > 1)

        finally:

            ext_instance.edit_end_fn = None

        self.assertEqual(ext_instance.edit_end_fn, None)

    async def test_show_icons(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        self._setting.set(extension.SETTINGS_MARKUP_SHOW_ICONS, True)
        await ui_test.human_delay(3)

    async def test_open_callback(self):
        ext_instance = extension.get_instance()
        try:
            call_list = []

            def open_callback(call_list):
                call_list.append(True)

            ext_instance.set_open_callback(lambda: open_callback(call_list))

            ext_instance.create_markup()
            ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=True)

            await ui_test.human_delay(3)
            self.assertEqual(len(call_list), 1)

            ext_instance.current_markup = None
            ext_instance.open_markup(list(ext_instance.get_markups())[0].name)

            await ui_test.human_delay(3)
            self.assertEqual(len(call_list), 2)

        finally:

            ext_instance.set_open_callback(None)

    async def test_notifications(self):
        ext_instance = extension.get_instance()

        def on_markup_created(call_list, markup):
            call_list.append(markup)

        def on_markup_deleted(call_list, markup):
            call_list.append(markup)

        def on_markup_changed(call_list, markup):
            call_list.append(markup)

        def on_reset(call_list):
            call_list.append(True)

        created_call_list = []
        deleted_call_list = []
        changed_call_list = []
        reset_call_list = []
        notification = extension.MarkupChangeCallbacks(
            lambda m: on_markup_created(created_call_list, m),
            lambda m: on_markup_deleted(deleted_call_list, m),
            lambda m: on_markup_changed(changed_call_list, m),
            lambda: on_reset(reset_call_list),
        )

        try:
            ext_instance.register_callback(notification)

            ext_instance.create_markup()

            # wait for thumbnail...
            await ui_test.human_delay(15)
            self.assertEqual(len(created_call_list), 1)
            self.assertEqual(len(deleted_call_list), 0)
            self.assertEqual(len(changed_call_list), 0)
            self.assertEqual(len(reset_call_list), 0)

            ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=True)

            # wait for thumbnail again...
            await ui_test.human_delay(15)
            self.assertEqual(len(created_call_list), 2)  # why?? That probably shouldn't happen right?
            self.assertEqual(len(deleted_call_list), 0)
            self.assertEqual(len(changed_call_list), 1)
            self.assertEqual(len(reset_call_list), 0)

            ext_instance.delete_markup(list(ext_instance.get_markups())[0])
            await ui_test.human_delay(15)
            self.assertEqual(len(created_call_list), 2)
            self.assertEqual(len(deleted_call_list), 1)
            self.assertEqual(len(changed_call_list), 1)
            self.assertEqual(len(reset_call_list), 1)

            await self._context.new_stage_async()
            await wait_for_viewport_frames()
            await ui_test.human_delay(15)
            self.assertEqual(len(created_call_list), 2)
            self.assertEqual(len(deleted_call_list), 1)
            self.assertEqual(len(changed_call_list), 1)
            self.assertTrue(len(reset_call_list) > 2)

        finally:

            ext_instance.deregister_callback(notification)

    async def test_edit_end_callback(self):
        ext_instance = extension.get_instance()
        call_list = []

        def edit_end_callback(call_list):
            call_list.append(True)

        ext_instance.create_markup()
        ext_instance.end_edit_markup(
            list(ext_instance.get_markups())[0], save=True, callback=lambda: edit_end_callback(call_list)
        )

        # wait for the thumbnail to generate:
        await ui_test.human_delay(15)
        self.assertEqual(len(call_list), 1)

    async def test_edit_state_change_fn(self):
        ext_instance = extension.get_instance()
        call_list = []

        try:

            def edit_state_change(call_list, x):
                call_list.append(x)

            ext_instance.edit_state_change_fn = lambda x: edit_state_change(call_list, x)

            ext_instance.create_markup()
            self.assertEqual(len(call_list), 1)
            ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=True)

            ext_instance.begin_edit_markup(list(ext_instance.get_markups())[0])
            self.assertEqual(len(call_list), 2)

            await ui_test.human_delay(15)

        finally:
            ext_instance.edit_state_change_fn = None

        self.assertEqual(ext_instance.edit_state_change_fn, None)

    async def test_end_edit_markup(self):

        ext_instance = extension.get_instance()
        ext_instance.refresh_stage()

        ext_instance.create_markup()
        await ui_test.human_delay()

        ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=True)

        ext_instance.begin_edit_markup(list(ext_instance.get_markups())[0])
        ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=False)

    async def test_end_edit_nav(self):

        ext_instance = extension.get_instance()
        ext_instance.refresh_stage()

        ext_instance.create_markup()
        await ui_test.human_delay()

        ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=True)

        ext_instance.begin_edit_markup(list(ext_instance.get_markups())[0])
        ext_instance.end_edit_markup(list(ext_instance.get_markups())[0], save=False)

        current_tool = self._setting.get("/app/viewport/currentTool")

        self.assertEqual(current_tool, "navigation")

    async def test_edit_hides_and_restores_navbar(self):
        # Editing a markup should hide the navigation menubar and restore its
        # prior value when editing ends.
        ext_instance = extension.get_instance()
        ext_instance.refresh_stage()

        nav_prev = self._setting.get_as_bool(extension.NAV_IS_VISIBLE)
        try:
            # Start from a known "visible" state.
            self._setting.set_bool(extension.NAV_IS_VISIBLE, True)

            # Creating a markup also enters edit mode, so it should hide the navbar too.
            ext_instance.create_markup()
            await ui_test.human_delay()
            self.assertFalse(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))

            # Leave edit mode so we have a saved markup we can re-enter cleanly.
            markup_00 = ext_instance.get_markup("Markup_00")
            ext_instance.end_edit_markup(markup_00, save=True)
            await ui_test.human_delay()
            self.assertTrue(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))

            # Entering edit mode should hide the navbar...
            ext_instance.begin_edit_markup(markup_00)
            self.assertFalse(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))

            # ...and exiting should restore it to the captured value.
            ext_instance.end_edit_markup(markup_00, save=True)
            await ui_test.human_delay()
            self.assertTrue(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))

            # The captured value should be whatever was set before editing, not a
            # hard-coded default: start hidden and confirm it stays hidden.
            self._setting.set_bool(extension.NAV_IS_VISIBLE, False)
            ext_instance.begin_edit_markup(markup_00)
            self.assertFalse(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))
            ext_instance.end_edit_markup(markup_00, save=True)
            await ui_test.human_delay()
            self.assertFalse(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))

            # Closing the stage mid-edit must still restore the navbar (this path
            # bypasses end_edit_markup), otherwise the navbar leaks hidden.
            self._setting.set_bool(extension.NAV_IS_VISIBLE, True)
            ext_instance.create_markup()
            await ui_test.human_delay()
            self.assertFalse(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))
            await self._context.new_stage_async()
            await wait_for_viewport_frames()
            await ui_test.human_delay(15)
            self.assertTrue(self._setting.get_as_bool(extension.NAV_IS_VISIBLE))
        finally:
            self._setting.set_bool(extension.NAV_IS_VISIBLE, nav_prev)

    async def test_extension_methods(self):

        ext_instance = extension.get_instance()
        ext_instance.refresh_stage()

        ext_instance.create_markup()
        await ui_test.human_delay()

        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup_00 = ext_instance.get_markup("Markup_00")
        self.assertTrue(ext_instance.is_markup_prim("/Viewport_Markups/Markup_00"))
        await ui_test.human_delay()
        ext_instance.load_markups()
        await ui_test.human_delay()
        ext_instance.begin_edit_markup(markup_00)
        await ui_test.human_delay()

        ext_instance.end_edit_markup(markup_00, save=True)
        await ui_test.human_delay(6)

        ext_instance.opened_markup_name = "yup"
        self.assertEqual(ext_instance.opened_markup_name, "yup")

        ext_instance.delete_markup(ext_instance.get_markup("Markup_00"))
        await ui_test.human_delay(6)
        self.assertEqual(len(ext_instance.get_markups()), 0)

        ext_instance.create_markup()

        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup_00 = ext_instance.get_markup("Markup_00")
        ext_instance.begin_edit_markup(markup_00)
        ext_instance.end_edit_markup(markup_00, save=False)
        await ui_test.human_delay()

        ext_instance.create_markup()
        markup_00 = ext_instance.get_markup("Markup_00")

        ext_instance.rename_markup(markup_00, "MyMarkup")

        self.assertEqual(ext_instance.get_markup("whatever"), None)

        self.assertEqual(ext_instance.get_markup_from_prim_path("/Viewport_Markups/MyMarkup"), markup_00)
        self.assertEqual(ext_instance.get_markup_from_prim_path("asdfsadf"), None)

        ext_instance.take_screenshot()

        mymarkup = ext_instance.get_markup("MyMarkup")

        self.assertTrue(ext_instance.can_edit_markup(mymarkup))

        self.assertEqual(ext_instance.get_markup_prim_path("whatever"), "/Viewport_Markups/whatever")
        self.assertEqual(ext_instance.get_markup_prim_path("MyMarkup"), "/Viewport_Markups/MyMarkup")

        self.assertEqual(ext_instance.get_all_markup_names(), ["MyMarkup"])

        self.assertEqual(ext_instance.get_markup_name("/Viewport_Markups/MyMarkup"), "MyMarkup")
        await ui_test.human_delay(5)

    async def test_camera_stuff(self):

        ext_instance = extension.get_instance()

        ext_instance.lock_camera(None)
        ext_instance.unlock_camera()

        ext_instance.lock_camera("/OmniverseKit_Persp")
        LOCK_CAMERA_ATTR = "omni:kit:cameraLock"
        stage = self._context.get_stage()
        prim = stage.GetPrimAtPath("/OmniverseKit_Persp")
        self.assertTrue(prim.HasAttribute(LOCK_CAMERA_ATTR))

        lockAttr = prim.GetAttribute(LOCK_CAMERA_ATTR)
        self.assertTrue(lockAttr.Get())

        omni.kit.undo.undo()

        self.assertFalse(prim.HasAttribute(LOCK_CAMERA_ATTR))

        omni.kit.undo.redo()

        lockAttr = prim.GetAttribute(LOCK_CAMERA_ATTR)
        self.assertTrue(lockAttr)
        self.assertTrue(lockAttr.Get())

        # lock again, which shouldn't do anything:
        stack_size_before = len(omni.kit.undo.get_undo_stack())
        ext_instance.lock_camera("/OmniverseKit_Persp")
        self.assertEqual(len(omni.kit.undo.get_undo_stack()), stack_size_before)

        lockAttr = prim.GetAttribute(LOCK_CAMERA_ATTR)
        self.assertTrue(lockAttr.Get())

        ext_instance.unlock_camera()

        self.assertFalse(prim.GetAttribute(LOCK_CAMERA_ATTR))

        omni.kit.undo.undo()

        self.assertTrue(lockAttr.Get())

        omni.kit.undo.redo()

        self.assertFalse(prim.GetAttribute(LOCK_CAMERA_ATTR))

        await ui_test.human_delay(6)

    async def test_elements(self):
        ext_instance = extension.get_instance()

        ext_instance.create_markup()
        await ui_test.human_delay()

        ext_instance.remove_element("whatever")

        markup_00 = ext_instance.get_markup("Markup_00")

        ext_instance.current_markup = markup_00

        element_style = {
            v: {"background_color": 0x0, "border_color": 0xFFFFFFFF, "border_width": 1}
            for v in ("FreeRectangle", "FreeCircle", "FreeEllipse")
        }
        element_name, element_path = ext_instance.add_element(
            0, 0, 10, 10, "Line", element_style, pixel_size=(10.0, 10.0)
        )
        self.assertEqual(element_name, "Line_0")
        stage = self._context.get_stage()
        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}"))

        elem = stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}")
        self.assertEqual(elem.GetAttribute("rect").Get(), (0, 0, 10, 10))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        omni.kit.undo.undo()

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}"))

        omni.kit.undo.redo()

        elem = stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}")
        self.assertTrue(elem)
        self.assertEqual(elem.GetAttribute("rect").Get(), (0, 0, 10, 10))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        ext_instance.update_element_pos(element_name, 10, 10, 20, 20)

        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        omni.kit.undo.undo()

        self.assertEqual(elem.GetAttribute("rect").Get(), (0, 0, 10, 10))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        omni.kit.undo.redo()

        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        new_element_style = {
            v: {"background_color": 0x0, "border_color": 0xFF0000FF, "border_width": 3}
            for v in ("FreeRectangle", "FreeCircle", "FreeEllipse")
        }
        ext_instance.update_element_attrs(
            element_name,
            element_style=new_element_style,
            text="test",
            points=[(0.0, 1.0), (2.0, 3.0)],
            ele_type="Circle",
            shape_type="Rectangle",
            color=int(0x00AAFF),
        )

        self.assertTrue(stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}"))
        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(elem.GetAttribute("points").Get(), [(0.0, 1.0), (2.0, 3.0)])
        self.assertEqual(elem.GetAttribute("hex_color").Get(), 0x00AAFF)
        self.assertEqual(elem.GetAttribute("shape_type").Get(), "Rectangle")
        self.assertEqual(eval(elem.GetAttribute("style").Get()), new_element_style)
        self.assertEqual(elem.GetAttribute("text").Get(), "test")
        self.assertEqual(elem.GetAttribute("type").Get(), "Circle")

        omni.kit.undo.undo()

        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(eval(elem.GetAttribute("style").Get()), element_style)
        self.assertEqual(elem.GetAttribute("type").Get(), "Line")

        omni.kit.undo.redo()

        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(elem.GetAttribute("points").Get(), [(0.0, 1.0), (2.0, 3.0)])
        self.assertEqual(elem.GetAttribute("hex_color").Get(), 0x00AAFF)
        self.assertEqual(elem.GetAttribute("shape_type").Get(), "Rectangle")
        self.assertEqual(eval(elem.GetAttribute("style").Get()), new_element_style)
        self.assertEqual(elem.GetAttribute("text").Get(), "test")
        self.assertEqual(elem.GetAttribute("type").Get(), "Circle")

        self.assertEqual(ext_instance.get_element_attr(element_name, "text", "whatever"), "test")

        ext_instance.remove_element(ext_instance.get_markup_elements()[0].GetPath())

        self.assertEqual(len(ext_instance.get_markup_elements()), 0)

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}"))

        omni.kit.undo.undo()

        elem = stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}")
        self.assertEqual(len(ext_instance.get_markup_elements()), 1)
        self.assertEqual(elem.GetAttribute("rect").Get(), (10, 10, 20, 20))
        self.assertEqual(elem.GetAttribute("points").Get(), [(0.0, 1.0), (2.0, 3.0)])
        self.assertEqual(elem.GetAttribute("hex_color").Get(), 0x00AAFF)
        self.assertEqual(elem.GetAttribute("shape_type").Get(), "Rectangle")
        self.assertEqual(eval(elem.GetAttribute("style").Get()), new_element_style)
        self.assertEqual(elem.GetAttribute("text").Get(), "test")
        self.assertEqual(elem.GetAttribute("type").Get(), "Circle")

        omni.kit.undo.redo()

        self.assertEqual(len(ext_instance.get_markup_elements()), 0)

        self.assertFalse(stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}"))

        omni.kit.undo.undo()
        ext_instance.current_markup = None
        elem = stage.GetPrimAtPath(f"/Viewport_Markups/Markup_00/{element_name}")
        # this shouldn't do anything as the current markup is null
        ext_instance.update_element_attrs(
            element_name,
            text="yeahyeah",
        )
        self.assertEqual(elem.GetAttribute("text").Get(), "test")

        # should return None if current markup is null
        self.assertEqual(ext_instance.get_element_attr(element_name, "text", "whatever"), None)

        await ui_test.human_delay(11)

    async def test_missing_layer(self):
        # This is to test OMFP-2961

        stage_path = str(TEST_DATA_PATH.absolute().joinpath("stage/missing_layer.usda").absolute())
        success = omni.usd.get_context().open_stage(stage_path)
        self.assertTrue(success)

        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage)

        root_layer = stage.GetRootLayer()
        self.assertIsNotNone(root_layer)

        layer = Sdf.Layer.FindRelativeToLayer(root_layer, "./existing_layer.usda")
        self.assertIsNotNone(layer)

        stage.SetEditTarget(layer)

        ext_instance = extension.get_instance()
        ext_instance.create_markup("/Viewport_Markups/TestMarkup")

        markup = ext_instance.get_markup("TestMarkup")
        self.assertIsNotNone(markup)
        ext_instance.end_edit_markup(markup, save=True)

        ext_instance.can_edit_markup(markup)

    async def test_prims_hidden(self):
        # This is to test OMFP-2500

        ext_instance = extension.get_instance()

        ext_instance.create_markup("/Viewport_Markups/TestMarkup")
        self.assertEqual(len(ext_instance.get_markups()), 1)
        markup = list(ext_instance.get_markups())[0]
        self.assertEqual(ext_instance.get_markup("TestMarkup"), markup)
        prim = markup.usd_prim
        hidden = prim.GetMetadata("hide_in_stage_window")
        self.assertTrue(hidden)

    async def test_cancel_delete(self):
        # This is to test OMFP-1516

        ext_instance = extension.get_instance()

        ext_instance.create_markup()
        self.assertEqual(len(ext_instance.get_markups()), 1)
        self.assertTrue(ext_instance.editing_markup)

        await ui_test.human_delay(10)
        extension._cancel_markup_edit()
        await ui_test.human_delay(10)

        self.assertFalse(ext_instance.editing_markup)
        self.assertEqual(len(ext_instance.get_markups()), 0)

    async def test_list_window_visibility(self):
        # Regression test for OMFP-2778

        ext_instance = extension.get_instance()
        list_window = MarkupListWindow()
        list_window.visible = False  # hide window initially

        ext_instance.create_markup()
        markup_00 = ext_instance.get_markup("Markup_00")

        # We have an editing_markup
        self.assertEqual(ext_instance.editing_markup, markup_00)

        ext_instance.end_edit_markup(markup_00, save=True)
        # Now we do NOT have an editing markup ...
        self.assertIsNone(ext_instance.editing_markup)
        # ... thus the list window should pop back up
        self.assertTrue(list_window.visible)

        # Hide it again.
        list_window.visible = False

        # Now set editing markup to None (redundantly) ...
        ext_instance.editing_markup = None
        # ... and ensure list window remains invisible
        self.assertFalse(list_window.visible)

        list_window.destroy()
