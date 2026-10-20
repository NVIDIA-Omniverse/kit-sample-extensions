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

import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.window.preferences
import omni.ui as ui
from omni.kit.thumbnails.mdl.preference_page import SETTING_TITLE
from omni.ui.tests.test_base import OmniUiTest

from ..constants import PERSISTENT_MDL_RENDER_SAMPLES, PERSISTENT_MDL_TEMPLATE_PATH, PERSISTENT_USD_TEMPLATE_PATH

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")

KIT_ROOT = Path(carb.tokens.acquire_tokens_interface().resolve("${kit}")).parent.parent.parent
OUTPUTS_DIR = KIT_ROOT.joinpath("outputs")


class TestPreference(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_preference(self):
        window = await self.create_test_window(width=1280, height=400)  # noqa: F841 pylint: disable=unused-variable

        settings = carb.settings.get_settings()
        save_mdl_template = settings.get(PERSISTENT_MDL_TEMPLATE_PATH)
        settings.set(PERSISTENT_MDL_TEMPLATE_PATH, "C:/template")
        save_usd_template = settings.get(PERSISTENT_USD_TEMPLATE_PATH)
        settings.set(PERSISTENT_USD_TEMPLATE_PATH, "C:/template")
        saved_samples = settings.get(PERSISTENT_MDL_RENDER_SAMPLES)
        settings.set(PERSISTENT_MDL_RENDER_SAMPLES, 8)

        # hack to remove other pages and only keep the current page being tested, to avoid image difference in page
        # order
        _original_pages = omni.kit.window.preferences.get_page_list()
        original_pages_copy = _original_pages.copy()

        for page in original_pages_copy:
            if page.get_title() == SETTING_TITLE:
                omni.kit.window.preferences.select_page(page)
            else:
                omni.kit.window.preferences.unregister_page(page)
        # hack to replace the created preferences records in ext instance so it won't error on shutdown
        omni.kit.window.preferences.get_instance()._created_preferences = (  # pylint: disable=protected-access
            _original_pages
        )

        omni.kit.window.preferences.rebuild_pages()
        omni.kit.window.preferences.show_preferences_window()
        await omni.kit.app.get_app().next_update_async()

        w = ui.Workspace.get_window("Preferences")

        await self.docked_test_window(
            window=w,
            width=1280,
            height=400,
        )

        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name="preference.png",
        )

        settings.set(PERSISTENT_MDL_TEMPLATE_PATH, save_mdl_template)
        settings.set(PERSISTENT_USD_TEMPLATE_PATH, save_usd_template)
        settings.set(PERSISTENT_MDL_RENDER_SAMPLES, saved_samples)
