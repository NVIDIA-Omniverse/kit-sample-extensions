# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import gc
import importlib
import weakref
from contextlib import ExitStack
from math import hypot, isclose, isfinite, isinf
from unittest.mock import Mock, patch

import omni.kit.app
import omni.ui
from carb.settings import get_settings
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from pxr import Gf

from ..common import DisplayAxisSpace, LabelSize, MeasureMode, Precision, UnitType
from ..manager import MeasurementManager
from ..system import MeasurePayload
from .test_util import PRIM_PATHS, TestMeasureBase, create_test_object, prim_path_world_pos

LOD_ENABLED = "/exts/omni.kit.tool.measure/label_lod_enabled"
LOD_ENTER = "/exts/omni.kit.tool.measure/label_lod_enter_px"
LOD_EXIT = "/exts/omni.kit.tool.measure/label_lod_exit_px"

# Perpendicular to the cube A -> cube B segment, so every measured point sits at the same view depth.
VIEW_DIR = Gf.Vec3d(1.0, 0.5, 1.0).GetNormalized()
REFERENCE_DISTANCE = 1000.0


def _label_lod_module():
    return importlib.import_module("omni.kit.tool.measure.viewport._label_lod")


def _mode_name(item):
    mode = getattr(item, "_label_mode", None)
    return getattr(mode, "name", None)


