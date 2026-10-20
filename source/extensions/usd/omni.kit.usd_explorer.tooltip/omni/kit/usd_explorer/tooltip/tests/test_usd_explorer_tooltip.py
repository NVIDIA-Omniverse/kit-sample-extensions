from pathlib import Path

import carb.tokens
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from ..extension import APP_TOOLTIP_ENABLED_SETTING_PATH, set_usd_explorer_tooltip

GOLDEN_IMG_DIR = Path(
    carb.tokens.get_tokens_interface().resolve("${omni.kit.usd_explorer.tooltip}/data/tests/golden_img")
)


class Testusd_explorerTooltip(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = GOLDEN_IMG_DIR.absolute()
        self._settings = carb.settings.get_settings()

        # setup test window and widget
        self._window = await self.create_test_window(width=400, height=400, block_devices=False)
        with self._window.frame:
            self._widget = ui.Button("Test Button", width=40, height=20)

    # After running each test
    async def tearDown(self):
        self._settings.set(APP_TOOLTIP_ENABLED_SETTING_PATH, False)
        self._widget.destroy()
        self._widget = None
        self._window = None

        await super().tearDown()

    async def test_normal_tooltip(self):
        set_usd_explorer_tooltip(self._widget, "test//normal tooltip")
        self.assertFalse(self._widget.has_tooltip_fn())
        self.assertEqual(self._widget.tooltip, "normal tooltip")

    async def test_custom_tooltip(self):
        self._settings.set(APP_TOOLTIP_ENABLED_SETTING_PATH, True)
        self.assertFalse(self._widget.has_tooltip_fn())

        # set a custom tooltip using the default tooltip template
        set_usd_explorer_tooltip(self._widget, "tname:template")
        self.assertTrue(self._widget.has_tooltip_fn())

        await ui_test.emulate_mouse_move(ui_test.Vec2(20, 10))
        await ui_test.wait_n_updates(10)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="custom_tooltip.png")
