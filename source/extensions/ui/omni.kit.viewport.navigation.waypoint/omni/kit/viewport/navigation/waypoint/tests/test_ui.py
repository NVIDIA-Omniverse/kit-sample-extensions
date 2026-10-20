import asyncio
import platform
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.ui_test import Vec2
from omni.kit.viewport.navigation.core import ViewportNavigationTooltip
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Tf, Usd

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300


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
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        await ui_test.wait_n_updates(2)
        await _wait_for_viewport_frames()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='waypoint'")

    async def tearDown(self):
        await self._move_away()
        ViewportNavigationTooltip.set_visible(False)

        window = ui.Workspace.get_window("Waypoints")
        if window:
            window.visible = False

        await super().tearDown()

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await _wait_for_viewport_frames()
        await super().finalize_test(0.01, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()

    async def test_general(self):
        await self.finalize_test(golden_img_name="navigation_waypoint.png")

    async def test_popup(self):
        # The window should start hidden.
        window = ui.Workspace.get_window("Waypoints")
        self.assertTrue(window is None or window.visible is False)

        # Show the window.
        await self._button.click()
        await ui_test.human_delay()
        window = ui.Workspace.get_window("Waypoints")
        self.assertTrue(window is not None and window.visible is True)

        # Hide the window.
        await self._button.click()
        await ui_test.human_delay()
        window = ui.Workspace.get_window("Waypoints")
        self.assertTrue(window is None or window.visible is False)

        # Visual test (without the window, as it is tested in its own extension).
        await self.finalize_test(golden_img_name="navigation_waypoint_popup.png")

    async def test_waypoint_active(self):
        # Create a new stage to show camera parameters
        await omni.usd.get_context().new_stage_async()

        await ui_test.emulate_mouse_move(self._button.center)
        await ui_test.human_delay()

        await self.finalize_test(golden_img_name="navigation_waypoint_active.png")

    async def test_tooltip(self):
        await self._move_away()
        await ui_test.human_delay()

        ViewportNavigationTooltip.set_visible(True)

        await ui_test.human_delay()
        await ui_test.emulate_mouse_move(self._button.center)
        await ui_test.human_delay()

        await self.finalize_test(golden_img_name="navigation_waypoint_tooltip.png")

    async def _move_away(self):
        await ui_test.emulate_mouse_move(Vec2(-50, -50))
