# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from unittest import skip

import carb
import omni.kit.app
import omni.kit.test
from omni.services.facilities import log


class TestLogFacility(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._log_data = None
        self._logger = log.CarbLogFacility()

        def on_log_event(e):
            self._log_data = e

        self._log_stream = omni.kit.app.get_app().get_log_event_stream()
        self._log_sub = self._log_stream.create_subscription_to_pop(on_log_event, name="test log event")

    async def tearDown(self):
        self._log_sub = None
        self._log_stream = None

    async def test_debug_function(self):
        assert self._logger.debug == carb.log_verbose

    async def test_info_function(self):
        assert self._logger.info == carb.log_info

    async def test_warning_function(self):
        assert self._logger.warning == carb.log_warn

    async def test_error_function(self):
        assert self._logger.error == carb.log_error

    async def test_exception_function(self):
        assert self._logger.exception == carb.log_error

    @skip("carb.log_info doesn't generate stream events")
    async def test_info_message(self):
        self._logger.info("info message")
        await omni.kit.app.get_app().next_update_async()
        assert self._log_data.payload["level"] == -1

    async def test_warning_message(self):
        self._logger.warning("testing warning message")
        await omni.kit.app.get_app().next_update_async()
        assert self._log_data.payload["level"] == 0

    async def test_error_message(self):
        self._logger.error("testing error message")
        await omni.kit.app.get_app().next_update_async()
        assert self._log_data.payload["level"] == 1

    async def test_exception_message(self):
        self._logger.exception("testing exception message")
        await omni.kit.app.get_app().next_update_async()
        assert self._log_data.payload["level"] == 1
