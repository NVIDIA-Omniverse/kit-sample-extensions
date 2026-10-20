import asyncio
from pathlib import Path

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300


def clear_viewport_display():
    def __set_viewport_display(setting: str, enable: bool):
        viewport_api_id = get_active_viewport().id
        carb.settings.get_settings().set(f"/persistent/app/viewport/{viewport_api_id}/{setting}/visible", enable)

    __set_viewport_display("guide/grid", False)
    __set_viewport_display("guide/axis", False)
    vp = get_active_viewport_window()
    if hasattr(vp, "_find_viewport_layer"):
        layer = vp._find_viewport_layer("Viewport HUD")
        if layer:
            layer.visible = False


async def _wait_for_viewport_frames(frames: int = 3):
    """Kit 111: the viewport renders the (empty) stage with OVRTX, starting ~0.4 s after startup. Wait for presented
    frames so a capture doesn't race the first one (black before, rendered after). Kit 110's test viewport has no
    renderer and never presents a frame, so only wait on Kit 111+."""
    if float(omni.kit.app.get_app().get_kit_version_short()) < 111.0:
        return
    from omni.kit.viewport.utility import get_active_viewport

    viewport = get_active_viewport()
    if viewport:
        await asyncio.wait_for(viewport.wait_for_rendered_frames(frames), timeout=30)



class TestWaypointMenuWindow(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        clear_viewport_display()
        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        await _wait_for_viewport_frames()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='Waypoint'")

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await _wait_for_viewport_frames()
        await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()

    async def test_general(self):
        await self.finalize_test(golden_img_name="menubar_waypoint.png")

    async def test_popup(self):
        await self._button.click()
        await ui_test.human_delay()

        # One click shows the window
        window = ui.Workspace.get_window("Waypoints")
        self.assertIsNotNone(window)
        self.assertEqual(window.visible, True)

        await self._button.click()
        await ui_test.human_delay()

        # The next click hides it again.
        window = ui.Workspace.get_window("Waypoints")
        self.assertEqual(window.visible, False)

        # NOTE: we are not testing the visual appearance of the window, since that is covered by its own tests.
        await self.finalize_test(golden_img_name="menubar_waypoint_popup.png")
