# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
from pathlib import Path

import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from omni.kit.waypoint.core import WaypointModel, get_instance

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestModel(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._waypoint_changed = False
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._waypoint_model = WaypointModel(on_waypoint_changed_fn=self._on_waypoint_changed)

    # After running each test
    async def tearDown(self):
        self._waypoint_model.destroy()
        self._waypoint_model = None

    async def test_1_empty(self):
        # When initialized, only one collection item "Stage", one category item "Stage" and no detail items
        collection_items = self._waypoint_model.get_item_children(None)
        self.assertEqual(len(collection_items), 1)
        self.assertEqual(collection_items[0].name, "Stage")

        category_items = self._waypoint_model.get_item_children(collection_items[0])
        self.assertEqual(len(category_items), 1)
        self.assertEqual(category_items[0].name, "Stage")

        detail_items = self._waypoint_model.get_item_children(category_items[0])
        self.assertEqual(len(detail_items), 0)

    async def test_2_waypoint_loaded(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        # Wait for waypoint loaded
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        collection_items = self._waypoint_model.get_item_children(None)
        self.assertEqual(len(collection_items), 1)
        self.assertEqual(collection_items[0].name, "Stage")

        category_items = self._waypoint_model.get_item_children(collection_items[0])
        self.assertEqual(len(category_items), 1)
        self.assertEqual(category_items[0].name, "Stage")

        detail_items = self._waypoint_model.get_item_children(category_items[0])
        self.assertEqual(len(detail_items), 2)

        # Recall the waypoint via execute
        self._waypoint_model.execute(detail_items[1])

        await self._context.close_stage_async()

    async def test_3_waypoint_changed(self):
        self.assertFalse(self._waypoint_changed)

        ext = get_instance()
        await ext.create_waypoint_async()
        self.assertTrue(self._waypoint_changed)

        self._waypoint_changed = False

        waypoint = ext.get_waypoint("Waypoint_00")
        waypoint.rename("Test")

        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        self.assertTrue(self._waypoint_changed)

    def _on_waypoint_changed(self):
        self._waypoint_changed = True
