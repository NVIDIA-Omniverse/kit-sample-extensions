import asyncio
import platform
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.markup.core import get_instance
from omni.kit.ui_test import Vec2
from omni.kit.viewport.navigation.core import ViewportNavigationTooltip, get_navigation_bar
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300


class TestMarkupMenuWindow(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()

        for i in range(12):
            await omni.kit.app.get_app().next_update_async()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='markup'")
        ViewportNavigationTooltip.set_visible(True)

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()
        await super().tearDown()

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(threshold=0.2, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()

    async def test_popup(self):
        if platform.system().lower() == "windows":
            await ui_test.human_delay()
            await self._button.click()
            await ui_test.emulate_mouse_move(ui_test.Vec2(700, 50))
            await ui_test.human_delay()
            await ui_test.emulate_mouse_move(self._button.center)
            await ui_test.human_delay(20)
            await self.finalize_test(golden_img_name="navigation_markup_popup.png")

            self._previous_button = ui_test.find("Markups//Frame/**/Button[*].name=='previous'")
            self._play_button = ui_test.find("Markups//Frame/**/Button[*].name=='play'")
            self._next_button = ui_test.find("Markups//Frame/**/Button[*].name=='next'")

            await self._previous_button.click()
            await self._play_button.click()
            await self._play_button.click()
            await self._next_button.click()

    async def test_nav_bar_visibility_after_markup(self):
        nav_bar = get_navigation_bar()
        self.assertTrue(nav_bar.visible)

        # Click markup button
        await self._button.click()

        await ui_test.human_delay(10)

        markup_ext = get_instance()
        markup_ext.create_markup()

        await ui_test.human_delay(10)
        markup_00 = markup_ext.get_markup("Markup_00")
        markup_ext.end_edit_markup(markup_00, save=True)

        await ui_test.human_delay(10)

        # Unlock markup to enter edit mode
        thumbnail_btn = ui_test.find("Markups//Frame/**/ImageThumbnail")
        await thumbnail_btn.click()
        await thumbnail_btn.double_click()

        edit_btn = ui_test.find("Markups//Frame/**/HoverEditButton")
        await ui_test.human_delay(10)
        await edit_btn.click()
        await ui_test.human_delay(10)

        # Nav bar is hidden when markup editing begins
        self.assertFalse(nav_bar.visible)

        markup_ext.end_edit_markup(markup_00, save=True)

        await ui_test.human_delay(10)

        # Nav bar is visible when markup editing ends
        self.assertTrue(nav_bar.visible)
