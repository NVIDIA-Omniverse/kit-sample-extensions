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

from .. import extension
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
EXT_ROOT_PATH = CURRENT_PATH.parent.parent.parent.parent.parent
TEST_DATA_PATH = EXT_ROOT_PATH.joinpath("data").joinpath("tests")
PRIM_PATH_CUBE = "/World/Cube"


class TestMarkupItem(OmniUiTest):

    async def setUp(self):
        import omni.usd
        from omni.kit.markup.core.model import MarkupItem

        await omni.usd.get_context().new_stage_async()
        await wait_for_viewport_frames()

        extension.get_instance().create_markup()
        self.markup = list(extension.get_instance().get_markups())[0]

        self.item = MarkupItem(self.markup)

    async def tearDown(self):
        import omni.usd

        self.markup = None
        self.item = None
        await super().tearDown()
        await omni.usd.get_context().close_stage_async()

    async def test_get_markup(self):
        """Get markup instance from the stored name"""
        self.assertEqual(self.markup, self.item.markup)

        extension.get_instance().delete_markup(self.markup)

        self.assertIsNone(self.item.markup)


class TestMarkupModel(OmniUiTest):

    async def setUp(self):
        import omni.usd
        from omni.kit.markup.core.model import MarkupModel

        await omni.usd.get_context().new_stage_async()
        await wait_for_viewport_frames()

        self.changelog = []

        self.model = MarkupModel(self.log_change)
        await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        import omni.usd

        await omni.usd.get_context().close_stage_async()
        if hasattr(self.model, "destroy"):
            self.model.destroy()
        self.model = None
        await super().tearDown()

    async def test_markup_changed_fn(self):
        """Basic test to instanciate MarkupModel"""
        await omni.kit.app.get_app().next_update_async()

        extension.get_instance().create_markup()
        extension.get_instance().end_edit_markup(list(extension.get_instance().get_markups())[0], save=True)

        await ui_test.human_delay(20)

        self.assertTrue(len(self.changelog) > 0)

    def log_change(self, *args, **kwargs):
        self.changelog.append([args, kwargs])


class DummyMarkup:
    def __init__(self, name, path, thumbnail_data=None):
        self.name = name
        self.path = path
        self.data = None
        self.thumbnail_data = thumbnail_data
