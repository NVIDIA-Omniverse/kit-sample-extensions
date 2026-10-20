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

import carb
import omni.appwindow as appwindow
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.sample.gesture_viewport.line import LineManipulator
from omni.ui import scene as sc

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add support for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
# Import extension python module we are testing with absolute import path, as if we are an external user (other extension)
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.sample.gesture_viewport}/data"))
GOLDEN_IMG_DIR = CURRENT_PATH / "tests"


def _flatten_matrix(matrix: Gf.Matrix4d):
    return [
        matrix[0][0],
        matrix[0][1],
        matrix[0][2],
        matrix[0][3],
        matrix[1][0],
        matrix[1][1],
        matrix[1][2],
        matrix[1][3],
        matrix[2][0],
        matrix[2][1],
        matrix[2][2],
        matrix[2][3],
        matrix[3][0],
        matrix[3][1],
        matrix[3][2],
        matrix[3][3],
    ]


class TestGestureViewport(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._saved_mouse_input_blocking_state = None

    # After running each test
    async def tearDown(self):
        # Restore the mouse input-blocking state if it was saved
        if self._saved_mouse_input_blocking_state is not None:
            app_window = appwindow.get_default_app_window()
            app_window.set_input_blocking_state(carb.input.DeviceType.MOUSE, self._saved_mouse_input_blocking_state)
        await super().tearDown()

    async def setup_test_area_and_input(self, title: str, width: int = 256, height: int = 256):
        self.__width, self.__height = width, height
        await self.create_test_area(width=width, height=height)
        app_window = appwindow.get_default_app_window()
        # Save the current mouse input-blocking state before modifying it
        self._saved_mouse_input_blocking_state = app_window.get_input_blocking_state(carb.input.DeviceType.MOUSE)
        app_window.set_input_blocking_state(carb.input.DeviceType.MOUSE, False)
        return ui.Window(
            title=title,
            width=width,
            height=height,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_MOVE,
        )

    async def create_perspective_scene_view(self, title="test", width=256, height=256, field_of_view=25, distance=100):
        window = await self.setup_test_area_and_input(title, width, height)

        with window.frame:
            # Camera matrices
            projection = self.perspective_projection(field_of_view)
            eye = Gf.Vec3d(distance, distance, distance)
            target = Gf.Vec3d(0, 0, 0)
            forward = (target - eye).GetNormalized()
            up = Gf.Vec3d(0, 0, 1).GetComplement(forward)
            view = _flatten_matrix(Gf.Matrix4d().SetLookAt(eye, target, up))
            scene_view = sc.SceneView(
                aspect_ratio_policy=sc.AspectRatioPolicy.STRETCH, model=sc.CameraModel(projection, view)
            )

            return window, scene_view

    def perspective_projection(
        self, field_of_view: float = 20, aspect_ratio: float = None, near: float = 0.001, far: float = 10000
    ):
        if aspect_ratio is None:
            aspect_ratio = self.__width / self.__height

        frustum = Gf.Frustum()
        frustum.SetPerspective(field_of_view / aspect_ratio, aspect_ratio, near, far)
        return _flatten_matrix(frustum.ComputeProjectionMatrix())

    async def test_gesture_viewport_visual(self):
        """Test the visual rendering of the LineManipulator in the viewport."""

        window, scene_view = await self.create_perspective_scene_view(
            "test_gesture_viewport_visual", width=800, height=600
        )
        with scene_view.scene:
            LineManipulator(line_size=10, up_axis="Z")

        # Allow sufficient frames for the scene to fully render
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(threshold=10, golden_img_dir=GOLDEN_IMG_DIR, golden_img_name="general.png")

    async def test_click_gesture(self):
        """Test click and double-click gestures on the LineManipulator."""

        window, scene_view = await self.create_perspective_scene_view("test_click_gesture", width=800, height=600)
        with scene_view.scene:
            LineManipulator(line_size=10, up_axis="Z")

        mouse_pos = ui_test.Vec2(self.__width / 2, self.__height / 2)
        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay()

        # Click gesture
        await ui_test.input.emulate_mouse_click()
        await ui_test.human_delay(10)
        await self.capture_and_compare(
            golden_img_dir=GOLDEN_IMG_DIR, golden_img_name="click_gesture.png", test_name="test_click_gesture"
        )
        await ui_test.human_delay(20)
        # Double click gesture
        await ui_test.input.emulate_mouse_click(double=True)
        await ui_test.human_delay(10)
        await self.capture_and_compare(
            golden_img_dir=GOLDEN_IMG_DIR, golden_img_name="general.png", test_name="double_click_gesture"
        )

    async def test_drag_gesture(self):
        """Test drag gesture functionality of the LineManipulator."""

        window, scene_view = await self.create_perspective_scene_view("test_drag_gesture", width=800, height=600)
        with scene_view.scene:
            LineManipulator(line_size=10, up_axis="Z")

        mouse_pos = ui_test.Vec2(self.__width / 2, self.__height / 2)
        await ui_test.emulate_mouse_move(mouse_pos)
        await ui_test.human_delay()

        # Drag gesture
        await ui_test.input.emulate_mouse_drag_and_drop(mouse_pos, mouse_pos + ui_test.Vec2(200, 0))
        await ui_test.human_delay(10)
        await self.finalize_test(
            threshold=10,
            golden_img_dir=GOLDEN_IMG_DIR,
            golden_img_name="drag_gesture.png",
            test_name="test_drag_gesture",
        )
