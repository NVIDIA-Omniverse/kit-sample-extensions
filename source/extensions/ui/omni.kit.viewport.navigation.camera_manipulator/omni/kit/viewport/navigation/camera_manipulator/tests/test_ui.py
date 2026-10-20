import asyncio
import platform
import sys
import unittest
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.commands
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from carb.input import MouseEventType
from omni.kit.test.teamcity import is_running_in_teamcity
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.ui_test import Vec2
from omni.kit.viewport.navigation.core import NAVIGATION_TOOL_OPERATION_ACTIVE, ViewportNavigationTooltip
from omni.kit.viewport.utility import get_active_viewport_and_window
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf

from ..common import NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE, NAVIGATION_TOOL_MIN_COI_DISTANCE
from ..orbit_target import (
    DEFAULT_ORBIT_DISTANCE_SETTING_PATH,
    SETTING_SECTION_ENABLED,
    SETTING_SECTION_PLANE,
    OrbitTarget,
)
from ..update_event_helper import delay_execute_by_frame

try:
    import omni.kit.notification_manager

    HAS_NOTIFICATION = True
except ModuleNotFoundError:
    HAS_NOTIFICATION = False

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300
SETTING_COMPARE_COLDEN = "/app.navigation.test/golden_compare"
# How many times _set_orbit_target() re-sends its emulated double click before giving up, and how
# many frames it then allows the raycast that click submits to take. The raycast is normally already
# answered by the time that budget starts, so it is a generous guard against a hitching agent rather
# than an expected wait.
DOUBLE_CLICK_ATTEMPTS = 5
RAYCAST_SETTLE_FRAMES = 300  # Kit 111: OVRTX answers raycasts once it presents frames


async def _wait_for_viewport_frames(frames: int = 3):
    """Kit 111: the OVRTX viewport presents its first frame ~30 updates after a stage opens, raycasts (double-click
    targets, orbit auto-center) are answered only once it renders, and ViewportAPI.transform follows rendered frames.
    No-op on Kit < 111: its test viewport never presents a frame, so those raycasts were never answered."""
    if float(omni.kit.app.get_app().get_kit_version_short()) < 111.0:
        return
    import asyncio
    from omni.kit.viewport.utility import get_active_viewport

    viewport = get_active_viewport()
    if viewport:
        await asyncio.wait_for(viewport.wait_for_rendered_frames(frames), timeout=30)


