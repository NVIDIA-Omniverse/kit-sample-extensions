# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from ..rectangle import DashRectangle, ShortSeparator
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestRectangle(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_dir = GOLDEN_IMG_DIR
        self._window = await self.create_test_window(width=480, height=320, block_devices=False)

        TestWidgetsCustomBase._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._window.destroy()
        self._window = None

    async def test_rect(self):
        with self._window.frame:
            with ui.VStack():
                ui.Spacer(height=20)
                with ui.HStack():
                    ui.Spacer(width=20)
                    ShortSeparator(height=20)
                    ui.Spacer()
                ui.Spacer(height=20)
                with ui.HStack():
                    ui.Spacer(width=20)
                    DashRectangle(440, 40)
                    ui.Spacer()

        await wait_frames(5)
        await self.finalize_test(50, golden_img_dir=self._golden_dir, golden_img_name="rectangle.png")
