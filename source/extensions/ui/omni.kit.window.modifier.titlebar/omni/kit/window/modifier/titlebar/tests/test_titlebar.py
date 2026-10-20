import sys
import unittest

import carb
import carb.tokens
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from .utils import DBG_PRINT, MainWindowInfo, capture_and_compare, set_mouse_pos

SETTING_CHANEGE_WINDOW_REGION = "/exts/omni.kit.window.modifier.titlebar/changeWindowRegion"


def is_ui_mode():
    if "--no-window" in sys.argv:  # pragma: no cover
        DBG_PRINT("Not ui mode")
        return False
    return True


@unittest.skipUnless(sys.platform == "win32", "Windows-only UI tests")
class WindowModifierTestCase(OmniUiTest):
    """Test custom application window style"""

    # Before running each test
    async def setUp(self, use_region=False):
        self._settings = carb.settings.get_settings()
        self._settings.set(SETTING_CHANEGE_WINDOW_REGION, use_region)
        await self.wait_n_updates(5)

        await super().setUp()

        # Main window information
        screen_w, screen_h = (800, 400)
        DBG_PRINT(f"Screen size: ({screen_w}, {screen_h})")

        self._mwi = MainWindowInfo(screen_w, screen_h)
        await self.wait_n_updates(3)

        path = "/exts/omni.kit.window.modifier.titlebar/windowBorder"
        self._border_width = self._settings.get_as_int(path + "/width")

        # Mouse position for caption buttons
        button_width = int((self._mwi.caption_h - self._border_width) * 1.55)
        y = self._mwi.caption_h - 2
        right = self._mwi.w - self._mwi.border_w
        self._close_pos = (self._mwi.x + right - 20, self._mwi.y + y)
        self._max_pos = (self._mwi.x + right - 20 - button_width, self._mwi.y + y)
        self._min_pos = (self._mwi.x + right - 20 - button_width * 2, self._mwi.y + y)

        # Empty mouse position in order to avoid mouse activate any button
        # (Use window rect center as the "safe" position)
        self._empty_pos = (self._mwi.x + self._mwi.w * 0.5, self._mwi.y + self._mwi.h * 0.5)

        cutoff = 5
        # For pyautogui, the region is in format of (left, top, width, height)
        # For PIL ImageGrab, the region is in format of (left, top, right, bottom)
        # self._wnd_region = (self._mwi.x + cutoff, self._mwi.y, self._mwi.w - 2 * cutoff, self._mwi.h - cutoff)
        self._wnd_region = (
            self._mwi.x + cutoff,
            self._mwi.y,
            self._mwi.x + self._mwi.w - cutoff,
            self._mwi.y + self._mwi.h - cutoff,
        )

        # await self.wait_n_updates(30)        # Capture region
        # self._wnd_region = (self._mwi.x, self._mwi.y, self._mwi.w, self._mwi.h)

        # make sure mouse is at empty position and not leaving hover tooltips
        # from other desktop software (eg.recycle bin)
        set_mouse_pos(self._empty_pos[0], self._empty_pos[1])
        # import pyautogui
        # pyautogui.moveTo(*self._empty_pos)

        # DPI information
        self._dpi_scale = int(ui.Workspace.get_dpi_scale() * 100)

        # wait for some time to be safe that any undesired tooltip would clean out
        await self.wait_n_updates(30)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def __verify_ui(self, verify_name: str, mouse_pos):
        if self._dpi_scale == 100 and is_ui_mode():
            await self.wait_n_updates(5)
            set_mouse_pos(mouse_pos[0], mouse_pos[1])
            await self.wait_n_updates(10)

            self.assertTrue(await capture_and_compare(verify_name, self._wnd_region))
        else:
            print("DPI is not 100 or no-window!")
            self.assertIsNotNone("DPI is not 100 or no-window")

    async def test_window_colors(self):
        """Test colors"""
        await self.__verify_ui(self.__class__.__name__ + "_window_colors", self._empty_pos)

    async def test_focus_close_button(self):
        """Test focus close button"""
        await self.__verify_ui(self.__class__.__name__ + "_close_button", self._close_pos)

    async def test_focus_min_button(self):
        """Test focus min button"""
        await self.__verify_ui(self.__class__.__name__ + "_min_button", self._min_pos)

    async def test_focus_max_button(self):
        """Test focus max button"""
        await self.__verify_ui(self.__class__.__name__ + "_max_button", self._max_pos)
