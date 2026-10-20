# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.test
from omni.services import client
from omni.services.core import main
from omni.services.facilities.monitoring.progress import facilities


class TestProgressFacility(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._progress_facility = facilities.ProgressFacility()
        self._client = client.AsyncClient("local://", app=main.get_app())

    async def tearDown(self) -> None:
        self._progress_facility.stop()
        self._client.stop()

    async def test_initial_progress_starts_at_zero(self):
        progress_data = await self._client.progress.retrieve()

        expected_result = {
            "current_step_index": 0,
            "total_step_count": 0,
            "progress": None,
            "status_message": None,
            "time_remaining": None,
        }
        self.assertEqual(expected_result, progress_data)

    async def test_updating_the_progress_records_the_new_data(self):
        update_data = {
            "current_step_index": 1,
            "total_step_count": 2,
            "progress": 0.5,
            "status_message": "Halfway done!",
            "time_remaining": 10.0,
        }
        self._progress_facility.set_progress(**update_data)

        await omni.kit.app.get_app().next_update_async()
        progress_data = await self._client.progress.retrieve()

        self.assertEqual(update_data, progress_data)
