# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import logging
import math
from pathlib import Path
from typing import List

import carb
import carb.input
import carb.settings
import omni.kit.commands
import omni.kit.ui_test as ui_test
import omni.kit.undo
import omni.usd
from omni.kit.manipulator.tool.snap import settings_constants as snap_c
from omni.kit.manipulator.tool.snap.builtin_snap_tools import SURFACE_SNAP_NAME
from omni.kit.manipulator.transform.settings_constants import Constants
from omni.kit.ui_test import Vec2
from omni.kit.viewport.utility import get_active_viewport_and_window
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, UsdGeom

from ..bindings import CurveEditingModeType
from ..scripts.bezier_curve_edits_context import BezierCurveEditsContextManager

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.curve.manipulator}/data"))
CAMERA_PATH = "/Camera"
CURVE_PATH = "/BasisCurves"

logger = logging.getLogger(__name__)

# This file contains the interactive manipulation tests for BezierCurveEdits
# It mimics user inputs inside of Viewport to create/manipulate/edit curves.
# If you need to add tests that does not involve viewport or user inputs, use test_curve_edits.py instead


class KeyDownScope:
    def __init__(self, key: carb.input.KeyboardInput, modifier: carb.input.KeyboardInput = 0):
        self._key = key
        self._modifier = modifier

    async def __aenter__(self):
        if self._key:
            await ui_test.human_delay()
            await ui_test.input.emulate_keyboard(carb.input.KeyboardEventType.KEY_PRESS, self._key, self._modifier)
            await ui_test.human_delay()

    async def __aexit__(self, exc_type, exc, tb):
        if self._key:
            await ui_test.human_delay()
            await ui_test.input.emulate_keyboard(carb.input.KeyboardEventType.KEY_RELEASE, self._key, 0)
            await ui_test.human_delay()


