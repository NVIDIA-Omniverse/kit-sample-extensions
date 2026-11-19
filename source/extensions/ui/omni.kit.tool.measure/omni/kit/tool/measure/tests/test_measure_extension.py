# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd

from .test_util import TestMeasureBase

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureXtension(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def test_extenstion(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.tool.measure"
        self.assertTrue(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay(10)
        self.assertFalse(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay(10)
        self.assertTrue(manager.is_extension_enabled(ext_id))
