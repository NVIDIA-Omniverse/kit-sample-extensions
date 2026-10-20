import sys
import unittest
import webbrowser
from pathlib import Path

import carb.input
import carb.settings
import omni.client
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.ui_test import Vec2
from omni.kit.viewport.utility import get_active_viewport_and_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 600
SETTING_ACTIVE_MARKUP = "/exts/omni.kit.markup.core/active_markup"
SETTING_COMPARE_COLDEN = "/app.navigation.test/golden_compare"

_ORIGINAL_WEBBROWSER_OPEN = webbrowser.open


class TestBasicUi(OmniUiTest):  # pragma: no cover

    @classmethod
    def setUpClass(cls):
        cls._browser_opened = []
        # Mock for view_screenshots test
        webbrowser.open = lambda x: cls._browser_opened.append(x)

    @classmethod
    def tearDownClass(cls):
        webbrowser.open = _ORIGINAL_WEBBROWSER_OPEN

    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()
        self._golden_compare = self._settings.get(SETTING_COMPARE_COLDEN)

        # Viewport setting: no title bar, fill frame
        viewport_api, viewport_window = get_active_viewport_and_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='Screenshot'")

        # Enable mouse input
        app_window = omni.appwindow.get_default_app_window()
        for device in [carb.input.DeviceType.MOUSE]:
            app_window.set_input_blocking_state(device, None)

    async def tearDown(self):
        await self.finalize_test_no_image()
        self._settings.set_string(SETTING_ACTIVE_MARKUP, "")
        return await super().tearDown()

    async def finalize_test(self, golden_img_name: str):
        if self._golden_compare:
            await omni.kit.app.get_app().next_update_async()
            await super().finalize_test(
                threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )
            await omni.kit.app.get_app().next_update_async()
        # else:
        # self.assertTrue(self._button)

    async def test_general(self):
        await self.finalize_test(golden_img_name="navigation_screenshot.png")

    async def test_popup(self):
        await self._button.right_click()
        await self.finalize_test(golden_img_name="navigation_screenshot_popup.png")

    async def test_type_markup(self):
        self._settings.set_string(SETTING_ACTIVE_MARKUP, "Test_Markup")
        await omni.kit.app.get_app().next_update_async()
        await self._button.click()
        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()
        if self._golden_compare:
            await self.finalize_test(golden_img_name="navigation_screenshot_markup.png")

    async def test_tooltip(self):
        from omni.kit.viewport.navigation.capture_no_ansel import extension

        instance = extension.Extension.get_instance()

        result = instance._build_tooltip()

        if self._golden_compare:
            await self.finalize_test(golden_img_name="navigation_screenshot_tooltip.png")

    async def test_set_screenshot_type(self):
        """Change screenshot types"""
        from omni.kit.viewport.navigation.capture_no_ansel import extension

        instance = extension.Extension.get_instance()
        await omni.kit.app.get_app().next_update_async()

        instance._set_screenshot_type(extension.CaptureTypes.MARKUP)
        self.assertEqual(instance._screenshot_type, extension.CaptureTypes.MARKUP)
        self.assertEqual(instance._button.name, extension.CaptureTypes.MARKUP.icon)

        instance._set_screenshot_type(extension.CaptureTypes.REGULAR)
        self.assertEqual(instance._screenshot_type, extension.CaptureTypes.REGULAR)
        self.assertEqual(instance._button.name, extension.CaptureTypes.REGULAR.icon)

    async def test_open_screenshot_settings(self):
        """Trigger opening "Screenshot Settings" window"""
        from omni.kit.viewport.navigation.capture_no_ansel import extension

        instance = extension.Extension.get_instance()
        await omni.kit.app.get_app().next_update_async()

        instance._on_screenshot_settings()
        await ui_test.wait_n_updates()
        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()

        if self._golden_compare:
            await self.finalize_test(golden_img_name="navigation_screenshot_settings.png")

    async def test_trigger_on_capture_done(self):
        """Trigger on_capture_done callback"""
        from omni.kit.viewport.navigation.capture_no_ansel import extension

        instance = extension.Extension.get_instance()
        await omni.kit.app.get_app().next_update_async()

        instance._on_capture_done("no_file.ext")
        await ui_test.wait_n_updates()
        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()

        if self._golden_compare:
            await self.finalize_test(golden_img_name="navigation_screenshot_on_capture_done.png")
        else:
            self.assertEqual(instance._settings.get_as_int(extension.SETTING_DASHBOARD_RUN_SCREENSHOT), 0)

    async def test_trigger_on_click_regular(self):
        """Trigger on_click callback at REGULAR capture type"""
        from omni.kit.viewport.navigation.capture_no_ansel import extension

        instance = extension.Extension.get_instance()
        await omni.kit.app.get_app().next_update_async()

        instance._set_screenshot_type(extension.CaptureTypes.REGULAR)
        instance._on_click()
        await ui_test.wait_n_updates()
        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()

        if self._golden_compare:
            await self.finalize_test(golden_img_name="navigation_screenshot_on_click_regular.png")

    async def _select_button_menu(self, index: int):
        await self._button.right_click()
        await omni.kit.app.get_app().next_update_async()
        pos = self._button.center + Vec2(40, 40 + index * 30)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        await ui_test.emulate_mouse_move_and_click(pos)