class TestCreation(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._context = omni.usd.get_context()
        self._selection = self._context.get_selection()
        self._settings = carb.settings.get_settings()
        self._curve_edits_context = BezierCurveEditsContextManager.get_context()
        self._key_edit_curve = 0
        self._key_append_curve = carb.input.KeyboardInput.LEFT_SHIFT

        await self._context.new_stage_async()
        self._stage = self._context.get_stage()

        self.assertIsNotNone(self._stage)

        self._settings.set(snap_c.SNAP_PROVIDER_NAME_SETTING_PATH, [])
        self._settings.set("/app/viewport/snapEnabled", False)
        self._settings.set("/persistent/app/viewport/snapToSurface", False)

        camera: UsdGeom.Camera = UsdGeom.Camera.Define(self._stage, CAMERA_PATH)
        camera.GetProjectionAttr().Set(UsdGeom.Tokens.orthographic)
        camera.GetHorizontalApertureAttr().Set(2000)
        camera.GetVerticalApertureAttr().Set(2000)

        api = UsdGeom.XformCommonAPI(camera)
        api.SetTranslate((0, 500, 0))
        api.SetRotate(Gf.Vec3f(90, 0, -180))

        await self._setup_viewport()

        # move the mouse out of the way
        await ui_test.emulate_mouse_move(Vec2(0, 0))
        await ui_test.human_delay()

    async def _setup_viewport(self):
        viewport_api, viewport_window = get_active_viewport_and_window()
        if viewport_window and viewport_api:
            viewport_api.camera_path = CAMERA_PATH
        else:
            self.assertTrue(False, "viewport_api or viewport_window is None")

        await viewport_api.wait_for_rendered_frames(2)

        try:
            await omni.kit.app.get_app().next_update_async()
            import omni.kit.viewport_legacy as legacy_vp

            legacy_vp.acquire_viewport_interface()
            self._key_edit_curve = carb.input.KeyboardInput.LEFT_SHIFT
            self._key_append_curve = carb.input.KeyboardInput.LEFT_ALT
        except:
            pass

    # After running each test
    async def tearDown(self):
        await self._context.close_stage_async()
        await super().tearDown()

    async def _test_bezier_tool_impl(self, expected: List[Gf.Vec3f], tolerance=1e-6, ignore_first=False):
        self._curve_edits_context.curve_edits.create_new_bezier_curve_and_edit(mode=CurveEditingModeType.DRAG)

        await ui_test.human_delay()

        async with KeyDownScope(self._key_edit_curve, self._key_edit_curve):
            # drag twice to create a curve with 4 cv
            await ui_test.emulate_mouse_drag_and_drop(Vec2(100, 200), Vec2(100, 300))
            await ui_test.input.emulate_mouse_slow_move(Vec2(100, 300), Vec2(300, 200))
            await ui_test.human_delay(10)  # must wait, otherwise VP1 snap goes nuts
            await ui_test.emulate_mouse_drag_and_drop(Vec2(300, 200), Vec2(300, 100))

        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)

        basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH)
        self.assertTrue(basis_curves.GetPrim().IsValid())

        points = basis_curves.GetPointsAttr().Get()

        self.assertEqual(len(points), len(expected))
        for i in range(len(points)):
            # a workaround for nondeterministic snap result of first frame in VP1
            if i == 0 and ignore_first:
                continue
            self.assertTrue(Gf.IsClose(points[i], expected[i], tolerance), f"{points[i]} is not close to {expected[i]}")

    async def test_bezier_tool_no_snap(self):
        expected = [Gf.Vec3f(50, 0, 0), Gf.Vec3f(50, 0, -50), Gf.Vec3f(-50, 0, -50), Gf.Vec3f(-50, 0, 0)]
        await self._test_bezier_tool_impl(expected)

    async def test_bezier_tool_snap(self):
        self._settings.set(snap_c.SNAP_PROVIDER_NAME_SETTING_PATH, [SURFACE_SNAP_NAME])
        self._settings.set("/app/viewport/snapEnabled", True)
        self._settings.set("/persistent/app/viewport/snapToSurface", True)

        omni.kit.commands.execute("CreateMeshPrimWithDefaultXformCommand", prim_type="Plane")
        omni.kit.commands.execute(
            "TransformPrimSRT", path="/Plane", new_scale=(10, 10, 10), new_translation=(0, -100, 0)
        )

        await ui_test.human_delay()

        expected = [Gf.Vec3f(50, -100, 0), Gf.Vec3f(50, -100, -50), Gf.Vec3f(-50, -100, -50), Gf.Vec3f(-50, -100, 0)]
        await self._test_bezier_tool_impl(expected, 1, ignore_first=True)

        self._settings.set("/app/viewport/snapEnabled", False)
        self._settings.set("/persistent/app/viewport/snapToSurface", False)

    async def test_cubic_pencil_tool(self):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode", "cubic")
        expected = [
            Gf.Vec3f(50, 0, 0),
            Gf.Vec3f(47.5, 0, 0),
            Gf.Vec3f(42.5, 0, 0),
            Gf.Vec3f(40, 0, 0),
            Gf.Vec3f(37.5, 0, 0),
            Gf.Vec3f(32.5, 0, 0),
            Gf.Vec3f(30, 0, 0),
            Gf.Vec3f(27.5, 0, 0),
            Gf.Vec3f(22.5, 0, 0),
            Gf.Vec3f(20, 0, 0),
            Gf.Vec3f(17.5, 0, 0),
            Gf.Vec3f(12.5, 0, 0),
            Gf.Vec3f(10, 0, 0),
            Gf.Vec3f(7.5, 0, 0),
            Gf.Vec3f(2.5, 0, 0),
            Gf.Vec3f(0, 0, 0),
            Gf.Vec3f(-2.5, 0, 0),
            Gf.Vec3f(-7.5, 0, 0),
            Gf.Vec3f(-10, 0, 0),
            Gf.Vec3f(-12.5, 0, 0),
            Gf.Vec3f(-17.5, 0, 0),
            Gf.Vec3f(-20, 0, 0),
            Gf.Vec3f(-22.5, 0, 0),
            Gf.Vec3f(-27.5, 0, 0),
            Gf.Vec3f(-30, 0, 0),
            Gf.Vec3f(-32.5, 0, 0),
            Gf.Vec3f(-37.5, 0, 0),
            Gf.Vec3f(-40, 0, 0),
            Gf.Vec3f(-42.5, 0, 0),
            Gf.Vec3f(-47.5, 0, 0),
            Gf.Vec3f(-50, 0, 0),
        ]
        await self._test_pencil_tool_impl(expected)

    async def test_linear_pencil_tool(self):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode", "linear")
        expected = [
            Gf.Vec3f(50, 0, 0),
            Gf.Vec3f(40, 0, 0),
            Gf.Vec3f(30, 0, 0),
            Gf.Vec3f(20, 0, 0),
            Gf.Vec3f(10, 0, 0),
            Gf.Vec3f(0, 0, 0),
            Gf.Vec3f(-10, 0, 0),
            Gf.Vec3f(-20, 0, 0),
            Gf.Vec3f(-30, 0, 0),
            Gf.Vec3f(-40, 0, 0),
            Gf.Vec3f(-50, 0, 0),
        ]
        await self._test_pencil_tool_impl(expected)

    # OM-103175
    async def test_linear_pencil_tool_rotated(self):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode", "linear")
        expected = [
            Gf.Vec3f(-50, 0, 0),
            Gf.Vec3f(-40, 0, 0),
            Gf.Vec3f(-30, 0, 0),
            Gf.Vec3f(-20, 0, 0),
            Gf.Vec3f(-10, 0, 0),
            Gf.Vec3f(0, 0, 0),
            Gf.Vec3f(10, 0, 0),
            Gf.Vec3f(20, 0, 0),
            Gf.Vec3f(30, 0, 0),
            Gf.Vec3f(40, 0, 0),
            Gf.Vec3f(50, 0, 0),
        ]
        await self._test_pencil_tool_impl(expected, True)

    async def test_linear_pencil_tool_multi_curve(self):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode", "linear")
        expected1 = [
            Gf.Vec3f(50, 0, 25),
            Gf.Vec3f(40, 0, 25),
            Gf.Vec3f(30, 0, 25),
            Gf.Vec3f(20, 0, 25),
            Gf.Vec3f(10, 0, 25),
            Gf.Vec3f(0, 0, 25),
            Gf.Vec3f(-10, 0, 25),
            Gf.Vec3f(-20, 0, 25),
            Gf.Vec3f(-30, 0, 25),
            Gf.Vec3f(-40, 0, 25),
            Gf.Vec3f(-50, 0, 25),
        ]
        expected2 = [
            Gf.Vec3f(50, 0, -25),
            Gf.Vec3f(40, 0, -25),
            Gf.Vec3f(30, 0, -25),
            Gf.Vec3f(20, 0, -25),
            Gf.Vec3f(10, 0, -25),
            Gf.Vec3f(0, 0, -25),
            Gf.Vec3f(-10, 0, -25),
            Gf.Vec3f(-20, 0, -25),
            Gf.Vec3f(-30, 0, -25),
            Gf.Vec3f(-40, 0, -25),
            Gf.Vec3f(-50, 0, -25),
        ]
        await self._test_pencil_tool_multi_curve_impl(expected1, expected2)

    async def _test_pencil_tool_impl(self, expected: List[Gf.Vec3f], rotate_curve_prim: bool = False):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolSpacing", 10)
        self._curve_edits_context.curve_edits.create_new_bezier_curve_and_edit(mode=CurveEditingModeType.DRAW)

        basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH)
        self.assertIsNotNone(basis_curves)

        if rotate_curve_prim:
            UsdGeom.XformCommonAPI(basis_curves.GetPrim()).SetRotate(Gf.Vec3f(0, 180, 0))

        await ui_test.human_delay()

        async with KeyDownScope(self._key_edit_curve, self._key_edit_curve):
            # draw a line
            await ui_test.emulate_mouse_drag_and_drop(Vec2(100, 200), Vec2(300, 200))

        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)

        points = basis_curves.GetPointsAttr().Get()
        self.assertEqual(len(points), len(expected))
        for i in range(len(points)):
            self.assertTrue(Gf.IsClose(points[i], expected[i], 1e-6))

    async def _test_pencil_tool_multi_curve_impl(self, expected1: List[Gf.Vec3f], expected2: List[Gf.Vec3f]):
        self._settings.set("/persistent/exts/omni.curve.manipulator/pencilToolSpacing", 10)
        self._curve_edits_context.curve_edits.create_new_bezier_curve_and_edit(mode=CurveEditingModeType.DRAW)

        await ui_test.human_delay()
        if self._key_edit_curve:
            await ui_test.input.emulate_keyboard(
                carb.input.KeyboardEventType.KEY_PRESS, self._key_edit_curve, self._key_edit_curve
            )
            await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(Vec2(100, 150), Vec2(300, 150))
        await ui_test.human_delay()
        if self._key_edit_curve:
            await ui_test.input.emulate_keyboard(
                carb.input.KeyboardEventType.KEY_PRESS, self._key_append_curve, self._key_edit_curve
            )
            await ui_test.human_delay()
        else:
            await ui_test.input.emulate_keyboard(
                carb.input.KeyboardEventType.KEY_PRESS, self._key_append_curve, self._key_append_curve
            )
            await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(Vec2(100, 250), Vec2(300, 250))
        await ui_test.human_delay()
        await ui_test.input.emulate_keyboard(carb.input.KeyboardEventType.KEY_RELEASE, self._key_append_curve)
        await ui_test.human_delay()
        if self._key_edit_curve:
            await ui_test.input.emulate_keyboard(carb.input.KeyboardEventType.KEY_RELEASE, self._key_edit_curve)
            await ui_test.human_delay()

        await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ENTER)

        basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH)
        self.assertIsNotNone(basis_curves)

        points = basis_curves.GetPointsAttr().Get()
        self.assertEqual(len(points), len(expected1) + len(expected2))

        vertexCounts = basis_curves.GetCurveVertexCountsAttr().Get()
        self.assertEqual(len(vertexCounts), 2)
        self.assertEqual(vertexCounts[0], len(expected1))
        self.assertEqual(vertexCounts[1], len(expected2))

        for i in range(len(points)):
            if i < len(expected1):
                self.assertTrue(Gf.IsClose(points[i], expected1[i], 1e-6))
            else:
                self.assertTrue(Gf.IsClose(points[i], expected2[i - len(expected1)], 1e-6))


