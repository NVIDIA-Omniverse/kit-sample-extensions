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
from datetime import datetime
from pathlib import Path

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit.widget.calendar import Calendar
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestCalendar(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_calendar(self):
        dt = datetime.now()
        calendar = Calendar(dt)
        self.assertEqual(calendar.day, dt.day)
        self.assertEqual(calendar.month, dt.month)
        self.assertEqual(calendar.year, dt.year)

    async def test_date_format(self):
        for dt, expected in [
            (datetime.fromisoformat("2023-01-01"), "2023-01-01"),
            (datetime.fromisoformat("2023-10-01"), "2023-10-01"),
            (datetime.fromisocalendar(year=2023, week=1, day=1), "2023-01-02"),
        ]:
            calendar = Calendar(dt)
            self.assertEqual(calendar._get_model_value(), expected, dt)
