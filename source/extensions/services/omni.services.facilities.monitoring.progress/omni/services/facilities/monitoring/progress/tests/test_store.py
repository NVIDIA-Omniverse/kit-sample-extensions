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
from omni.services.facilities.monitoring.progress import store


class TestProgressStore(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._progress_store = store.ProgressStore()

    def test_initial_progress_starts_at_zero(self):
        progress_data = self._progress_store.get_progress()

        expected_result = {
            "current_step_index": 0,
            "total_step_count": 0,
            "progress": None,
            "status_message": None,
            "time_remaining": None,
        }
        self.assertEqual(expected_result, progress_data)

    def test_updating_the_progress_records_the_new_data(self):
        update_data = {
            "current_step_index": 1,
            "total_step_count": 2,
            "progress": 0.5,
            "status_message": "Halfway done!",
            "time_remaining": 100.0,
        }
        self._progress_store.update_progress(**update_data)
        progress_data = self._progress_store.get_progress()

        self.assertEqual(update_data, progress_data)

    def test_updating_the_progress_computes_the_progress_percentage(self):
        update_data = {
            "current_step_index": 1,
            "total_step_count": 2,
            "progress": None,
            "status_message": "Halfway done!",
            "time_remaining": 10.0,
        }
        self._progress_store.update_progress(**update_data)
        progress_data = self._progress_store.get_progress()

        # The Progress Facility should be able to compute the task's progress is at 50% based on having received
        # information about the task having completed 1 out of 2 steps:
        expected_result = {
            **update_data,
            "progress": 0.5,
        }
        self.assertEqual(expected_result, progress_data)

    def test_updating_the_progress_computes_the_progress_percentage_without_computation_error(self):
        # Similar to the `test_updating_the_progress_computes_the_progress_percentage` test, except we ensure the
        # Progress Facility does not attempt a division by `0` in case the given `total_step_count` is `0`:
        update_data = {
            "current_step_index": 1,
            "total_step_count": 0,  # Voluntarily unconventional data here.
            "progress": None,
            "status_message": "Submitting potentially unconventional input data.",
            "time_remaining": None,
        }
        self._progress_store.update_progress(**update_data)
        progress_data = self._progress_store.get_progress()

        # The Progress Facility should be able to compute the task's progress is at 50% based on having received
        # information about the task having completed 1 out of 2 steps:
        expected_result = {
            **update_data,
            "progress": 0.0,
        }
        self.assertEqual(expected_result, progress_data)