CURVE_PATH2 = "/World/BasisCurves"


class TestManipulation(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._input = carb.input.acquire_input_interface()
        self._context = omni.usd.get_context()
        self._selection = self._context.get_selection()
        self._settings = carb.settings.get_settings()
        self._usd_scene_dir = CURRENT_PATH.absolute().resolve().joinpath("tests").joinpath("usd")
        self._curve_edits_context = BezierCurveEditsContextManager.get_context()
        self._curve_edits = self._curve_edits_context.curve_edits
        usd_path = self._usd_scene_dir.joinpath("test_scene.usda")

        self._settings.set("/app/viewport/snapEnabled", False)
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SELECT)

        await self._context.open_stage_async(str(usd_path))
        self._stage = self._context.get_stage()

        self.assertIsNotNone(self._stage)

        await ui_test.human_delay()

        self._basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH2)

        omni.kit.commands.execute(
            "EnableCurveEditing",
            curve_context=self._curve_edits_context.curve_edits.curve_context,
            paths=[CURVE_PATH2],
            mode=CurveEditingModeType.DRAG,
        )

        await ui_test.human_delay()

    # After running each test
    async def tearDown(self):
        await self._context.close_stage_async()
        await super().tearDown()

    def _compare_points(self, points, expected):
        try:
            self.assertEqual(len(points), len(expected))
            for i in range(len(points)):
                self.assertTrue(Gf.IsClose(points[i], expected[i], 1e-1))
        except AssertionError as e:
            carb.log_error(f"{points} is not close to expected {expected}")
            raise e

    async def _click_and_drag_test(self, start: Vec2, end: Vec2, expected):
        points_attr = self._basis_curves.GetPointsAttr()

        await ui_test.emulate_mouse_move_and_click(start, human_delay_speed=30)
        await ui_test.emulate_mouse_drag_and_drop(start, end, human_delay_speed=5)
        points = points_attr.Get()
        self._compare_points(points, expected)

        omni.kit.undo.undo()
        await ui_test.human_delay(5)

    # 2025-12-12: Failing on Kit 110 - temporarily disable until Jihui returns!
    # async def test_translate(self):
    #     self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_MOVE)
    #     await ui_test.human_delay()

    #     half_sqrt_2 = math.sqrt(2) * 0.5

    #     # 1) test translate anchor, anchor and both tangents move
    #     expected = [(50, 0, -50), (50, 0, 0), (50, 0, 0), (0, 0, 0), (-50, 0, 0), (-50, 0, 0), (-50, 0, -50)]
    #     await self._click_and_drag_test(Vec2(200, 100), Vec2(200, 200), expected)

    #     # 2) test translate tangent, both tangents move, but in opposite direction
    #     expected = [(50, 0, -50), (50, 0, 0), (50, 0, 0), (0, 0, 50), (-50, 0, 100), (-50, 0, 0), (-50, 0, -50)]
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 3) break tangent and move, only one tangent moves
    #     self._curve_edits.break_tangents(self._basis_curves, [3])
    #     expected = [(50, 0, -50), (50, 0, 0), (50, 0, 0), (0, 0, 50), (-50, 0, 50), (-50, 0, 0), (-50, 0, -50)]
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 4) restore smooth and even tangents to 2)
    #     self._curve_edits.smooth_tangents(self._basis_curves, [3])
    #     self._curve_edits.even_tangents(self._basis_curves, [3])
    #     expected = [(50, 0, -50), (50, 0, 0), (50, 0, 0), (0, 0, 50), (-50, 0, 100), (-50, 0, 0), (-50, 0, -50)]
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 5) uneven tangent
    #     self._curve_edits.uneven_tangents(self._basis_curves, [3])
    #     expected = [
    #         (50, 0, -50),
    #         (50, 0, 0),
    #         (50, 0, 0),
    #         (0, 0, 50),
    #         (-50 * half_sqrt_2, 0, 50 + 50 * half_sqrt_2),
    #         (-50, 0, 0),
    #         (-50, 0, -50),
    #     ]
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    async def test_rotate(self):
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_ROTATE)
        await ui_test.human_delay()

        expected = [(50, 0, -50), (50, 0, 0), (-50, 0, 50), (0, 0, 50), (50, 0, 50), (-50, 0, 0), (-50, 0, -50)]

        ARC_RADIUS = 80
        await ui_test.emulate_mouse_move_and_click(Vec2(200, 100), human_delay_speed=30)
        await self._click_and_drag_test(Vec2(200 - ARC_RADIUS, 100), Vec2(200 + ARC_RADIUS, 100), expected)

    async def test_scale(self):
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SCALE)
        await ui_test.human_delay()

        expected = [(50, 0, -50), (50, 0, 0), (-50, 0, 50), (0, 0, 50), (50, 0, 50), (-50, 0, 0), (-50, 0, -50)]
        await self._click_and_drag_test(Vec2(200, 100), Vec2(200, 200), expected)

    async def test_marquee(self):
        cv_selection = self._curve_edits_context.selection

        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SELECT)

        await ui_test.emulate_mouse_drag_and_drop(Vec2(50, 50), Vec2(350, 150))
        selected_id = cv_selection.get_selected_ids(self._basis_curves)
        self.assertEqual(selected_id, {2, 3, 4})

        await ui_test.human_delay(human_delay_speed=30)

        # ctrl + drag: invert selection
        async with KeyDownScope(carb.input.KeyboardInput.LEFT_CONTROL, carb.input.KeyboardInput.LEFT_CONTROL):
            await ui_test.emulate_mouse_drag_and_drop(Vec2(50, 50), Vec2(350, 350))
        selected_id = cv_selection.get_selected_ids(self._basis_curves)
        self.assertEqual(selected_id, {0, 1, 5, 6})

        await ui_test.human_delay(human_delay_speed=30)

        # ctrl + shift + drag: combine selection
        async with KeyDownScope(carb.input.KeyboardInput.LEFT_CONTROL):
            async with KeyDownScope(carb.input.KeyboardInput.LEFT_SHIFT, carb.input.KeyboardInput.LEFT_CONTROL):
                await ui_test.emulate_mouse_drag_and_drop(Vec2(50, 50), Vec2(350, 350))
        selected_id = cv_selection.get_selected_ids(self._basis_curves)
        self.assertEqual(selected_id, {0, 1, 2, 3, 4, 5, 6})

        await ui_test.human_delay(human_delay_speed=30)

        self.assertEqual(self._input.get_keyboard_value(None, carb.input.KeyboardInput.LEFT_CONTROL), 0)
        self.assertEqual(self._input.get_keyboard_value(None, carb.input.KeyboardInput.LEFT_SHIFT), 0)

        # do a reset select again
        await ui_test.emulate_mouse_drag_and_drop(Vec2(50, 50), Vec2(350, 150))
        selected_id = cv_selection.get_selected_ids(self._basis_curves)
        self.assertEqual(selected_id, {2, 3, 4})

    async def test_cv_edits(self):
        half_sqrt_2 = math.sqrt(2) * 0.5
        points_attr = self._basis_curves.GetPointsAttr()

        # make a corner
        self._curve_edits.corner(self._basis_curves, [3])
        expected = [(50, 0, -50), (50, 0, 0), (0, 0, 50), (0, 0, 50), (0, 0, 50), (-50, 0, 0), (-50, 0, -50)]
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

        # make a bezier corner
        self._curve_edits.bezier_corner(self._basis_curves, [3])
        expected = [(50, 0, -50), (50, 0, 0), (25, 0, 25), (0, 0, 50), (-25, 0, 25), (-50, 0, 0), (-50, 0, -50)]
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

        # make bezier
        self._curve_edits.bezier(self._basis_curves, [3])
        expected = (
            (50, 0, -50),
            (50, 0, 0),
            (50 * half_sqrt_2, 0, 50),
            (0, 0, 50),
            (-50 * half_sqrt_2, 0, 50),
            (-50, 0, 0),
            (-50, 0, -50),
        )
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

    async def test_open_close_curve(self):
        points_attr = self._basis_curves.GetPointsAttr()
        wrap_attr = self._basis_curves.GetWrapAttr()

        # close curve
        self._curve_edits.open_close_curve(self._basis_curves)
        expected = [
            (50, 0, -50),
            (50, 0, 0),
            (50, 0, 50),
            (0, 0, 50),
            (-50, 0, 50),
            (-50, 0, 0),
            (-50, 0, -50),
            (-50, 0, -100),
            (50, 0, -100),
        ]
        self._compare_points(points_attr.Get(), expected)
        self.assertEqual(wrap_attr.Get(), UsdGeom.Tokens.periodic)

        await ui_test.human_delay()

        # undo
        omni.kit.undo.undo()
        expected = [(50, 0, -50), (50, 0, 0), (50, 0, 50), (0, 0, 50), (-50, 0, 50), (-50, 0, 0), (-50, 0, -50)]
        self._compare_points(points_attr.Get(), expected)
        self.assertEqual(wrap_attr.Get(), UsdGeom.Tokens.nonperiodic)

        await ui_test.human_delay()

        # redo
        omni.kit.undo.redo()

        await ui_test.human_delay()

        # open curve
        self._curve_edits.open_close_curve(self._basis_curves)
        expected = [(50, 0, -50), (50, 0, 0), (50, 0, 50), (0, 0, 50), (-50, 0, 50), (-50, 0, 0), (-50, 0, -50)]
        self._compare_points(points_attr.Get(), expected)
        self.assertEqual(wrap_attr.Get(), UsdGeom.Tokens.nonperiodic)

        await ui_test.human_delay()

        # undo
        omni.kit.undo.undo()
        expected = [
            (50, 0, -50),
            (50, 0, 0),
            (50, 0, 50),
            (0, 0, 50),
            (-50, 0, 50),
            (-50, 0, 0),
            (-50, 0, -50),
            (-50, 0, -100),
            (50, 0, -100),
        ]
        self._compare_points(points_attr.Get(), expected)
        self.assertEqual(wrap_attr.Get(), UsdGeom.Tokens.periodic)

        await ui_test.human_delay()

    async def test_cv_snap(self):
        start = Vec2(200, 100)
        end = Vec2(200, 200)

        points_attr = self._basis_curves.GetPointsAttr()

        await ui_test.emulate_mouse_move(start, human_delay_speed=30)
        await ui_test.emulate_mouse_click()

        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_MOVE)
        self._settings.set(snap_c.SNAP_PROVIDER_NAME_SETTING_PATH, [SURFACE_SNAP_NAME])
        self._settings.set("/app/viewport/snapEnabled", True)

        await ui_test.human_delay(human_delay_speed=30)

        await ui_test.emulate_mouse_drag_and_drop(start, end, human_delay_speed=1)
        points = points_attr.Get()

        # snap to Y = -100 plane
        for i, point in enumerate(points):
            if i >= 2 and i <= 4:
                self.assertEqual(point[1], -100)
            else:
                self.assertEqual(point[1], 0)

        omni.kit.undo.undo()
        await ui_test.human_delay(5)


