# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""UI tests for ScatterWindow with golden image comparison."""

from pathlib import Path

import omni.kit.app
import omni.kit.test
from omni.sample.ui_scatter_tool.window import ScatterWindow
from omni.ui.tests.test_base import OmniUiTest

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestWindow(OmniUiTest):
    async def test_general(self):
        """Testing general look of section"""
        window = ScatterWindow("Test")
        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(
            window=window,
            width=300,
            height=550,
        )

        # Wait for images
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=TEST_DATA_PATH, golden_img_name="window.png")
