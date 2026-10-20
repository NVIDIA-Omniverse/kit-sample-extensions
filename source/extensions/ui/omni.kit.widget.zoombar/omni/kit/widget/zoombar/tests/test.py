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
from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.widget.zoombar import ZoomBar
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestZoombar(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

    # After running each test
    async def tearDown(self):
        self._zoombar.destroy()
        await super().tearDown()

    async def test_general(self):
        """Testing general look of Zoombar"""

        def _on_view_mode_changed(mode: bool) -> None:
            self._icon_mode = mode

        def _on_value_changed(value) -> None:
            self._value = value

        window = await self.create_test_window(width=200, height=30)
        with window.frame:
            self._zoombar = ZoomBar(
                on_view_mode_changed_fn=_on_view_mode_changed, on_value_changed_fn=_on_value_changed
            )

        # Wait for icon load completed
        await asyncio.sleep(2)

        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="zoombar.png")

        window_ref = ui_test.WindowRef(window, "")
        button_ref = window_ref.find_all(f"**/Button[*]")[0]
        await button_ref.click()
        self.assertEqual(self._icon_mode, True)

        value = 10
        self._zoombar.model.set_value(value)
        self.assertEqual(self._value, value)