class TestPeriodicManipulation(OmniUiTest):
    SHOULD_NOT_CHANGE = [
        (-50, 0, 0),
        (-50, 0, -50),
        (-50, 0, -100),
        (50, 0, -100),
        (50, 0, -50),
        (50, 0, 0),
    ]

    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._input = carb.input.acquire_input_interface()
        self._context = omni.usd.get_context()
        self._selection = self._context.get_selection()
        self._settings = carb.settings.get_settings()
        self._usd_scene_dir = CURRENT_PATH.absolute().resolve().joinpath("tests").joinpath("usd")
        self._curve_edits_context = BezierCurveEditsContextManager.get_context()
        self._curve_edits = self._curve_edits_context.curve_edits
        usd_path = self._usd_scene_dir.joinpath("test_scene_periodic.usda")

        self._settings.set("/app/viewport/snapEnabled", False)
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SELECT)

        await self._context.open_stage_async(str(usd_path))
        self._stage = self._context.get_stage()

        self.assertIsNotNone(self._stage)

        self._key_edit_curve = 0
        self._key_append_curve = carb.input.KeyboardInput.LEFT_SHIFT
        await self._setup_viewport()
        await ui_test.human_delay()

        self._basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH2)

        omni.kit.commands.execute(
            "EnableCurveEditing",
            curve_context=self._curve_edits_context.curve_edits.curve_context,
            paths=[CURVE_PATH2],
            mode=CurveEditingModeType.DRAG,
        )

        await ui_test.human_delay()

    # After running each test
    async def tearDown(self):
        await self._context.close_stage_async()
        await super().tearDown()

    async def _setup_viewport(self):
        viewport_api, viewport_window = get_active_viewport_and_window()
        await viewport_api.wait_for_rendered_frames(2)

        try:
            await omni.kit.app.get_app().next_update_async()
            import omni.kit.viewport_legacy as legacy_vp

            legacy_vp.acquire_viewport_interface()
            self._key_edit_curve = carb.input.KeyboardInput.LEFT_SHIFT
            self._key_append_curve = carb.input.KeyboardInput.LEFT_ALT
        except:
            pass

    def _compare_points(self, points, expected):
        try:
            self.assertEqual(len(points), len(expected))
            for i in range(len(points)):
                self.assertTrue(Gf.IsClose(points[i], expected[i], 1e-1))
        except AssertionError as e:
            carb.log_error(f"{points} is not close to expected {expected}")
            raise e

    async def _click_and_drag_test(self, start: Vec2, end: Vec2, expected):
        points_attr = self._basis_curves.GetPointsAttr()

        await ui_test.emulate_mouse_move_and_click(start, human_delay_speed=30)
        await ui_test.emulate_mouse_drag_and_drop(start, end, human_delay_speed=5)
        points = points_attr.Get()
        self._compare_points(points, expected)

        omni.kit.undo.undo()
        await ui_test.human_delay(5)

    # 2025-12-12: Failing on Kit 110 - temporarily disable until Jihui returns!
    # async def test_periodic_translate(self):
    #     self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_MOVE)
    #     await ui_test.human_delay()

    #     half_sqrt_2 = math.sqrt(2) * 0.5

    #     # 1) test translate anchor, anchor and both tangents move
    #     expected = (
    #         [
    #             (0, 0, 0),
    #             (-50, 0, 0),
    #         ]
    #         + self.SHOULD_NOT_CHANGE
    #         + [
    #             (50, 0, 0),
    #         ]
    #     )
    #     await self._click_and_drag_test(Vec2(200, 100), Vec2(200, 200), expected)

    #     # 2) test translate tangent, both tangents move, but in opposite direction
    #     expected = (
    #         [
    #             (0, 0, 50),
    #             (-50, 0, 100),
    #         ]
    #         + self.SHOULD_NOT_CHANGE
    #         + [
    #             (50, 0, 0),
    #         ]
    #     )
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 3) break tangent and move, only one tangent moves
    #     self._curve_edits.break_tangents(self._basis_curves, [0])
    #     expected = (
    #         [
    #             (0, 0, 50),
    #             (-50, 0, 50),
    #         ]
    #         + self.SHOULD_NOT_CHANGE
    #         + [
    #             (50, 0, 0),
    #         ]
    #     )
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 4) restore smooth and even tangents to 2)
    #     self._curve_edits.smooth_tangents(self._basis_curves, [0])
    #     self._curve_edits.even_tangents(self._basis_curves, [0])
    #     expected = (
    #         [
    #             (0, 0, 50),
    #             (-50, 0, 100),
    #         ]
    #         + self.SHOULD_NOT_CHANGE
    #         + [
    #             (50, 0, 0),
    #         ]
    #     )
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    #     # 5) uneven tangent
    #     self._curve_edits.uneven_tangents(self._basis_curves, [0])
    #     expected = (
    #         [
    #             (0, 0, 50),
    #             (-50 * half_sqrt_2, 0, 50 + 50 * half_sqrt_2),
    #         ]
    #         + self.SHOULD_NOT_CHANGE
    #         + [
    #             (50, 0, 0),
    #         ]
    #     )
    #     await self._click_and_drag_test(Vec2(100, 100), Vec2(100, 200), expected)

    async def test_periodic_rotate(self):
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_ROTATE)
        await ui_test.human_delay()

        expected = (
            [
                (0, 0, 50),
                (50, 0, 50),
            ]
            + self.SHOULD_NOT_CHANGE
            + [
                (-50, 0, 50),
            ]
        )

        ARC_RADIUS = 80
        await ui_test.emulate_mouse_move_and_click(Vec2(200, 100), human_delay_speed=30)
        await self._click_and_drag_test(Vec2(200 - ARC_RADIUS, 100), Vec2(200 + ARC_RADIUS, 100), expected)

    async def test_periodic_scale(self):
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SCALE)
        await ui_test.human_delay()

        expected = (
            [
                (0, 0, 50),
                (50, 0, 50),
            ]
            + self.SHOULD_NOT_CHANGE
            + [
                (-50, 0, 50),
            ]
        )
        await self._click_and_drag_test(Vec2(200, 100), Vec2(200, 200), expected)

    async def test_periodic_cv_edits(self):
        half_sqrt_2 = math.sqrt(2) * 0.5
        points_attr = self._basis_curves.GetPointsAttr()

        # make a corner
        self._curve_edits.corner(self._basis_curves, [0])
        expected = (
            [
                (0, 0, 50),
                (0, 0, 50),
            ]
            + self.SHOULD_NOT_CHANGE
            + [
                (0, 0, 50),
            ]
        )
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

        # make a bezier corner
        self._curve_edits.bezier_corner(self._basis_curves, [0])
        expected = (
            [
                (0, 0, 50),
                (-25, 0, 25),
            ]
            + self.SHOULD_NOT_CHANGE
            + [
                (25, 0, 25),
            ]
        )
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

        # make bezier
        self._curve_edits.bezier(self._basis_curves, [0])
        expected = (
            [
                (0, 0, 50),
                (-50 * half_sqrt_2, 0, 50),
            ]
            + self.SHOULD_NOT_CHANGE
            + [
                (50 * half_sqrt_2, 0, 50),
            ]
        )
        self._compare_points(points_attr.Get(), expected)

        await ui_test.human_delay()

    async def test_periodic_cv_split_and_add_last_segment(self):
        CURVE_DRAW_POINTS_SETTING = "persistent/exts/omni.curve.manipulator/curveDrawPoints"
        prev_draw = self._settings.get(CURVE_DRAW_POINTS_SETTING)
        self._settings.set(CURVE_DRAW_POINTS_SETTING, True)

        points_attr = self._basis_curves.GetPointsAttr()

        # click on the last curve segment, split it and adds a new CV + tangents
        await ui_test.emulate_mouse_move(Vec2(127, 127))
        async with KeyDownScope(self._key_edit_curve, self._key_edit_curve):
            await ui_test.emulate_mouse_click()
        expected = (
            [(0, 0, 50), (-50, 0, 50)]
            + self.SHOULD_NOT_CHANGE[:-1]
            + [
                (50, 0, -16.57471),
                (50, 0, 16.850578),
                (35.06224, 0, 35.338104),
                (27.655, 0, 44.505577),
                (16.57471, 0, 50),
            ]
        )
        self._compare_points(points_attr.Get(), expected)

        # click and drag on empty space, insert a new CV + tangents
        async with KeyDownScope(self._key_edit_curve, self._key_edit_curve):
            await ui_test.emulate_mouse_drag_and_drop(Vec2(50, 50), Vec2(50, 80))
        expected = (
            expected[:11]
            + [
                (75, 0, 90),
                (75, 0, 75),
                (75, 0, 60),
            ]
            + [expected[-1]]
        )
        self._compare_points(points_attr.Get(), expected)

        self._settings.set(CURVE_DRAW_POINTS_SETTING, prev_draw)