class TestManipulatorWindow(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()
        # TODO: golden img test for camera manipulator is not stable now
        self._golden_compare = False  # self._settings.get(SETTING_COMPARE_COLDEN)

        viewport_api, viewport_window = get_active_viewport_and_window()
        self._viewport_window = viewport_window
        viewport_window.position_x = 0
        viewport_window.position_y = 0
        await self.resize_app_window()
        self._viewport_window.focus()
        await omni.kit.app.get_app().next_update_async()

        self._orbit_button = ui_test.find("Viewport//Frame/**/Button[*].name=='orbit'")
        self._dolly_button = ui_test.find("Viewport//Frame/**/Button[*].name=='dolly'")
        self._look_button = ui_test.find("Viewport//Frame/**/Button[*].name=='look'")
        self._pan_button = ui_test.find("Viewport//Frame/**/Button[*].name=='pan'")
        self._frame_button = ui_test.find("Viewport//Frame/**/Button[*].name=='frame'")
        context = omni.usd.get_context()
        await context.new_stage_async()
        await _wait_for_viewport_frames()
        await omni.kit.app.get_app().next_update_async()

    def _get_cam_mtx(self):
        viewport_api, _ = get_active_viewport_and_window()
        cam_mtx = viewport_api.transform
        return cam_mtx

    def assertAlmostEqual(self, a, b, delta=1e-3):
        if isinstance(a, (float, int)):
            super().assertAlmostEqual(a, b, delta=delta)
        elif isinstance(a, (Gf.Matrix4d, Gf.Matrix4f)):
            for va, vb in zip(a, b):
                for vva, vvb in zip(va, vb):
                    super().assertAlmostEqual(vva, vvb, delta=delta)
        else:
            for va, vb in zip(a, b):
                super().assertAlmostEqual(va, vb, delta=delta)

    async def tearDown(self):
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, "none")
        await ui_test.wait_n_updates(100)
        contex = omni.usd.get_context()
        await contex.close_stage_async()
        await omni.kit.app.get_app().next_update_async()

    async def _setup_scene(self):
        context = omni.usd.get_context()
        await context.open_stage_async(f"{TEST_DATA_PATH}/stage/test_scene.usda")
        await _wait_for_viewport_frames()
        await wait_stage_loading()
        await ui_test.wait_n_updates(10)

    def _get_focus_distance(self):
        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        stage = viewport_api.stage
        cam_prim = stage.GetPrimAtPath(cam_path)
        coi_attr = cam_prim.GetAttribute("omni:kit:centerOfInterest")
        coi = coi_attr.Get()
        return coi.GetLength()

    async def _set_orbit_target(self, x=400, y=90):
        """Double click at (x, y) and wait until the raycast that click triggers has been answered.

        Says nothing about the outcome; the caller decides whether the resulting target should be
        valid via :meth:`_validate_orbit_target`.

        The only mouse gesture that sets an orbit target is ``sc.DoubleClickGesture``; no single
        click reaches ``OrbitTarget.set_orbit_target`` (its one other caller, ``set_world_center()``,
        runs on entering orbit mode). Both that gesture and the
        ``PreventOthers.amend_input`` fallback in ``navigation_scene.py`` decide that two clicks
        form a double click by comparing wall-clock timestamps against
        ``/exts/omni.ui/clickGesture/multiClickWait`` (200ms for this suite).
        ``emulate_mouse_click(double=True)`` separates the two clicks by four frames, so a single
        frame hitch on a loaded agent -- these tests render with path tracing enabled -- silently
        degrades the emulated double click into two single clicks: no gesture fires, nothing is
        logged, and ``target_valid`` simply never turns True. So retry until the gesture is
        observed instead of assuming one emulated double click always lands.
        """
        orbit_target = OrbitTarget()
        # Bound methods captured before the instance attributes below shadow them.
        set_orbit_target = orbit_target.set_orbit_target
        query = orbit_target.query
        gesture_fired = False
        raycast_answered = False

        def _spy_set_orbit_target(mx, my, double_click=False):
            nonlocal gesture_fired
            gesture_fired = gesture_fired or double_click
            return set_orbit_target(mx, my, double_click)

        def _spy_query(double_click, prim_path, pos, *args, **kwargs):
            nonlocal raycast_answered
            raycast_answered = True
            return query(double_click, prim_path, pos, *args, **kwargs)

        orbit_target.set_orbit_target = _spy_set_orbit_target
        orbit_target.query = _spy_query
        try:
            for attempt in range(DOUBLE_CLICK_ATTEMPTS):
                # double click on target cube
                await ui_test.human_delay(5)
                if attempt == 0:
                    # Only the first attempt has to move the cursor and let the hover settle; on a
                    # retry it is already parked on the target, and repeating the 30 frame settle is
                    # what made this helper cost minutes on a slow agent.
                    await ui_test.emulate_mouse_move(ui_test.Vec2(x, y))
                    await ui_test.human_delay(30)
                await ui_test.emulate_mouse_click(double=True)
                await ui_test.human_delay(5)
                await ui_test.wait_n_updates(10)
                if gesture_fired:
                    break
            else:
                self.fail(
                    f"emulated double click at ({x}, {y}) never reached the orbit double click gesture "
                    f"after {DOUBLE_CLICK_ATTEMPTS} attempts"
                )

            # The viewport pick query (request_query) answers on a later frame, so wait for the callback
            # rather than letting the caller's assertion race it. Every pick is answered, including one
            # that lands on sectioned-out geometry -- it just comes back as a miss -- so
            # treat running out of budget here as a failure rather than carrying on and letting the
            # caller assert against a target that has not settled.
            for _ in range(RAYCAST_SETTLE_FRAMES):
                if raycast_answered:
                    break
                await omni.kit.app.get_app().next_update_async()
            else:
                self.fail(
                    f"raycast submitted by the double click at ({x}, {y}) was not answered within "
                    f"{RAYCAST_SETTLE_FRAMES} frames"
                )
        finally:
            del orbit_target.set_orbit_target
            del orbit_target.query

    async def _validate_orbit_target(self, valid=True):
        orbit_target = OrbitTarget()
        if valid:
            await self.assertTrueWithRetry(lambda: orbit_target.target_valid)
            await self.assertTrueWithRetry(lambda: orbit_target.target_indicator_model.visible)
        else:
            await self.assertTrueWithRetry(lambda: not orbit_target.target_valid)
            await self.assertTrueWithRetry(lambda: not orbit_target.target_indicator_model.visible)

    async def reset_camera(self, cam_path, cam_mtx):
        omni.kit.commands.create(
            "TransformPrimCommand", path=cam_path, new_transform_matrix=cam_mtx, usd_context_name=""
        ).do()
        await omni.kit.app.get_app().next_update_async()

    async def resize_app_window(self):
        app_window = omni.appwindow.get_default_app_window()
        dpi_scale = ui.Workspace.get_dpi_scale()

        # requested size scaled with dpi
        width_with_dpi = int(TEST_WIDTH * dpi_scale)
        height_with_dpi = int(TEST_HEIGHT * dpi_scale)

        # Current main window size
        current_width = app_window.get_width()
        current_height = app_window.get_height()

        # If the main window is already has requested size, do nothing
        if width_with_dpi == current_width and height_with_dpi == current_height:
            self._saved_width = None
            self._saved_height = None
        else:
            # Save the size of the main window to be able to restore it at the end of the test
            self._saved_width = current_width
            self._saved_height = current_height

            app_window.resize(width_with_dpi, height_with_dpi)

            # Wait for getWindowResizeEventStream
            await app_window.get_window_resize_event_stream().next_event()

    async def finalize_test(self, golden_img_name: str):
        # OMPE-47773: shoud skip image compare until nrd removed from aarch64
        if self._golden_compare and platform.processor() != "aarch64":
            await self.wait_n_updates()
            await super().finalize_test(
                threshold=1, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )
            await self.wait_n_updates()

        else:
            await self.finalize_test_no_image()
            self.assertTrue(self._orbit_button)
            self.assertTrue(self._dolly_button)
            self.assertTrue(self._look_button)
            self.assertTrue(self._pan_button)
            self.assertTrue(self._frame_button)

    async def test_general(self):
        await ui_test.wait_n_updates(10)
        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.7071067811865476, 0, -0.7071067811865476, 0),
            (-0.4082482839677567, 0.8164965874238325, -0.4082482839677567, 0),
            (0.5773502737830667, 0.577350260002744, 0.5773502737830667, -0),
            (500.0000000000001, 500.00000000000006, 500.0000000000001, 1.0000000000000002),
        )
        await self.finalize_test(golden_img_name="navigation_transform.png")
        self.assertAlmostEqual(cam_mtx, expected_cam_mtx)

    async def test_orbit_gesture(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()
            await _wait_for_viewport_frames()  # Kit 111: orbit auto-center raycast answers after a rendered frame

        default_distance = self._settings.get(DEFAULT_ORBIT_DISTANCE_SETTING_PATH)
        focus_distance = self._get_focus_distance()
        self.assertNotEqual(focus_distance, default_distance)

        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100))
        await ui_test.human_delay(20)
        await ui_test.wait_n_updates(10)

        # When there is no focus set, focus distance should be defaulted to 5M
        focus_distance = self._get_focus_distance()
        self.assertEqual(focus_distance, default_distance)

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.8884391396396785, 3.696918826623372e-9, -0.45899443913440574, 0),
            (-0.2113582827248833, 0.887669491013488, -0.40910946096056416, 0),
            (0.4074353586520149, 0.4604811339499752, 0.7886403196617889, -0),
            (384.06121166034774, 500.0000000000001, 586.4094227647198, 0.9999999999999998),
        )
        self.assertAlmostEqual(cam_mtx, expected_cam_mtx)

        if HAS_NOTIFICATION:
            await self.finalize_test(golden_img_name="test_orbit_gesture.png")
        else:
            await self.finalize_test(golden_img_name="test_orbit_gesture_no_notification.png")

    async def test_orbit_look_gesture(self):
        await self._setup_scene()
        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()
            await _wait_for_viewport_frames()  # Kit 111: orbit auto-center raycast answers after a rendered frame
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100), right_click=True)
        await omni.kit.app.get_app().next_update_async()
        await _wait_for_viewport_frames()  # Kit 111: ViewportAPI.transform follows rendered frames

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.8884391396396785, 3.696918826623372e-9, -0.45899443913440574, 0),
            (-0.2113582827248833, 0.887669491013488, -0.40910946096056416, 0),
            (0.4074353586520149, 0.4604811339499752, 0.7886403196617889, -0),
            (500.0000000000002, 500.0000000000001, 500.0000000000002, 0.9999999999999998),
        )
        self.assertAlmostEqual(cam_mtx, expected_cam_mtx)

        await self.finalize_test(golden_img_name="test_orbit_look_gesture.png")

    async def test_orbit_gesture_with_target(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()
            await _wait_for_viewport_frames()  # Kit 111: orbit auto-center raycast answers after a rendered frame
        # double click on target cube; _set_orbit_target() waits for the async
        # raycast callback to complete (wait_n_updates(10)) so the orbit target
        # and camera COI are fully established before the drag gesture begins.
        # Without this wait the raycast can fire mid-drag, repositioning the
        # camera while the TumbleGesture has already locked _orbit_target_validated=True,
        # producing the wrong orbit axis and a failing matrix comparison.
        await self._set_orbit_target()
        # emulate camera movement and let the frame settle
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100))
        await ui_test.human_delay(20)
        await ui_test.wait_n_updates(10)

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.8884391320733578, -1.6220266102484615e-9, -0.4589944537799327, 0),
            (-0.13974485843016393, 0.9525255341624356, -0.27049303375669453, 0),
            (0.43720393770307264, 0.3044587111063942, 0.8462609586223159, 0),
            (-280.2221336862685, 208.9488985511776, -38.99195476070784, 1),
        )
        # Kit 111: the orbit target comes from the viewport pick query (the depth at the clicked texture pixel), not an
        # analytic world ray, so the orbited camera's position differs from this world-ray recording by about 0.5 % of its
        # ~280-unit distance (0.6 and 1.3 units measured). The orbit itself (the rotation rows) must match to 1e-3; the
        # position is checked to 1 % of that distance.
        for row in range(3):
            for col in range(3):
                super().assertAlmostEqual(cam_mtx[row][col], expected_cam_mtx[row][col], delta=1e-3)
        for col in range(3):
            super().assertAlmostEqual(cam_mtx[3][col], expected_cam_mtx[3][col], delta=3.0)

        await self.finalize_test(golden_img_name="test_orbit_gesture_with_target.png")

    async def test_orbit_target_invalidate(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()

        orbit_target = OrbitTarget()
        self.assertFalse(orbit_target.target_valid)

        # double click on target cube
        await self._set_orbit_target()

        await omni.kit.app.get_app().next_update_async()

        await self._validate_orbit_target(True)

        # right mouse drag to look, orbit target will be lost
        await ui_test.emulate_mouse_drag_and_drop(
            ui_test.Vec2(400, 70), ui_test.Vec2(450, 70), right_click=True, human_delay_speed=5
        )
        await omni.kit.app.get_app().next_update_async()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        self.assertFalse(orbit_target.target_valid)
        self.assertFalse(orbit_target.target_indicator_model.visible)

        await omni.kit.app.get_app().next_update_async()
        if orbit_target._target_notification is not None:
            self.assertTrue(orbit_target._target_notification.dismissed)

        # orbit again, notification should show up
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(450, 70), ui_test.Vec2(400, 70), human_delay_speed=5)
        await omni.kit.app.get_app().next_update_async()
        await ui_test.human_delay(5)
        if orbit_target._target_notification is not None:
            self.assertFalse(orbit_target._target_notification.dismissed)

    @unittest.skipIf(sys.platform.startswith("linux"), "OOMPE-68825: test is flaky failed on linux ETM agents")
    async def test_orbit_target_with_wasd(self):
        """
        Test orbit target with WASD walk
        """
        await self._setup_scene()
        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()

        await self._validate_orbit_target(False)

        await self._set_orbit_target()
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(True)

        # Right click and press W/S to move camera forward and backward, target should still be valid
        async def press_right_button_and_key(key, press_duration=2, release_mouse=True):
            await ui_test.human_delay(10)
            await ui_test.input.emulate_mouse(MouseEventType.RIGHT_BUTTON_DOWN)
            await ui_test.human_delay(5)
            await ui_test.emulate_keyboard_press(key, human_delay_speed=press_duration)
            await ui_test.human_delay(10)
            if release_mouse:
                await ui_test.input.emulate_mouse(MouseEventType.RIGHT_BUTTON_UP)
                await ui_test.human_delay(20)

        # Press W
        await press_right_button_and_key(carb.input.KeyboardInput.W)
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(True)

        # Press S
        await press_right_button_and_key(carb.input.KeyboardInput.S)
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(True)

        # Press W then S, go beyond target and come back
        await press_right_button_and_key(carb.input.KeyboardInput.W, 80, release_mouse=False)
        await press_right_button_and_key(carb.input.KeyboardInput.S, 100)
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(True)

        # Press A
        await press_right_button_and_key(carb.input.KeyboardInput.A)
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(False)

        # Reset Cam
        await self.reset_camera(cam_path, cam_mtx_to_restore)

        await self._set_orbit_target()
        await self._validate_orbit_target(True)

        # Press W to go beyond target
        await press_right_button_and_key(carb.input.KeyboardInput.W, 80)
        await ui_test.wait_n_updates(10)
        await self._validate_orbit_target(False)

        # Reset Cam
        await self.reset_camera(cam_path, cam_mtx_to_restore)
        await self._set_orbit_target()
        await self._validate_orbit_target(True)

        # Press E, Q, D
        await press_right_button_and_key(carb.input.KeyboardInput.E, release_mouse=False)
        await press_right_button_and_key(carb.input.KeyboardInput.Q, release_mouse=False)
        await press_right_button_and_key(carb.input.KeyboardInput.D)
        await ui_test.wait_n_updates(10)
        await self._validate_orbit_target(False)

        # Reset Cam
        await self.reset_camera(cam_path, cam_mtx_to_restore)
        await self._set_orbit_target()
        await self._validate_orbit_target(True)
        await press_right_button_and_key(carb.input.KeyboardInput.W, 30, release_mouse=False)

        # OMPE-65314: Use proper drag and drop to trigger the gesture system
        await ui_test.emulate_mouse_drag_and_drop(
            ui_test.Vec2(400, 90), ui_test.Vec2(500, 90), right_click=True, human_delay_speed=5
        )
        await ui_test.wait_n_updates(10)

        await self._validate_orbit_target(False)

    async def test_orbit_target_with_section_tool(self):
        """
        Test orbit target when scene is sectioned
        """
        await self._setup_scene()
        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()

        await self._validate_orbit_target(False)

        await self._set_orbit_target()
        await ui_test.wait_n_updates(10)
        await self._validate_orbit_target(True)

        # Enable section
        self._settings.set(SETTING_SECTION_ENABLED, True)
        self._settings.set(SETTING_SECTION_PLANE, [0, -1, 0, 30])
        await ui_test.wait_n_updates(10)

        # Orbit target will become invalid
        await self._validate_orbit_target(False)

        # Click on position that is sectioned out, orbit target will not be set
        await self._set_orbit_target()
        await self._validate_orbit_target(False)

        # Click on non-sectioned out position, orbit target will be set
        await self._set_orbit_target(200, 200)
        await self._validate_orbit_target(True)

        # Reset camera
        await self._orbit_button.click()
        await ui_test.wait_n_updates(5)
        await self.reset_camera(cam_path, cam_mtx_to_restore)
        await self._orbit_button.click()
        await ui_test.wait_n_updates(5)

        # Reverse section direction
        self._settings.set(SETTING_SECTION_PLANE, [0, 1, 0, -30])
        await ui_test.wait_n_updates(10)

        await ui_test.human_delay(1000)

        # Click on sectioned-out space, orbit target will not be set
        await self._set_orbit_target(200, 200)
        await self._validate_orbit_target(False)

        # Orbit target will be set
        await self._set_orbit_target()
        await self._validate_orbit_target(True)

        # Turn off section
        self._settings.set(SETTING_SECTION_ENABLED, False)
        await ui_test.wait_n_updates(10)

        # Orbit target should still be valid
        await self._validate_orbit_target(True)

    async def test_default_target_distance(self):
        await self._setup_scene()
        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await omni.kit.app.get_app().next_update_async()

        orbit_target = OrbitTarget()
        self.assertFalse(orbit_target.target_valid)

        # Use the shared helper so we get the same `wait_n_updates(10)` settling
        # that prevents flakiness across the rest of the suite.
        await self._set_orbit_target()
        await self.assertTrueWithRetry(lambda: orbit_target.target_valid)

        viewport_api, _ = get_active_viewport_and_window()
        stage = viewport_api.stage
        cam_path = viewport_api.camera_path
        cam_prim = stage.GetPrimAtPath(cam_path)

        # Focus distance should be reset to default when setting orbit target for the first time
        default_distance = self._settings.get(DEFAULT_ORBIT_DISTANCE_SETTING_PATH)

        focus_distance_attr = cam_prim.GetAttribute("focusDistance")
        focus_distance = focus_distance_attr.Get()

        self.assertAlmostEqual(default_distance, focus_distance)

        coi_dist = self._get_focus_distance()
        self.assertAlmostEqual(default_distance, coi_dist, delta=1e-3)

        # Scroll to move camera back
        await ui_test.human_delay(10)
        await ui_test.emulate_mouse_scroll(ui_test.Vec2(0, -50), human_delay_speed=3)
        await ui_test.human_delay(10)
        coi_dist = self._get_focus_distance()
        self.assertNotEqual(coi_dist, default_distance)
        self.assertTrue(orbit_target.target_valid)

        # Loose target
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100), right_click=True)
        await ui_test.human_delay(20)
        self.assertFalse(orbit_target.target_valid)

        await self.reset_camera(cam_path, cam_mtx_to_restore)

        await self._set_orbit_target()
        await self.assertTrueWithRetry(lambda: orbit_target.target_valid)

        coi_dist = self._get_focus_distance()
        self.assertAlmostEqual(default_distance, coi_dist, delta=1e-3)

    async def test_orbit_pan_gesture(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await self.wait_n_updates()
            await _wait_for_viewport_frames()  # Kit 111: orbit auto-center raycast answers after a rendered frame

        start_pos = ui_test.Vec2(100, 100)
        end_pos = ui_test.Vec2(150, 100)
        await ui_test.input.emulate_mouse(MouseEventType.MOVE, start_pos)
        await ui_test.input.emulate_mouse(MouseEventType.MIDDLE_BUTTON_DOWN)
        await ui_test.input.emulate_mouse_slow_move(start_pos, end_pos)
        await self.wait_n_updates(200)
        await ui_test.input.emulate_mouse(MouseEventType.MIDDLE_BUTTON_UP)
        await self.wait_n_updates()

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = (
            (0.6937508553108465, -5.182743040288431e-9, -0.72021507256893, 0),
            (-0.3316454594466259, 0.8876694842905379, -0.3194591928365924, 0),
            (0.6393129437012094, 0.4604811469098064, 0.6158214622410654, 0),
            (427.73428420560515, 500.00000053986935, 575.0224051569435, 1),
        )
        # Rotation values should not have changed, so use a small epsilon
        self.assertAlmostEqual(cam_mtx[0], expected_cam_mtx[0])
        self.assertAlmostEqual(cam_mtx[1], expected_cam_mtx[1])
        self.assertAlmostEqual(cam_mtx[2], expected_cam_mtx[2])
        # Translation values have change, so use a larger epsilon
        self.assertAlmostEqual(cam_mtx[3], expected_cam_mtx[3], 0.5)

        await self.finalize_test(golden_img_name="test_orbit_pan_gesture.png")

    async def test_look_gesture(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "look":
            await self._look_button.click()

        await self.wait_n_updates()
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100))
        await self.wait_n_updates()

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.8884391396396785, 3.696918826623372e-9, -0.45899443913440574, 0),
            (-0.2113582827248833, 0.887669491013488, -0.40910946096056416, 0),
            (0.4074353586520149, 0.4604811339499752, 0.7886403196617889, -0),
            (499.99999999999983, 499.99999999999994, 499.99999999999983, 0.9999999999999998),
        )
        self.assertAlmostEqual(cam_mtx, expected_cam_mtx)

        await self.finalize_test(golden_img_name="test_look_gesture.png")

    async def test_pan_gesture(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "pan":
            await self._pan_button.click()
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(150, 100))
        await omni.kit.app.get_app().next_update_async()

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.6937508553108465, -5.182743040288431e-9, -0.72021507256893, 0),
            (-0.3316454594466259, 0.8876694842905379, -0.3194591928365924, 0),
            (0.6393129437012094, 0.4604811469098064, 0.6158214622410654, 0),
            (138.67142102802364, 500.0000026993454, 875.1120257847149, 1.0000000000000002),
        )
        self.assertAlmostEqual(cam_mtx, expected_cam_mtx)

        await self.finalize_test(golden_img_name="test_pan_gesture.png")

    async def test_dolly_gesture(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "dolly":
            await self._dolly_button.click()
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        cam_before = self._get_cam_mtx()
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(180, 100), ui_test.Vec2(100, 100))
        await omni.kit.app.get_app().next_update_async()

        cam_after = self._get_cam_mtx()
        expected_rotation = Gf.Matrix4d(
            (0.6937508553108465, -5.182743040288431e-9, -0.72021507256893, 0),
            (-0.3316454594466259, 0.8876694842905379, -0.3194591928365924, 0),
            (0.6393129437012094, 0.4604811469098064, 0.6158214622410654, 0),
            (0, 0, 0, 1),
        )
        self.assertAlmostEqual(cam_after[0], expected_rotation[0])
        self.assertAlmostEqual(cam_after[1], expected_rotation[1])
        self.assertAlmostEqual(cam_after[2], expected_rotation[2])
        self.assertFalse(
            Gf.IsClose(cam_before, cam_after, 1e-6),
            "Dolly should still move the camera when max navigation magnitude is enforced",
        )

        await self.finalize_test(golden_img_name="test_dolly_gesture.png")

    async def test_orbit_drag_after_double_click(self):
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await ui_test.wait_n_updates()
            await _wait_for_viewport_frames()  # Kit 111: orbit auto-center raycast answers after a rendered frame

        orbit_target = OrbitTarget()
        self.assertFalse(orbit_target.target_valid)

        # double click on target cube
        await ui_test.human_delay(5)
        await ui_test.emulate_mouse_move(ui_test.Vec2(400, 90))
        await ui_test.human_delay(30)

        # Double click but last click does not release mouse
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.wait_n_updates(2)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.wait_n_updates(2)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.wait_n_updates(2)
        await ui_test.human_delay(5)

        await omni.kit.app.get_app().next_update_async()

        await _wait_for_viewport_frames()  # Kit 111: the double click's raycast answers after a rendered frame
        self.assertTrue(orbit_target.target_valid)
        self.assertTrue(orbit_target.target_indicator_model.visible)

        prev_target_pos = orbit_target.target_indicator_model.display_position

        await ui_test.input.emulate_mouse_slow_move(ui_test.Vec2(400, 90), ui_test.Vec2(500, 90))
        await ui_test.human_delay(5)

        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await omni.kit.app.get_app().next_update_async()

        new_target_pos = orbit_target.target_indicator_model.display_position
        self.assertTrue(Gf.IsClose(prev_target_pos, new_target_pos, 1e-3))

    @unittest.skipIf(sys.platform.startswith("linux"), "OMPE-75089: test is flaky failed on linux ETM agents")
    async def test_orbit_double_click_speed(self):
        """
        Test max interval between two clicks to set orbit target
        """
        await self._setup_scene()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await ui_test.wait_n_updates()

        orbit_target = OrbitTarget()
        self.assertFalse(orbit_target.target_valid)

        # in millisecond
        click_interval = self._settings.get("/exts/omni.ui/clickGesture/multiClickWait")

        async def double_click_with_interval(interval):
            await ui_test.human_delay(5)
            await ui_test.emulate_mouse_move(ui_test.Vec2(400, 90))
            await ui_test.human_delay(10)
            await ui_test.emulate_mouse_click()
            # in second
            await asyncio.sleep(interval / 1000.0)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay(10)

        # Interval is longer than limit, orbit target will not be set
        await double_click_with_interval(click_interval + 50)
        self.assertFalse(orbit_target.target_valid)

        await ui_test.wait_n_updates(10)

        # Interval is within limit, orbit target will be set
        await double_click_with_interval(click_interval - 50)
        self.assertTrue(orbit_target.target_valid)

    async def test_orbit_with_prim_selected(self):
        """
        Test enter orbit mode when prims are selected on stage
        """
        await self._setup_scene()

        viewport_api, _ = get_active_viewport_and_window()

        # Select a cube
        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(["/World/Cube"], True)

        # Camera will frame selected prim
        before_cam_mtx = viewport_api.transform

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "orbit":
            await self._orbit_button.click()
            await ui_test.human_delay(20)

        after_cam_mtx = viewport_api.transform
        self.assertFalse(Gf.IsClose(before_cam_mtx, after_cam_mtx, 1e-6))

        await ui_test.human_delay(10)
        await self._orbit_button.click()
        await ui_test.human_delay(10)
        await self.reset_camera(viewport_api.camera_path, before_cam_mtx)

        # Add a guide prim with metadata to stage
        stage = viewport_api.stage
        guide_prim_path = "/Test_guide"
        omni.kit.commands.create(
            "CreatePrim",
            prim_type="Xform",
            prim_path=guide_prim_path,
        ).do()
        guide_prim = stage.GetPrimAtPath(guide_prim_path)
        guide_prim.SetMetadata("hide_in_stage_window", True)

        omni.kit.commands.create(
            "CreatePrim",
            prim_type="Xform",
            prim_path="/Test_guide/tool_prim",
        ).do()
        await ui_test.wait_n_updates(2)

        # Camera should stay static when guide prim is selected
        selection.set_selected_prim_paths(["/Test_guide/tool_prim"], True)
        await ui_test.human_delay(10)
        await self._orbit_button.click()
        await ui_test.human_delay(10)

        after_cam_mtx = viewport_api.transform
        self.assertTrue(Gf.IsClose(before_cam_mtx, after_cam_mtx, 1e-6))

    async def test_frame_button(self):
        await self._setup_scene()

        await self._frame_button.click()
        await ui_test.wait_n_updates(20)

        cam_mtx = self._get_cam_mtx()
        expected_cam_mtx = Gf.Matrix4d(
            (0.6937508553108465, -5.182743040288431e-9, -0.72021507256893, 0),
            (-0.3316454594466259, 0.8876694842905379, -0.3194591928365924, 0),
            (0.6393129437012094, 0.4604811469098064, 0.6158214622410654, 0),
            (944.011317377192, 920.8548837356007, 905.5436880480635, 1.0000000000000002),
        )

        # Orientation is invariant to the framing distance, so assert the rotation basis exactly.
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(cam_mtx[i][j], expected_cam_mtx[i][j], delta=1e-3)

        # Framing only slides the eye along the camera forward axis; the exact distance differs
        # across Kit versions (FramePrimsCommand per-axis vs legacy bounding-sphere framing,
        # OMPE-44796). Assert the eye stays on the expected view ray rather than pinning the exact
        # position, so the test passes for both the old and new framing distance.
        forward = Gf.Vec3d(-cam_mtx[2][0], -cam_mtx[2][1], -cam_mtx[2][2]).GetNormalized()
        eye_actual = Gf.Vec3d(cam_mtx[3][0], cam_mtx[3][1], cam_mtx[3][2])
        eye_expected = Gf.Vec3d(expected_cam_mtx[3][0], expected_cam_mtx[3][1], expected_cam_mtx[3][2])
        delta_eye = eye_actual - eye_expected
        perp = delta_eye - forward * Gf.Dot(delta_eye, forward)  # component off the view ray
        self.assertAlmostEqual(perp.GetLength(), 0.0, delta=1e-2)

        await self.finalize_test(golden_img_name="test_frame_button.png")

    async def test_tooltips(self):
        def get_tooltip_widget():
            return ui_test.find("Viewport//Frame/**/Label[*].name=='shortcut'")

        look_tooltip = get_tooltip_widget()
        self.assertIsNone(look_tooltip)

        ViewportNavigationTooltip.set_visible(True)
        # Test look tooltip
        await self._look_button.right_click()
        await omni.kit.app.get_app().next_update_async()
        look_tooltip = get_tooltip_widget()
        self.assertEqual(look_tooltip.widget.text, "Drag")

        # Test pan tooltip
        await self._pan_button.right_click()
        await omni.kit.app.get_app().next_update_async()
        pan_tooltip = get_tooltip_widget()
        self.assertEqual(pan_tooltip.widget.text, "Drag")

        # Test frame tooltip
        await self._frame_button.right_click()
        await omni.kit.app.get_app().next_update_async()
        frame_tooltip = ui_test.find("Viewport//Frame/**/Label[*].name=='keyboard'")
        self.assertEqual(frame_tooltip.widget.text, "F")

        # Test orbit tooltip
        await self._orbit_button.right_click()
        await omni.kit.app.get_app().next_update_async()
        orbit_tooltip = get_tooltip_widget()
        self.assertEqual(orbit_tooltip.widget.text, "ALT")

        # Test dolly tooltip
        await self._dolly_button.right_click()
        await omni.kit.app.get_app().next_update_async()
        dolly_tooltip = get_tooltip_widget()
        self.assertEqual(dolly_tooltip.widget.text, "Scroll")

    async def test_ndc_scale_clamping(self):
        """
        Test that _clamp_ndc_scale correctly enforces minimum absolute values
        on ndc_scale components to prevent the dolly infinity-point freeze.
        """
        from ..gesture.gestures import _clamp_ndc_scale

        min_mag = self._settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or 1.0
        max_mag = self._settings.get(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE)
        self.assertIsNotNone(max_mag)
        oversized_mag = max_mag + 500.0
        within_max_mag = max(min_mag, max_mag * 0.6)
        sub_min_mag = min_mag * 0.05

        # Normal values should pass through unchanged
        normal = [-1092.0, -562.0, -827.0]
        result = _clamp_ndc_scale(normal)
        self.assertEqual(result, normal)

        # Tiny values should be clamped to minimum magnitude while preserving sign
        tiny = [-(sub_min_mag * 0.1), -(sub_min_mag * 0.05), -(sub_min_mag * 0.075)]
        result = _clamp_ndc_scale(tiny)
        for v in result:
            self.assertGreaterEqual(abs(v), min_mag)
            self.assertLess(v, 0)

        # Mixed: only the small component should be clamped
        mixed = [-1092.0, -sub_min_mag, -546.0]
        result = _clamp_ndc_scale(mixed)
        self.assertEqual(result[0], -1092.0)
        self.assertEqual(result[1], -min_mag)
        self.assertEqual(result[2], -546.0)

        # Positive tiny values: sign should be preserved as positive
        pos_tiny = [sub_min_mag * 0.1, sub_min_mag * 0.05, sub_min_mag * 0.075]
        result = _clamp_ndc_scale(pos_tiny)
        for v in result:
            self.assertGreater(v, 0)
            self.assertGreaterEqual(v, min_mag)

        # Oversized values should be clamped to the configured max magnitude
        oversized = [-oversized_mag, within_max_mag, sub_min_mag]
        result = _clamp_ndc_scale(oversized)
        self.assertEqual(result[0], -max_mag)
        self.assertEqual(result[1], within_max_mag)
        self.assertEqual(result[2], min_mag)

        # None / empty should pass through
        self.assertIsNone(_clamp_ndc_scale(None))

    async def test_navigation_max_magnitude_setting(self):
        """
        Test that the max clamp magnitude is configurable via settings.
        """
        from ..gesture.gestures import _clamp_components

        min_mag = self._settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or 1.0
        original_max_mag = self._settings.get(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE)
        self.assertIsNotNone(original_max_mag)

        try:
            configured_max_mag = max(min_mag, original_max_mag * 0.75)
            oversized_mag = configured_max_mag + 1000.0
            within_max_mag = max(min_mag, configured_max_mag * 0.8)
            sub_min_mag = min_mag * 0.05
            self._settings.set(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE, configured_max_mag)
            result = _clamp_components([oversized_mag, -oversized_mag, within_max_mag])
            self.assertEqual(result[0], configured_max_mag)
            self.assertEqual(result[1], -configured_max_mag)
            self.assertEqual(result[2], within_max_mag)

            result = _clamp_components([oversized_mag, -oversized_mag, sub_min_mag])
            self.assertEqual(result[0], configured_max_mag)
            self.assertEqual(result[1], -configured_max_mag)
            self.assertEqual(result[2], min_mag)
        finally:
            self._settings.set(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE, original_max_mag)

    async def test_world_speed_clamping(self):
        """
        Test that final world_speed also gets clamped so Pan/Dolly do not stall
        when the composed speed becomes extremely small.
        """
        from ..gesture.gestures import _clamp_world_speed

        min_mag = self._settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or 1.0
        max_mag = self._settings.get(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE)
        self.assertIsNotNone(max_mag)
        oversized_mag = max_mag + 500.0
        within_max_mag = max(min_mag, max_mag * 0.75)
        sub_min_mag = min_mag * 0.05

        # Normal values should pass through unchanged
        normal = Gf.Vec3d(-1092.0, -562.0, -827.0)
        result = _clamp_world_speed(normal)
        self.assertAlmostEqual(result, normal)

        # Tiny values should be clamped to minimum magnitude while preserving sign
        tiny = Gf.Vec3d(-(sub_min_mag * 0.1), -(sub_min_mag * 0.05), -(sub_min_mag * 0.075))
        result = _clamp_world_speed(tiny)
        for v in result:
            self.assertGreaterEqual(abs(v), min_mag)
            self.assertLess(v, 0)

        # Mixed values should only clamp the tiny components
        mixed = Gf.Vec3d(0.0, -sub_min_mag, 546.0)
        result = _clamp_world_speed(mixed)
        self.assertEqual(result[0], min_mag)
        self.assertEqual(result[1], -min_mag)
        self.assertEqual(result[2], 546.0)

        # Oversized values should clamp to the configured maximum magnitude
        oversized = Gf.Vec3d(oversized_mag, -(oversized_mag + 500.0), within_max_mag)
        result = _clamp_world_speed(oversized)
        self.assertEqual(result[0], max_mag)
        self.assertEqual(result[1], -max_mag)
        self.assertEqual(result[2], within_max_mag)

        # None should pass through
        self.assertIsNone(_clamp_world_speed(None))

    async def test_dolly_infinity_point_recovery(self):
        """
        Test that Dolly and Pan remain usable after the camera's
        center-of-interest distance becomes very small.

        Reproduces the 'infinity point' bug where the user dollies very close
        to an object, causing ndc_scale to approach zero. After the fix,
        both Dolly and Pan should still produce visible camera movement.
        """
        await self._setup_scene()

        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        stage = viewport_api.stage
        cam_prim = stage.GetPrimAtPath(cam_path)
        cam_mtx_to_restore = viewport_api.transform

        coi_attr_path = cam_path.AppendProperty("omni:kit:centerOfInterest")
        tiny_coi = Gf.Vec3d(0, 0, -0.005)

        async def set_tiny_coi():
            omni.kit.commands.execute(
                "ChangePropertyCommand",
                prop_path=coi_attr_path,
                value=tiny_coi,
                prev=cam_prim.GetAttribute("omni:kit:centerOfInterest").Get(),
            )
            await omni.kit.app.get_app().next_update_async()

        # --- Dolly with very small COI ---
        await set_tiny_coi()

        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "dolly":
            await self._dolly_button.click()
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        cam_before = self._get_cam_mtx()
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(180, 100), ui_test.Vec2(100, 100))
        await omni.kit.app.get_app().next_update_async()
        cam_after = self._get_cam_mtx()

        self.assertFalse(
            Gf.IsClose(cam_before, cam_after, 1e-6),
            "Dolly should produce camera movement even with very small COI",
        )

        # --- Reset for Pan test ---
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, "none")
        await omni.kit.app.get_app().next_update_async()
        await self.reset_camera(cam_path, cam_mtx_to_restore)
        await set_tiny_coi()

        # --- Pan with very small COI ---
        if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "pan":
            await self._pan_button.click()
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        cam_before = self._get_cam_mtx()
        await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(100, 100), ui_test.Vec2(200, 100))
        await omni.kit.app.get_app().next_update_async()
        cam_after = self._get_cam_mtx()

        self.assertFalse(
            Gf.IsClose(cam_before, cam_after, 1e-6),
            "Pan should produce camera movement even with very small COI",
        )

    async def test_dolly_normal_speed_respects_max_navigation_magnitude(self):
        """
        Test that Dolly motion at normal distances responds to the
        maxNavigationMagnitude setting.
        """
        await self._setup_scene()

        viewport_api, _ = get_active_viewport_and_window()
        cam_path = viewport_api.camera_path
        cam_mtx_to_restore = viewport_api.transform
        cam_prim = viewport_api.stage.GetPrimAtPath(viewport_api.camera_path)

        coi = cam_prim.GetAttribute("omni:kit:centerOfInterest").Get()
        self.assertGreater(coi.GetLength(), 1.0, "Setup scene should have a normal COI distance")
        min_mag = self._settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or 1.0

        def _translation_delta(before, after):
            return (
                (after[3][0] - before[3][0]) ** 2
                + (after[3][1] - before[3][1]) ** 2
                + (after[3][2] - before[3][2]) ** 2
            ) ** 0.5

        async def _run_dolly_with_max(max_mag):
            self._settings.set(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE, max_mag)
            self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, "none")
            await omni.kit.app.get_app().next_update_async()
            await self.reset_camera(cam_path, cam_mtx_to_restore)

            if self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) != "dolly":
                await self._dolly_button.click()
                await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            cam_before = self._get_cam_mtx()
            await ui_test.emulate_mouse_drag_and_drop(ui_test.Vec2(180, 100), ui_test.Vec2(100, 100))
            await omni.kit.app.get_app().next_update_async()
            cam_after = self._get_cam_mtx()
            return _translation_delta(cam_before, cam_after)

        original_max_mag = self._settings.get(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE)
        self.assertIsNotNone(original_max_mag)
        try:
            reduced_max_mag = max(min_mag, original_max_mag * 0.25)
            default_delta = await _run_dolly_with_max(original_max_mag)
            reduced_delta = await _run_dolly_with_max(reduced_max_mag)

            self.assertGreater(default_delta, 0.0, "Dolly should move the camera with the configured max magnitude")
            self.assertGreater(reduced_delta, 0.0, "Dolly should still move the camera with a lower max magnitude")
            self.assertLess(
                reduced_delta,
                default_delta,
                "Reducing maxNavigationMagnitude should reduce Dolly movement",
            )
        finally:
            self._settings.set(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE, original_max_mag)

    async def test_delay_execute(self):
        res = [0]

        def test(res):
            res.append(1)
            return True

        import functools

        delay_obj = delay_execute_by_frame(1, functools.partial(test, res), "test")
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(res, [0, 1])
        delay_obj = None
