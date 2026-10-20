# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.ui_test as ui_test
import omni.kit.window.preferences as preferences
from omni.ui.tests.test_base import OmniUiTest

from .utils import TestTeleportBase


class TestTeleportPreference(OmniUiTest):
    async def test_preference_page(self):
        title = "Navigation"
        found = False
        for page in preferences.get_page_list():
            if page.get_title() == title:
                preferences.select_page(page)
                found = True

        self.assertTrue(found)

        preferences.show_preferences_window()
        await ui_test.wait_n_updates(30)

        # would be better to do img test, but it does not work right now.
        await self.finalize_test_no_image()
