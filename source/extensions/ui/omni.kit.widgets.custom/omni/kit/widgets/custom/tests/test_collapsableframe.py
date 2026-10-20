# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from ..collapsableframe import InfoPanel
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestInfoPanel(TestWidgetsCustomBase):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR

        self._hide_main_menu_bar()

    async def test_simple_gridview(self):
        window = await self.create_test_window()

        with window.frame:
            self._info_panel = InfoPanel()

        await wait_frames(3)
        self._info_panel.rebuild()

        await wait_frames(3)
        self._info_panel.update_data([["Foo", "Bar"], ["Spam", "Egg"]])

        await wait_frames(3)
        self._info_panel.show()

        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="info_panel.png")
