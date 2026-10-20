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
from pathlib import Path

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.viewport.utility import get_active_viewport_camera_string
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf

from .. import extension
from ..common import ApproveType
from ..viewport_markup import ViewportMarkup
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestViewportMarkup(OmniUiTest):
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

    async def test_rename(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup = ext_instance.get_markup("Markup_00")
        self.assertTrue(isinstance(markup, ViewportMarkup))

        # rename to something sensible:
        markup.rename("Markup_renamed")

        self.assertEqual(str(markup.path), "/Viewport_Markups/Markup_renamed")

        # rename to garbage (should do nothing):
        markup.rename("****")
        self.assertEqual(str(markup.path), "/Viewport_Markups/Markup_renamed")

    async def test_recall(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup = ext_instance.get_markup("Markup_00")
        self.assertTrue(isinstance(markup, ViewportMarkup))

        markup.recall(without_camera=True, enable_settings=["a", "b"], disable_settings=["a", "d"])

    async def test_dirty(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup = ext_instance.get_markup("Markup_00")
        self.assertTrue(isinstance(markup, ViewportMarkup))

        self.assertEqual(markup.is_dirty, False)

        # should flag as dirty if the camera has been moved:
        camera_state = ViewportCameraState(get_active_viewport_camera_string())
        camera_state.set_position_world((10, 0, 0), False)

        self.assertEqual(markup.is_dirty, True)

    async def test_general(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()

        markup = ext_instance.get_markup("Markup_00")
        self.assertTrue(isinstance(markup, ViewportMarkup))

        markup.recall()
        self.assertEqual(markup.name, "Markup_00")
        self.assertEqual(markup.thumbnail, None)
        self.assertEqual(markup.thumbnail_data, None)
        self.assertEqual(markup.comment, "")
        self.assertNotEqual(markup.camera_prim, None)
        self.assertEqual(markup.is_dirty, False)
        self.assertEqual(markup.frame, 0.0)

        self.assertTrue(isinstance(markup.create_time, str))
        self.assertTrue(isinstance(markup.created_by, str))
        self.assertTrue(isinstance(markup.approval_type, ApproveType))

        markup.frame = 10.0
        self.assertEqual(markup.frame, 10.0)

        markup.comment = "this is a comment"
        self.assertEqual(markup.comment, "this is a comment")

        markup.name = "blah"
        self.assertEqual(markup.name, "blah")

        self.assertEqual(markup.__str__(), '"blah"')
        self.assertEqual(markup.__repr__(), '"blah"')

        markup.approve()
        markup.reject()
        markup.reset_approval()
        await markup.wait()

        self.assertTrue(isinstance(markup.info, list))