class TestMeasureLabelLod(TestMeasureBase):
    async def setUp(self):
        await super().setUp()
        self._settings = get_settings()
        self._saved_settings = {path: self._settings.get(path) for path in (LOD_ENABLED, LOD_ENTER, LOD_EXIT)}
        self._viewport_api = omni.ui.Workspace.get_window("Viewport").viewport_api
        # Most tests exercise the opt-in feature; preserve the packaged defaults separately.
        self._settings.set_bool(LOD_ENABLED, True)
        self._settings.set_float(LOD_ENTER, 60.0)
        self._settings.set_float(LOD_EXIT, 90.0)
        await self._wait_for_viewport()

    async def tearDown(self):
        for path, value in self._saved_settings.items():
            if value is not None:
                self._settings.set(path, value)
            else:
                self._settings.destroy_item(path)
        await super().tearDown()

    # Helpers
    async def _wait_for_viewport(self, predicate=None, expected_transform=None):
        """Wait for a delivered frame with the requested input state, never for a label assertion."""
        ready = asyncio.get_running_loop().create_future()
        armed = False

        def on_frame(viewport):
            # Subscribing invokes the callback immediately for the previous frame.
            if not armed or ready.done():
                return
            try:
                if min(self._display_size()) <= 0:
                    return
                if expected_transform is not None:
                    actual = viewport.transform
                    if not all(
                        isclose(actual[row][col], expected_transform[row][col], rel_tol=1e-5, abs_tol=1e-4)
                        for row in range(4)
                        for col in range(4)
                    ):
                        return
                if predicate is not None and not predicate():
                    return
                ready.set_result(None)
            except Exception as error:
                ready.set_exception(error)

        subscription = self._viewport_api.subscribe_to_frame_change(on_frame)
        armed = True
        try:
            await asyncio.wait_for(ready, timeout=30)
        except asyncio.TimeoutError:
            self.fail(
                "Viewport did not deliver the requested state within 30 seconds: "
                f"transform={self._viewport_api.transform}, expected={expected_transform}, "
                f"resolution={self._viewport_api.resolution}, display_size={self._display_size()}"
            )
        finally:
            subscription.destroy()
        # Flush manipulator invalidations queued by the synchronized frame's callbacks.
        await omni.kit.app.get_app().next_update_async()

    async def _wait_for_resolution(self, resolution):
        await self._wait_for_viewport(
            lambda: all(
                abs(actual - expected) <= 2 for actual, expected in zip(self._viewport_api.resolution, resolution)
            )
        )

    async def _wait_for_display_size(self, size):
        await self._wait_for_viewport(
            lambda: all(abs(actual - expected) <= 1 for actual, expected in zip(self._display_size(), size))
        )

    async def _wait_for_measurement_name(self, uuid, name):
        def has_name():
            item = self._extension.viewport.read(uuid)
            measure_prim = MeasurementManager().read(uuid)
            return item is not None and measure_prim is not None and item.payload.name == measure_prim.name == name

        await self._wait_for_viewport(has_name)

    @staticmethod
    def _rebuild_count(draw_spy):
        return sum(
            bool(call.kwargs.get("label_dirty", call.args[0] if call.args else True))
            for call in draw_spy.call_args_list
        )

    async def _create_measurement(
        self,
        name: str = "Wall-to-Floor",
        axis_display: DisplayAxisSpace = DisplayAxisSpace.NONE,
        mode: MeasureMode = MeasureMode.POINT_TO_POINT,
        prim_paths=None,
        offset=Gf.Vec3d(0, 0, 0),
    ) -> int:
        prim_paths = list(prim_paths or PRIM_PATHS)
        points = [Gf.Vec3d(*prim_path_world_pos(path)) + offset for path in prim_paths]

        payload = MeasurePayload()
        payload.name = name
        payload.prim_paths = prim_paths
        payload.points = MeasurePayload.world_to_local_points(points, prim_paths)
        payload.tool_mode = mode
        payload.axis_display = axis_display
        payload.unit_type = UnitType.CENTIMETERS
        payload.precision = Precision.HUNDRETH
        payload.label_size = LabelSize.MEDIUM
        MeasurementManager().create(payload)

        def creation_finished():
            item = self._extension.viewport.read(payload.uuid)
            measure_prim = MeasurementManager().read(payload.uuid)
            # add_measure_prim runs asynchronously and names the measurement after its prim.
            return (
                item is not None
                and measure_prim is not None
                and bool(item.payload.computed_points)
                and measure_prim.name == measure_prim.path.name
            )

        await self._wait_for_viewport(creation_finished)
        # Store the requested name only after asynchronous creation has assigned its default.
        MeasurementManager().read(payload.uuid).name = name
        await self._wait_for_measurement_name(payload.uuid, name)
        return payload.uuid

    def _item(self, uuid: int):
        item = self._extension.viewport.read(uuid)
        self.assertIsNotNone(item, f"No viewport measurement item for uuid {uuid}")
        return item

    def _span_px(self, points) -> float:
        """Reference projection in the UI pixels occupied by the measurement overlay."""
        world_to_ndc = self._viewport_api.world_to_ndc
        width, height = self._display_size()
        xs, ys = [], []
        for point in points:
            clip = Gf.Vec4d(point[0], point[1], point[2], 1.0) * world_to_ndc
            xs.append(clip[0] / clip[3] * 0.5 * width)
            ys.append(clip[1] / clip[3] * 0.5 * height)
        return hypot(max(xs) - min(xs), max(ys) - min(ys))

    def _display_size(self):
        scene_view = self._extension.viewport._scene_view
        return scene_view.computed_width, scene_view.computed_height

    def _assert_value_label_mode(self, item, expected):
        self.assertEqual(_mode_name(item), expected)
        if expected == "NAME":
            self.assertIsNotNone(item._name_label)
            self.assertTrue(item._name_label.visible)
            self.assertEqual(item._name_label.text, item.payload.name)
            self.assertIsNone(item._value_label)
        else:
            self.assertIsNotNone(item._value_label)
            self.assertTrue(item._value_label.visible)
            self.assertIsNone(item._name_label)

    async def _place_camera(self, target: Gf.Vec3d, distance: float) -> None:
        camera_state = ViewportCameraState(viewport=self._viewport_api)
        camera_state.set_position_world(target + VIEW_DIR * distance, False)
        camera_state.set_target_world(target, True)
        expected_transform = camera_state.usd_camera.ComputeLocalToWorldTransform(self._viewport_api.time)
        await self._wait_for_viewport(expected_transform=expected_transform)

    def _midpoint(self, item) -> Gf.Vec3d:
        points = [Gf.Vec3d(*p) for p in item.payload.computed_points]
        return sum(points, Gf.Vec3d(0, 0, 0)) / len(points)

    async def _calibrate(self, item) -> float:
        """Return span * distance for this measurement, so a camera distance can be derived from a target span."""
        await self._place_camera(self._midpoint(item), REFERENCE_DISTANCE)
        return self._span_px(item.payload.computed_points) * REFERENCE_DISTANCE

    async def _set_span(self, item, k: float, span: float) -> float:
        await self._place_camera(self._midpoint(item), k / span)
        return self._span_px(item.payload.computed_points)

    # AC1
    async def test_lod_hysteresis_decision(self):
        lod = _label_lod_module()
        DETAIL, NAME = lod.LabelMode.DETAIL, lod.LabelMode.NAME
        sequence = [(200, DETAIL), (59, DETAIL), (75, NAME), (91, NAME), (75, DETAIL)]
        expected = [DETAIL, NAME, NAME, DETAIL, DETAIL]
        results = [lod.decide_label_mode(span, previous, 60, 90) for span, previous in sequence]
        self.assertEqual(results, expected)

        # Misconfigured thresholds (enter >= exit) are clamped instead of crashing or flickering.
        self.assertEqual(lod.decide_label_mode(50, DETAIL, 90, 60), NAME)
        self.assertEqual(lod.decide_label_mode(89, NAME, 90, 60), NAME)
        self.assertEqual(lod.decide_label_mode(200, NAME, 90, 60), DETAIL)

    # AC2
    async def test_screen_span_scales_with_camera_distance(self):
        lod = _label_lod_module()
        third = "/test_cubeC"
        create_test_object(third, position=(125 + 30, -120, 125 + 30))
        await self._wait_for_viewport()

        linear_uuid = await self._create_measurement(name="linear")
        multi_uuid = await self._create_measurement(
            name="multi", mode=MeasureMode.MULTI_POINT, prim_paths=[PRIM_PATHS[0], third, PRIM_PATHS[1]]
        )
        for uuid, expected_count in ((linear_uuid, 2), (multi_uuid, 3)):
            item = self._item(uuid)
            points = [Gf.Vec3d(*p) for p in item.payload.computed_points]
            self.assertEqual(len(points), expected_count)
            target = self._midpoint(item)

            await self._place_camera(target, REFERENCE_DISTANCE)
            near_span = lod.compute_screen_span(points, self._viewport_api, self._display_size())
            self.assertAlmostEqual(near_span, self._span_px(points), delta=near_span * 0.01)
            if expected_count == 2:
                ndc = [self._viewport_api.world_to_ndc.Transform(p) for p in points]
                width, height = self._display_size()
                segment = hypot((ndc[0][0] - ndc[1][0]) * 0.5 * width, (ndc[0][1] - ndc[1][1]) * 0.5 * height)
                self.assertAlmostEqual(near_span, segment, delta=segment * 0.01)

            await self._place_camera(target, REFERENCE_DISTANCE * 10)
            far_span = lod.compute_screen_span(points, self._viewport_api, self._display_size())
            self.assertGreater(far_span, 0.0)
            self.assertAlmostEqual(near_span / far_span, 10.0, delta=0.5)

    async def test_render_scale_does_not_change_display_label_thresholds(self):
        """Lower/higher texture quality must not change labels at the same on-screen size."""
        original_scale = self._viewport_api.resolution_scale
        try:
            self._viewport_api.resolution_scale = 1.0
            await self._wait_for_resolution(self._viewport_api.full_resolution)
            item = self._item(await self._create_measurement(name="Render scale"))
            k = await self._calibrate(item)
            display_size = self._display_size()
            full_resolution = self._viewport_api.full_resolution

            for scale in (1.0, 0.25, 2.0):
                with self.subTest(render_scale=scale):
                    self._viewport_api.resolution_scale = scale
                    await self._wait_for_resolution(tuple(full * scale for full in full_resolution))
                    for actual, full in zip(self._viewport_api.resolution, full_resolution):
                        self.assertAlmostEqual(actual, full * scale, delta=2)
                    for actual, expected in zip(self._display_size(), display_size):
                        self.assertAlmostEqual(actual, expected, delta=1)

                    # Texture spans shrink/grow with render scale, while the displayed
                    # spans and their label modes must remain unchanged.
                    for span, expected_mode in ((120, "DETAIL"), (40, "NAME")):
                        self.assertAlmostEqual(await self._set_span(item, k, span), span, delta=1)
                        self._assert_value_label_mode(item, expected_mode)
        finally:
            self._viewport_api.resolution_scale = original_scale
            await self._wait_for_resolution(tuple(full * original_scale for full in self._viewport_api.full_resolution))

    async def test_fixed_render_resolution_does_not_change_display_label_thresholds(self):
        """Changing fixed render resolution at constant UI size preserves zoom thresholds."""
        original_scale = self._viewport_api.resolution_scale
        original_resolution = self._viewport_api.full_resolution
        original_fill_frame = self._viewport_api.fill_frame
        try:
            self._viewport_api.fill_frame = False
            self._viewport_api.resolution_scale = 1.0
            self._viewport_api.resolution = (640, 480)
            await self._wait_for_resolution((640, 480))
            item = self._item(await self._create_measurement(name="Fixed resolution"))
            k = await self._calibrate(item)
            display_size = self._display_size()

            for resolution in ((640, 480), (160, 120), (1280, 960)):
                with self.subTest(render_resolution=resolution):
                    self._viewport_api.resolution = resolution
                    await self._wait_for_resolution(resolution)
                    self.assertEqual(tuple(self._viewport_api.resolution), resolution)
                    for actual, expected in zip(self._display_size(), display_size):
                        self.assertAlmostEqual(actual, expected, delta=1)
                    for span, expected_mode in ((120, "DETAIL"), (40, "NAME")):
                        self.assertAlmostEqual(await self._set_span(item, k, span), span, delta=1)
                        self._assert_value_label_mode(item, expected_mode)
        finally:
            self._viewport_api.resolution = original_resolution
            self._viewport_api.resolution_scale = original_scale
            self._viewport_api.fill_frame = original_fill_frame
            await self._wait_for_viewport()

    async def test_scene_view_resize_updates_labels_without_camera_change(self):
        """A real overlay layout change must refresh LOD even when the camera is unchanged."""
        item = self._item(await self._create_measurement(name="Resize overlay"))
        k = await self._calibrate(item)
        self.assertAlmostEqual(await self._set_span(item, k, 160), 160, delta=1)
        self._assert_value_label_mode(item, "DETAIL")
        scene_view = self._extension.viewport._scene_view
        # Widget Length getters reference mutable widget state. Multiplication
        # creates independent Length values while preserving their original units.
        original_width, original_height = scene_view.width * 1.0, scene_view.height * 1.0
        display_width, display_height = self._display_size()
        camera_matrix = Gf.Matrix4d(self._viewport_api.world_to_ndc)
        render_resolution = tuple(self._viewport_api.resolution)

        try:
            # Resize the actual visible SceneView, retaining its aspect ratio and the
            # viewport's camera/render resolution. No controller refresh is called.
            scene_view.width = omni.ui.Pixel(display_width * 0.25)
            scene_view.height = omni.ui.Pixel(display_height * 0.25)
            await self._wait_for_display_size((display_width * 0.25, display_height * 0.25))
            self.assertAlmostEqual(scene_view.computed_width, display_width * 0.25, delta=1)
            self.assertAlmostEqual(scene_view.computed_height, display_height * 0.25, delta=1)
            self.assertEqual(self._viewport_api.world_to_ndc, camera_matrix)
            self.assertEqual(tuple(self._viewport_api.resolution), render_resolution)
            self.assertAlmostEqual(self._span_px(item.payload.computed_points), 40, delta=1)
            self._assert_value_label_mode(item, "NAME")

            scene_view.width, scene_view.height = original_width, original_height
            await self._wait_for_display_size((display_width, display_height))
            self.assertAlmostEqual(scene_view.computed_width, display_width, delta=1)
            self.assertAlmostEqual(scene_view.computed_height, display_height, delta=1)
            self.assertEqual(self._viewport_api.world_to_ndc, camera_matrix)
            self.assertEqual(tuple(self._viewport_api.resolution), render_resolution)
            self.assertAlmostEqual(self._span_px(item.payload.computed_points), 160, delta=1)
            self._assert_value_label_mode(item, "DETAIL")
        finally:
            scene_view.width, scene_view.height = original_width, original_height
            await self._wait_for_display_size((display_width, display_height))

    # AC3
    async def test_axis_stack_switches_to_name_when_zoomed_out(self):
        uuid = await self._create_measurement(name="Wall-to-Floor", axis_display=DisplayAxisSpace.WORLD)
        item = self._item(uuid)
        k = await self._calibrate(item)

        self.assertGreater(await self._set_span(item, k, 300), 90)
        self.assertEqual(_mode_name(item), "DETAIL")
        self.assertTrue(item._stack_label.visible)

        self.assertLess(await self._set_span(item, k, 30), 60)
        self.assertEqual(_mode_name(item), "NAME")
        self.assertTrue(item._stack_label is None or not item._stack_label.visible)
        self.assertEqual(item._name_label.text, "Wall-to-Floor")
        self.assertEqual(item._name_label.text, item.payload.name)
        self.assertEqual(MeasurementManager().read(uuid).name, "Wall-to-Floor")

    # AC4
    async def test_axis_stack_restores_detail_when_zoomed_in(self):
        uuid = await self._create_measurement(name="Wall-to-Floor", axis_display=DisplayAxisSpace.WORLD)
        item = self._item(uuid)
        k = await self._calibrate(item)

        await self._set_span(item, k, 300)
        stack = item._stack_label
        before = [stack._m_label.text, stack._x_label.text, stack._y_label.text, stack._z_label.text]
        self.assertTrue(all(before))

        await self._set_span(item, k, 30)
        self.assertEqual(_mode_name(item), "NAME")

        self.assertGreater(await self._set_span(item, k, 300), 90)
        self.assertEqual(_mode_name(item), "DETAIL")
        stack = item._stack_label
        self.assertIsNotNone(stack)
        self.assertTrue(stack.visible)
        after = [stack._m_label.text, stack._x_label.text, stack._y_label.text, stack._z_label.text]
        self.assertEqual(after, before)
        self.assertIsNone(item._name_label)

    # AC5
    async def test_value_label_switches_to_name_and_back(self):
        uuid = await self._create_measurement(name="Pipe-Run", axis_display=DisplayAxisSpace.NONE)
        item = self._item(uuid)
        k = await self._calibrate(item)

        await self._set_span(item, k, 300)
        value_text = item._value_label.text
        self.assertTrue(value_text.endswith(" cm"), value_text)

        await self._set_span(item, k, 30)
        self.assertEqual(_mode_name(item), "NAME")
        self.assertEqual(item._name_label.text, "Pipe-Run")
        self.assertIsNone(item._value_label)

        await self._set_span(item, k, 300)
        self.assertEqual(_mode_name(item), "DETAIL")
        self.assertEqual(item._value_label.text, value_text)
        self.assertIsNone(item._name_label)

    # AC6
    async def test_no_flicker_between_thresholds(self):
        uuid = await self._create_measurement(name="Between")
        item = self._item(uuid)
        k = await self._calibrate(item)

        await self._set_span(item, k, 300)
        span = await self._set_span(item, k, 75)
        self.assertTrue(60 < span < 90, span)
        self.assertEqual(_mode_name(item), "DETAIL")
        with patch.object(item, "draw", wraps=item.draw) as draw:
            for i in range(20):
                span = await self._set_span(item, k, 65 if i % 2 == 0 else 85)
                self.assertTrue(60 < span < 90, span)
                self.assertEqual(_mode_name(item), "DETAIL")
            self.assertEqual(self._rebuild_count(draw), 0)

    # AC7
    async def test_only_crossing_measurements_rebuild(self):
        uuids = [await self._create_measurement(name=f"m{i:02d}", offset=Gf.Vec3d(0, i * 2.0, 0)) for i in range(20)]
        items = [self._item(uuid) for uuid in uuids]
        k = await self._calibrate(items[0])

        await self._set_span(items[0], k, 400)
        self.assertTrue(all(_mode_name(item) == "DETAIL" for item in items))
        with ExitStack() as stack:
            draws = [stack.enter_context(patch.object(item, "draw", wraps=item.draw)) for item in items]
            for i in range(30):
                await self._set_span(items[0], k, 300 + (i % 5) * 40)
            self.assertEqual([self._rebuild_count(draw) for draw in draws], [0] * len(items))

            await self._set_span(items[0], k, 20)
            self.assertTrue(all(_mode_name(item) == "NAME" for item in items))
            self.assertEqual([self._rebuild_count(draw) for draw in draws], [1] * len(items))

    # AC8
    async def test_disable_setting_restores_legacy_labels(self):
        uuid = await self._create_measurement(name="Toggle-Me")
        item = self._item(uuid)
        k = await self._calibrate(item)
        await self._set_span(item, k, 30)
        self.assertEqual(_mode_name(item), "NAME")

        self._settings.set_bool(LOD_ENABLED, False)
        await self._wait_for_viewport()
        self.assertEqual(_mode_name(item), "DETAIL")
        self.assertIsNotNone(item._value_label)
        self.assertIsNone(item._name_label)

        await self._set_span(item, k, 10)
        self.assertEqual(_mode_name(item), "DETAIL")

        self._settings.set_bool(LOD_ENABLED, True)
        await self._wait_for_viewport()
        self.assertEqual(_mode_name(item), "NAME")
        self.assertEqual(item._name_label.text, "Toggle-Me")

    # AC9
    async def test_name_label_follows_rename(self):
        uuid = await self._create_measurement(name="Before_Name")
        item = self._item(uuid)
        k = await self._calibrate(item)
        await self._set_span(item, k, 30)
        self.assertEqual(_mode_name(item), "NAME")
        self.assertEqual(item._name_label.text, "Before_Name")

        MeasurementManager().rename(uuid, "After_Name")
        await self._wait_for_measurement_name(uuid, "After_Name")

        item = self._item(uuid)
        self.assertEqual(MeasurementManager().read(uuid).name, "After_Name")
        self.assertEqual(_mode_name(item), "NAME")
        self.assertEqual(item._name_label.text, "After_Name")

    # AC10
    async def test_empty_name_keeps_detail_label(self):
        uuid = await self._create_measurement(name="Temporary")
        MeasurementManager().read(uuid).name = ""
        await self._wait_for_measurement_name(uuid, "")
        item = self._item(uuid)
        self.assertEqual(item.payload.name, "")
        k = await self._calibrate(item)

        self.assertLess(await self._set_span(item, k, 30), 60)
        self.assertEqual(_mode_name(item), "DETAIL")
        self.assertIsNone(item._name_label)
        self.assertTrue(item._value_label.text.endswith(" cm"))

    async def test_default_setting_keeps_detail_until_enabled(self):
        """The package preserves legacy rendering until a consumer opts in."""
        self.assertIs(self._saved_settings[LOD_ENABLED], False)
        self._settings.set_bool(LOD_ENABLED, False)
        item = self._item(await self._create_measurement(name="Opt in"))
        k = await self._calibrate(item)
        self.assertLess(await self._set_span(item, k, 30), 60)
        self._assert_value_label_mode(item, "DETAIL")

        self._settings.set_bool(LOD_ENABLED, True)
        await self._wait_for_viewport()
        self._assert_value_label_mode(item, "NAME")

        # An absent setting must use the same opt-in fallback as extension.toml.
        self._settings.destroy_item(LOD_ENABLED)
        await self._wait_for_viewport()
        self.assertIsNone(self._settings.get(LOD_ENABLED))
        self._assert_value_label_mode(item, "DETAIL")

    async def test_cached_settings_update_without_per_frame_reads(self):
        """Orbit uses cached values; settings events apply threshold edits immediately."""
        item = self._item(await self._create_measurement(name="Cached settings"))
        controller = item._label_lod
        k = await self._calibrate(item)
        await self._set_span(item, k, 300)

        with patch.object(controller, "_read_settings", wraps=controller._read_settings) as read_settings:
            for span in (75, 80, 75):
                await self._set_span(item, k, span)
                self._assert_value_label_mode(item, "DETAIL")
                controller.refresh()
                controller.resolve(item)
            read_settings.assert_not_called()

            # Neither edit moves the camera; the settings event must trigger the redraw.
            self._settings.set_float(LOD_ENTER, 80.0)
            await self._wait_for_viewport()
            self._assert_value_label_mode(item, "NAME")
            self.assertGreater(read_settings.call_count, 0)

            # enter >= exit is clamped to 80 / 81, so 75 px stays in NAME.
            self._settings.set_float(LOD_EXIT, 70.0)
            await self._wait_for_viewport()
            self._assert_value_label_mode(item, "NAME")

            self._settings.set_float(LOD_ENTER, 40.0)
            await self._wait_for_viewport()
            self._assert_value_label_mode(item, "DETAIL")

            self._settings.set_bool(LOD_ENABLED, False)
            await self._wait_for_viewport()
            read_settings.reset_mock()
            with patch.object(controller, "resolve", wraps=controller.resolve) as resolve:
                await self._set_span(item, k, 10)
                self._assert_value_label_mode(item, "DETAIL")
                resolve.assert_not_called()
            read_settings.assert_not_called()

            self._settings.set_bool(LOD_ENABLED, True)
            await self._wait_for_viewport()
            self._assert_value_label_mode(item, "NAME")
            self.assertGreater(read_settings.call_count, 0)

    async def test_refresh_ignores_detached_and_foreign_controller_items(self):
        """Only the controller used by an item's draw path may advance its LOD state."""
        lod = _label_lod_module()
        item = self._item(await self._create_measurement(name="Ownership"))
        controller = item._label_lod
        k = await self._calibrate(item)
        await self._set_span(item, k, 30)
        self._assert_value_label_mode(item, "NAME")
        foreign_controller = lod.LabelLodController(None, None)
        try:
            for owner in (None, foreign_controller):
                with self.subTest(detached=owner is None):
                    item._label_lod = owner
                    item._lod_state = lod.LabelMode.DETAIL
                    item.draw()
                    self._assert_value_label_mode(item, "DETAIL")
                    with (
                        patch.object(controller, "resolve", wraps=controller.resolve) as resolve,
                        patch.object(item, "draw", wraps=item.draw) as draw,
                    ):
                        for _ in range(3):
                            controller.refresh()
                        await self._wait_for_viewport()
                        resolve.assert_not_called()
                        self.assertEqual(self._rebuild_count(draw), 0)
                        self.assertEqual(item._lod_state, lod.LabelMode.DETAIL)
        finally:
            item._label_lod = controller
            foreign_controller.destroy()
            controller.refresh()
        await self._wait_for_viewport()
        self._assert_value_label_mode(item, "NAME")

    async def test_projection_retains_detail_across_camera_plane(self):
        """Real perspective projection keeps conservative detail for unclipped camera-plane crossings."""
        lod = _label_lod_module()
        await self._place_camera(Gf.Vec3d(125, 0, 125), REFERENCE_DISTANCE)
        camera_to_world = self._viewport_api.transform
        front = [camera_to_world.Transform(Gf.Vec3d(x, 0, -100)) for x in (-1, 1)]
        behind = camera_to_world.Transform(Gf.Vec3d(0, 0, 100))
        on_plane = camera_to_world.Transform(Gf.Vec3d(0, 0, 0))
        near_plane = camera_to_world.Transform(Gf.Vec3d(0, 0, -1e-10))
        self.assertGreater((Gf.Vec4d(*front[0], 1) * self._viewport_api.world_to_ndc)[3], 0)
        self.assertLess((Gf.Vec4d(*behind, 1) * self._viewport_api.world_to_ndc)[3], 0)
        self.assertTrue(isfinite(lod.compute_screen_span(front, self._viewport_api, self._display_size())))
        for points in ([front[0], behind], [behind], [front[0], on_plane], [front[0], near_plane]):
            with self.subTest(points=points):
                span = lod.compute_screen_span(points, self._viewport_api, self._display_size())
                self.assertTrue(isinf(span))
                self.assertEqual(lod.decide_label_mode(span, lod.LabelMode.NAME, 60, 90), lod.LabelMode.DETAIL)

    async def _exercise_controller_destroy(self, destroy_widget_first, detach_error=None):
        from omni.ui import scene as sc

        from ..viewport._model import ViewportMeasurementModel

        # Every subcase must move the camera, even if a preceding subcase failed early.
        await self._place_camera(Gf.Vec3d(125, 0, 125), REFERENCE_DISTANCE * 3)
        window = omni.ui.Window("Label LOD teardown test", width=120, height=80)
        with window.frame:
            scene_view = sc.SceneView()
        controller = _label_lod_module().LabelLodController(self._viewport_api, ViewportMeasurementModel(), scene_view)
        window_destroyed = False
        try:
            with (
                patch.object(controller, "_read_settings", wraps=controller._read_settings) as read_settings,
                patch.object(controller, "refresh", wraps=controller.refresh) as refresh,
            ):
                # Establish that the actual settings and viewport subscriptions are active.
                self._settings.set_bool(LOD_ENABLED, True)
                self._settings.set_float(LOD_ENTER, self._settings.get(LOD_ENTER) + 1)
                await self._wait_for_viewport()
                read_settings.assert_called()
                refresh.reset_mock()
                await self._place_camera(Gf.Vec3d(125, 0, 125), REFERENCE_DISTANCE)
                refresh.assert_called()

                if destroy_widget_first:
                    scene_view.destroy()
                    window.destroy()
                    window_destroyed = True
                if detach_error is not None:
                    # Some Kit bindings allow clearing a destroyed widget. Inject only
                    # this failure boundary while keeping real settings/view subscriptions.
                    unavailable_view = Mock(wraps=scene_view)
                    unavailable_view.set_computed_content_size_changed_fn.side_effect = detach_error(
                        "SceneView callback is unavailable during teardown"
                    )
                    controller._scene_view = unavailable_view

                read_settings.reset_mock()
                refresh.reset_mock()
                if detach_error is ValueError:
                    # Unexpected errors still surface after releasing the subscriptions.
                    with self.assertRaises(ValueError):
                        controller.destroy()
                else:
                    controller.destroy()
                self.assertIsNone(controller._scene_view)
                self.assertEqual(controller._settings_subs, [])
                self.assertIsNone(controller._view_sub)
                self.assertIsNone(controller._viewport_api)
                self.assertIsNone(controller._model)
                controller.destroy()

                self._settings.set_bool(LOD_ENABLED, False)
                self._settings.set_float(LOD_ENTER, self._settings.get(LOD_ENTER) + 1)
                self._settings.set_float(LOD_EXIT, self._settings.get(LOD_EXIT) + 1)
                await self._place_camera(Gf.Vec3d(125, 0, 125), REFERENCE_DISTANCE * 2)
                read_settings.assert_not_called()
                refresh.assert_not_called()
        finally:
            # Keep a failing baseline from leaking its native subscriptions into later tests.
            controller._scene_view = None
            controller.destroy()
            scene_view.destroy()
            if not window_destroyed:
                window.destroy()
        return weakref.ref(controller)

    async def test_destroy_releases_live_and_destroyed_scene_views(self):
        for destroy_widget_first in (False, True):
            with self.subTest(destroy_widget_first=destroy_widget_first):
                reference = await self._exercise_controller_destroy(destroy_widget_first)
                gc.collect()
                self.assertIsNone(reference(), "Destroyed controller is retained by a subscription")

    async def test_destroy_releases_subscriptions_when_scene_view_disconnect_raises(self):
        for detach_error in (RuntimeError, ReferenceError, ValueError):
            with self.subTest(detach_error=detach_error.__name__):
                reference = await self._exercise_controller_destroy(True, detach_error)
                gc.collect()
                self.assertIsNone(reference(), "Failed widget detach retained the controller")

    async def test_name_elision_character_boundary(self):
        """Names up to 18 characters remain complete; longer display text fits the same budget."""
        uuid = await self._create_measurement(name="Boundary_123456789")
        item = self._item(uuid)
        k = await self._calibrate(item)
        await self._set_span(item, k, 30)
        self.assertEqual(item._name_label.text, "Boundary_123456789")

        MeasurementManager().rename(uuid, "Boundary_1234567890")
        await self._wait_for_measurement_name(uuid, "Boundary_1234567890")
        item = self._item(uuid)
        self.assertEqual(_mode_name(item), "NAME")
        self.assertEqual(item._name_label.text, "Boundary_123456...")
        self.assertEqual(item.payload.name, "Boundary_1234567890")
        self.assertEqual(MeasurementManager().read(uuid).name, "Boundary_1234567890")

    async def test_long_name_and_rename_preserve_payload_for_all_measurement_types(self):
        """Every label renderer uses bounded overview text without truncating stored names."""
        third, fourth = "/test_cubeC", "/test_cubeD"
        create_test_object(third, position=(155, -120, 155))
        create_test_object(fourth, position=(95, 120, 95))
        await self._wait_for_viewport()
        specs = [
            ("linear", MeasureMode.POINT_TO_POINT, PRIM_PATHS, DisplayAxisSpace.NONE),
            ("world_axes", MeasureMode.POINT_TO_POINT, PRIM_PATHS, DisplayAxisSpace.WORLD),
            ("multi", MeasureMode.MULTI_POINT, [PRIM_PATHS[0], third, PRIM_PATHS[1]], DisplayAxisSpace.NONE),
            ("angle", MeasureMode.ANGLE, [PRIM_PATHS[0], third, PRIM_PATHS[1]], DisplayAxisSpace.NONE),
            ("area", MeasureMode.AREA, [PRIM_PATHS[0], third, PRIM_PATHS[1], fourth], DisplayAxisSpace.NONE),
            ("diameter", MeasureMode.DIAMETER, [PRIM_PATHS[0], third, PRIM_PATHS[1]], DisplayAxisSpace.NONE),
        ]
        for kind, mode, paths, axes in specs:
            with self.subTest(measurement_type=kind):
                full_name, renamed = "A" * 100 + "_" + kind, "Renamed" + "B" * 80 + "_" + kind
                uuid = await self._create_measurement(name=full_name, mode=mode, prim_paths=paths, axis_display=axes)
                item = self._item(uuid)
                k = await self._calibrate(item)
                await self._set_span(item, k, 30)
                self.assertEqual(_mode_name(item), "NAME")
                self.assertEqual(item._name_label.text, "A" * 15 + "...")
                self.assertTrue(item._name_label.visible)
                self.assertEqual(item.payload.name, full_name)
                self.assertEqual(MeasurementManager().read(uuid).name, full_name)
                original_value = item.payload.primary_value

                MeasurementManager().rename(uuid, renamed)
                await self._wait_for_measurement_name(uuid, renamed)
                item = self._item(uuid)
                self.assertEqual(_mode_name(item), "NAME")
                self.assertEqual(item._name_label.text, "Renamed" + "B" * 8 + "...")
                self.assertEqual(item.payload.name, renamed)
                self.assertEqual(MeasurementManager().read(uuid).name, renamed)

                await self._set_span(item, k, 300)
                self.assertEqual(_mode_name(item), "DETAIL")
                self.assertIsNone(item._name_label)
                self.assertAlmostEqual(item.payload.primary_value, original_value)
                await self._set_span(item, k, 30)
                self.assertEqual(_mode_name(item), "NAME")
                self.assertEqual(item._name_label.text, "Renamed" + "B" * 8 + "...")
                self.assertEqual(item.payload.name, renamed)
