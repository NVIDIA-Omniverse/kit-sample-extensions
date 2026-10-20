import asyncio
from functools import lru_cache
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from carb.input import KeyboardEventType, KeyboardInput
from omni.kit.tool.teleport import Teleport
from omni.kit.ui_test import Vec2
from omni.kit.viewport.navigation.core import NAVIGATION_TOOL_OPERATION_ACTIVE
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300
SETTING_COMPARE_COLDEN = "/app.navigation.test/golden_compare"


@lru_cache()
def _get_input_provider() -> carb.input.InputProvider:
    return carb.input.acquire_input_provider()


async def emulate_keyboard(event_type: KeyboardEventType, key: KeyboardInput, modifier: carb.input.KeyboardInput = 0):
    keyboard = omni.appwindow.get_default_app_window().get_keyboard()
    _get_input_provider().buffer_keyboard_key_event(keyboard, event_type, key, modifier)


class TestMarkupMenuWindow(OmniUiTest):
    async def setUp(self):
        await self._move_mouse(Vec2(0.0, 0.0))
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()
        self._golden_compare = self._settings.get(SETTING_COMPARE_COLDEN)

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._teleport = Teleport.get_instance()
        self.assertFalse(self._teleport.get_active())

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='teleport'")

    async def finalize_test(self, golden_img_name: str = None):
        if self._golden_compare and golden_img_name:
            await omni.kit.app.get_app().next_update_async()
            await super().finalize_test(
                threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )
            await omni.kit.app.get_app().next_update_async()
        else:
            self.assertTrue(self._button)
            await super().finalize_test_no_image()
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, "none")
        self.assertFalse(self._teleport.get_active())
        await omni.usd.get_context().close_stage_async()

    async def _click_button(self):
        await self._button.click()
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

    async def _move_mouse(self, pos: Vec2):
        await ui_test.emulate_mouse_move(pos)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

    async def test_general(self):
        await omni.usd.get_context().new_stage_async()
        await self.finalize_test(golden_img_name="navigation_teleport.png")

    async def test_waypoint_active(self):
        # Create a new stage to show camera parameters
        await omni.usd.get_context().new_stage_async()
        await self._click_button()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                break
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="navigation_teleport_active.png")

    async def test_on_operation_active_changed(self):
        await omni.usd.get_context().new_stage_async()
        self.assertFalse(self._teleport.get_active())
        await self._click_button()
        self.assertTrue(self._teleport.get_active())
        await self._click_button()
        self.assertFalse(self._teleport.get_active())
        await self._click_button()
        self.assertTrue(self._teleport.get_active())
        await self.finalize_test()

    async def test_on_bar_hover_changed_active_non_teleport(self):
        await omni.usd.get_context().new_stage_async()
        self.assertFalse(self._teleport.get_active())
        await self._move_mouse(self._button.center)
        self.assertFalse(self._teleport.get_active())
        await self.finalize_test()

    async def test_on_bar_hover_changed_active_teleport(self):
        await omni.usd.get_context().new_stage_async()
        await self._click_button()
        self.assertTrue(self._teleport.get_active())
        await self._move_mouse(Vec2(0, 0))
        await self._move_mouse(self._button.center)
        self.assertFalse(self._teleport.get_active())
        await self.finalize_test()

    async def test_on_Y_pressed(self):
        self._settings.set("/omni/kit/hotkey/core/hotkeys_enabled", True)
        await omni.usd.get_context().new_stage_async()
        await emulate_keyboard(KeyboardEventType.KEY_PRESS, KeyboardInput.Y)
        await ui_test.human_delay(3)
        self.assertTrue(self._teleport.get_active())
        await emulate_keyboard(KeyboardEventType.KEY_RELEASE, KeyboardInput.Y)
        await ui_test.human_delay(3)
        self.assertFalse(self._teleport.get_active())
        self._settings.set("/omni/kit/hotkey/core/hotkeys_enabled", False)
        await self.finalize_test()

    async def test_on_U_pressed(self):
        TELE_BEAM_VISIBLE = "/exts/omni.kit.tool.teleport/beamVisible"
        self._settings.set("/omni/kit/hotkey/core/hotkeys_enabled", True)
        await omni.usd.get_context().new_stage_async()

        # the default value of beamVisible is True
        before = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self._settings.set(TELE_BEAM_VISIBLE, False)
        await self._click_button()
        self.assertTrue(self._teleport.get_active())
        await self._move_mouse(Vec2(0, 0))
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertFalse(is_visible)

        await emulate_keyboard(KeyboardEventType.KEY_PRESS, KeyboardInput.U)
        await ui_test.human_delay(4)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertTrue(is_visible)

        await emulate_keyboard(KeyboardEventType.KEY_RELEASE, KeyboardInput.U)
        await ui_test.human_delay(4)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertFalse(not is_visible)
        await emulate_keyboard(KeyboardEventType.KEY_PRESS, KeyboardInput.U)

        await ui_test.human_delay(4)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertTrue(not is_visible)

        await emulate_keyboard(KeyboardEventType.KEY_RELEASE, KeyboardInput.U)
        await ui_test.human_delay(4)
        is_visible = self._settings.get_as_bool(TELE_BEAM_VISIBLE)
        self.assertFalse(is_visible)
        self._settings.set("/omni/kit/hotkey/core/hotkeys_enabled", False)
        self._settings.set(TELE_BEAM_VISIBLE, before)
        await self.finalize_test()
