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

from omni.ui.tests.test_base import OmniUiTest

from ..update_event_helper import Timer


class TestTimer(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._timer = Timer(1, self._on_timer)

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._timer.stop()
        self._timer = None

    async def test_play(self):
        self._timer.start()
        self.assertFalse(self._timer._paused)

        self.assertTrue(self._timer.running)

        await asyncio.sleep(1)

        await self.retry_until_success(lambda: not self._timer.running)

    async def test_pause(self):
        self._timer.start()
        self.assertFalse(self._timer._paused)

        self.assertTrue(self._timer.running)

        await asyncio.sleep(0.5)

        self._timer.pause()
        self.assertTrue(self._timer._paused)

        await asyncio.sleep(0.5)

        self.assertTrue(self._timer.running)

        self._timer.resume()
        self.assertFalse(self._timer._paused)

        await asyncio.sleep(0.5)

        await self.retry_until_success(lambda: not self._timer.running)

    def _on_timer(self):
        return False
