# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import carb.eventdispatcher
import omni.kit.app
import omni.kit.clipboard
import omni.kit.test
import omni.usd
from omni.kit.test_suite.helpers import StageEventHandler, wait_stage_loading
from omni.ui.tests.test_base import OmniUiTest

from ..encoder import Base64URLEncoder
from ..utils.scene_utils import get_resolved_value


# pylint: disable=protected-access
class TestAPI(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        await omni.usd.get_context().new_stage_async()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        await omni.usd.get_context().new_stage_async()

    async def test_generate_link(self):
        omni.kit.clipboard.copy("test")

        usd_path = Path(
            f"{omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)}/data/tests"
        )

        usd_context = omni.usd.get_context()
        test_file_path = str(usd_path.joinpath("placeholder.usda").absolute()).replace("\\", "/")
        await usd_context.open_stage_async(str(test_file_path))
        await wait_stage_loading()

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "omni.web.deeplink"
        action_registry.execute_action(actions_tag, "generate_link_clicked")

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        clipboard = omni.kit.clipboard.paste()
        self.assertNotEqual(clipboard, "test")
        self.assertTrue(Base64URLEncoder.can_decode_link(clipboard))

        decoded = Base64URLEncoder.decode(clipboard)
        self.assertEqual(decoded["stage"].lower(), test_file_path.lower())
        self.assertEqual(decoded["camera"]["camera"], "/OmniverseKit_Persp")
        self.assertEqual(decoded["time"]["current_time"], "0")
        # these are floats and need todo almost equal tests...
        translate = get_resolved_value(decoded["camera"]["xformOp:translate"])
        self.assertAlmostEqual(translate, (500, 500, 500))
        rotate = get_resolved_value(decoded["camera"]["xformOp:rotateXYZ"])
        self.assertAlmostEqual(rotate, (-35.2644, 45, 0))
        scale = get_resolved_value(decoded["camera"]["xformOp:scale"])
        self.assertAlmostEqual(scale, (1, 1, 1))

    async def test_apply_link(self):
        omni.kit.clipboard.copy("test")

        usd_path = Path(
            f"{omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)}/data/tests"
        )

        usd_context = omni.usd.get_context()
        test_file_path = str(usd_path.joinpath("placeholder.usda").absolute()).replace("\\", "/")
        await usd_context.open_stage_async(str(test_file_path))
        await wait_stage_loading()

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "omni.web.deeplink"
        action_registry.execute_action(actions_tag, "generate_link_clicked")

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        clipboard = omni.kit.clipboard.paste()
        self.assertNotEqual(clipboard, "test")
        self.assertTrue(Base64URLEncoder.can_decode_link(clipboard))

        await usd_context.new_stage_async()
        # open stage and wait for it to be opened
        stage_event_handler = StageEventHandler("omni.web.deeplink")
        await stage_event_handler.reset_stage_event(omni.usd.StageEventType.OPENED)
        action_registry.execute_action(actions_tag, "apply_link_clicked")
        await stage_event_handler.wait_for_stage_event()
        del stage_event_handler

        # verify that the stage is opened
        self.assertEqual(usd_context.get_stage().GetRootLayer().GetDisplayName(), "placeholder.usda")

    async def test_event_handling(self):
        # Send valid link via Events 2.0 — the extension subscribes to
        # "apply_deeplink_request" with carb.eventdispatcher.observe_event.
        dispatcher = carb.eventdispatcher.get_eventdispatcher()
        event_name = "apply_deeplink_request"

        omni.kit.clipboard.copy("test")

        usd_path = Path(
            f"{omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)}/data/tests"
        )

        usd_context = omni.usd.get_context()
        test_file_path = str(usd_path.joinpath("placeholder.usda").absolute()).replace("\\", "/")
        await usd_context.open_stage_async(str(test_file_path))
        await wait_stage_loading()

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "omni.web.deeplink"
        action_registry.execute_action(actions_tag, "generate_link_clicked")

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        clipboard = omni.kit.clipboard.paste()
        self.assertNotEqual(clipboard, "test")
        self.assertTrue(Base64URLEncoder.can_decode_link(clipboard))

        await usd_context.new_stage_async()

        url = Base64URLEncoder._remove_padding(clipboard)
        self.assertTrue(Base64URLEncoder.can_decode_link(url, remove_padding=False, use_crc=True))

        payload = {"data": url}

        stage_event_handler = StageEventHandler("omni.web.deeplink")
        await stage_event_handler.reset_stage_event(omni.usd.StageEventType.OPENED)

        dispatcher.dispatch_event(event_name, payload=payload)

        await stage_event_handler.wait_for_stage_event()
        del stage_event_handler

        # verify that the stage is opened
        self.assertEqual(usd_context.get_stage().GetRootLayer().GetDisplayName(), "placeholder.usda")

    async def test_invalid_link(self):
        omni.kit.clipboard.copy("test")

        # Dispatch invalid payload via Events 2.0 — the extension handles
        # the error internally; this test passes if no exception escapes.
        dispatcher = carb.eventdispatcher.get_eventdispatcher()
        event_name = "apply_deeplink_request"

        payload = {"data": "test"}
        dispatcher.dispatch_event(event_name, payload=payload)

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        # nothing to verify as errors are handled in the event handler
        # as long as there are no errors, the test passes

    async def test_no_bound_camera(self):
        omni.kit.clipboard.copy("test")

        usd_path = Path(
            f"{omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)}/data/tests"
        )

        usd_context = omni.usd.get_context()
        test_file_path = str(usd_path.joinpath("no_camera.usda").absolute()).replace("\\", "/")
        await usd_context.open_stage_async(str(test_file_path))
        await wait_stage_loading()

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "omni.web.deeplink"
        action_registry.execute_action(actions_tag, "generate_link_clicked")

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        clipboard = omni.kit.clipboard.paste()
        self.assertNotEqual(clipboard, "test")
        self.assertTrue(Base64URLEncoder.can_decode_link(clipboard))

        decoded = Base64URLEncoder.decode(clipboard)
        self.assertEqual(decoded["stage"].lower(), test_file_path.lower())
        self.assertEqual(decoded["camera"]["camera"], "/OmniverseKit_Persp")
        self.assertEqual(decoded["time"]["current_time"], "0")
        # these are floats and need todo almost equal tests...
        translate = get_resolved_value(decoded["camera"]["xformOp:translate"])
        self.assertAlmostEqual(translate, (500, 500, 500))
        rotate = get_resolved_value(decoded["camera"]["xformOp:rotateXYZ"])
        self.assertAlmostEqual(rotate, (-35.2644, 45, 0))
        scale = get_resolved_value(decoded["camera"]["xformOp:scale"])
        self.assertAlmostEqual(scale, (1, 1, 1))
