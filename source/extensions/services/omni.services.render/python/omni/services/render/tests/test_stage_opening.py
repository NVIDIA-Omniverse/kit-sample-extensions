# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import unittest
from tempfile import NamedTemporaryFile

import omni.kit.test
import omni.usd
from omni.services.render.services.render import _open_stage_sync

_usd_data = """#usda 1.0
def Cube "box" {
    double size = 4.0
}
"""


class TestStageManagement(omni.kit.test.AsyncTestCase):

    @unittest.skip("Test misbehaves on Linux when closing the stage.")
    async def test_open_stage_sync_valid(self):
        with NamedTemporaryFile(suffix=".usda") as file:
            file.write(_usd_data.encode("ascii"))
            file.flush()

            success, error = _open_stage_sync(file.name)
            self.assertTrue(success)
            self.assertEqual(error, None)

        context = omni.usd.get_context()
        context.close_stage()

    async def test_open_stage_sync_invalid(self):
        success, error = _open_stage_sync("i_do_not_exist.usd")

        self.assertFalse(success)
        self.assertEqual(error, "Open USD error: i_do_not_exist.usd")
