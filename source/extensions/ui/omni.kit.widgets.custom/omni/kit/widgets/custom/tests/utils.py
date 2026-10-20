# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

import carb
import omni.kit.ui_test as ui_test
from omni.ui.tests.test_base import OmniUiTest

from .compare_utils import capture_and_compare

DEBUG_MODE = True
GOLDEN_IMG_DIR = Path(
    carb.tokens.get_tokens_interface().resolve("${omni.kit.widgets.custom}/data/tests/golden_img")
).absolute()


async def wait_frames(frame_count):
    await ui_test.wait_n_updates(frame_count)


class TestWidgetsCustomBase(OmniUiTest):
    @staticmethod
    def _hide_main_menu_bar():
        try:
            from omni.kit.mainwindow import get_main_window

            main_window = get_main_window()
            menu_bar = main_window.get_main_menu_bar()
            menu_bar.visible = False
        except ImportError:
            pass

    async def compare_screen_with_golden(self, test_name="", golden_img=None, threadhold=100):
        """Capture current frame and compare it with the golden image. Assert if the diff is more than given threshold."""
        diff = await capture_and_compare(golden_img, threadhold, self._golden_img_dir, use_log=True)
        if diff != 0:
            carb.log_warn(f"[{test_name}] the generated image has difference {diff}")

        self.assertTrue(
            (diff is not None and diff < threadhold),
            msg=f"The image for test '{test_name}' doesn't match the golden one. Difference of {diff} is is not less than threshold of 10.",
        )
