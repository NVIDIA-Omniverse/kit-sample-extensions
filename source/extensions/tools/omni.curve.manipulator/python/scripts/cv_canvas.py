# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import math
import weakref
from typing import List, Set, Tuple

import carb.input
import carb.profiler
import carb.settings
import omni.kit.commands
import omni.kit.undo
from omni.kit.manipulator.tool.snap import SnapProviderManager
from omni.kit.manipulator.tool.snap import settings_constants as snap_c
from omni.kit.manipulator.transform.gestures import TransformGesture
from omni.kit.manipulator.transform.settings_listener import SnapSettingsListener
from omni.ui import color as cl
from omni.ui import scene as sc
from pxr import Gf, Sdf, UsdGeom

from ..bindings import CurveManipulatorContext, get_interface
from .cv_selection import CvSelection, SelectMode
from .cv_viz import CvClickGesture

CURVE_DRAW_POINTS_SETTING = "persistent/exts/omni.curve.manipulator/curveDrawPoints"


def flatten(transform):
    """Convert array[4][4] to array[16]"""

    # flatten the matrix by hand
    # USING LIST COMPREHENSION IS VERY SLOW (e.g. return [item for sublist in transform for item in sublist]), which takes around 10ms.
    return [
        transform[0][0],
        transform[0][1],
        transform[0][2],
        transform[0][3],
        transform[1][0],
        transform[1][1],
        transform[1][2],
        transform[1][3],
        transform[2][0],
        transform[2][1],
        transform[2][2],
        transform[2][3],
        transform[3][0],
        transform[3][1],
        transform[3][2],
        transform[3][3],
    ]


class PreventOthers(sc.GestureManager):
    """
    Manager makes TransformGesture the priority gesture
    """

    def can_be_prevented(self, gesture):
        # Never prevent in the middle of drag
        return gesture.state != sc.GestureState.CHANGED

    def should_prevent(self, gesture, preventer):
        if isinstance(preventer, MarqueeGesture) and (
            preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED
        ):
            # Transform manipulator has higher priority
            if isinstance(gesture, TransformGesture):
                return False

            # CvClickGesture has higher priority
            if isinstance(gesture, CvClickGesture):
                return False

            if isinstance(gesture, RaycastGesture):
                return False

            try:
                # Camera manipulation has higher priority
                from omni.kit.manipulator.camera.gesturebase import CameraGestureBase

                if isinstance(gesture, CameraGestureBase):
                    return False
            except ImportError:
                ...

            # MarqueeGesture is the priority when it's against any other gesture
            return True
        return super().should_prevent(gesture, preventer)


class RaycastPreventOthers(sc.GestureManager):
    """
    Manager makes RaycastGesture the priority gesture
    """

    def can_be_prevented(self, gesture):
        # Never prevent in the middle of drag
        return gesture.state != sc.GestureState.CHANGED

    def should_prevent(self, gesture, preventer):
        if isinstance(preventer, RaycastGesture) and (
            preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED
        ):
            # Transform manipulator has higher priority
            if isinstance(gesture, TransformGesture):
                return False

            # don't prevent marquee
            if isinstance(gesture, MarqueeGesture):
                return False

            try:
                # Camera manipulation has higher priority
                from omni.kit.manipulator.camera.gesturebase import CameraGestureBase

                if isinstance(gesture, CameraGestureBase):
                    return False
            except ImportError:
                ...

            # RaycastGesture is the priority when it's against any other gesture
            return True
        return super().should_prevent(gesture, preventer)


class RaycastBase:
    def __init__(self, cv_canvas: CvCanvas, can_snap: bool):
        self._cv_canvas = cv_canvas
        self._curve_manip = get_interface()
        self._can_snap = can_snap

    def _begin_snap(self):
        if (
            self._cv_canvas._snap_settings_listener.snap_enabled
            and self._cv_canvas._snap_settings_listener.snap_provider
        ):
            # Don't snap to curve itself
            editing_curve_paths = self._curve_manip.get_editing_curve_paths(self._cv_canvas.curve_context)
            self._cv_canvas.snap_manager.on_began(excluded_paths=[Sdf.Path(p) for p in editing_curve_paths])

    def _end_snap(self):
        if (
            self._cv_canvas._snap_settings_listener.snap_enabled
            and self._cv_canvas._snap_settings_listener.snap_provider
        ):
            self._cv_canvas.snap_manager.on_ended()

    def _on_mouse(self, input: bool, end: bool):
        viewport_api = self._cv_canvas.viewport_api
        if viewport_api is not None:
            mouse = self.sender.gesture_payload.mouse
            ndc_near = Gf.Vec3f(mouse[0], mouse[1], -1)
            ndc_far = Gf.Vec3f(mouse[0], mouse[1], 1)

            origin = viewport_api.ndc_to_world.Transform(ndc_near)
            direction = (viewport_api.ndc_to_world.Transform(ndc_far) - origin).GetNormalized()

            view_proj = viewport_api.view * viewport_api.projection
            camera_path = viewport_api.camera_path.pathString

            rect = carb.Float4(0, 0, viewport_api.resolution[0], viewport_api.resolution[1])

            def apply_position(snap_world_pos=None, snap_world_orient=None, keep_spacing: bool = True):
                # ignore snap_world_orient and keep_spacing for now

                if snap_world_pos and (
                    math.isfinite(snap_world_pos[0])
                    and math.isfinite(snap_world_pos[1])
                    and math.isfinite(snap_world_pos[2])
                ):
                    snap_world_pos = carb.Double3(snap_world_pos[0], snap_world_pos[1], snap_world_pos[2])
                else:
                    snap_world_pos = None

                self._curve_manip.on_raycast(
                    self._cv_canvas.curve_context,
                    carb.Float3(origin[0], origin[1], origin[2]),  # carb.Float3(*origin) is slow
                    carb.Float3(direction[0], direction[1], direction[2]),
                    input,
                    end,
                    camera_path,
                    rect,
                    flatten(view_proj),
                    snap_world_pos,
                )

            if (
                self._cv_canvas._snap_settings_listener.snap_enabled
                and self._cv_canvas._snap_settings_listener.snap_provider
                and self._can_snap
            ):
                if self._cv_canvas.snap_manager.get_snap_pos(
                    Gf.Matrix4d(1),
                    (mouse[0], mouse[1], -1),
                    self.sender.scene_view,
                    lambda **kwargs: apply_position(
                        kwargs.get("position", None), kwargs.get("orient", None), kwargs.get("keep_spacing", True)
                    ),
                ):
                    return

            apply_position()


class RaycastGesture(sc.DragGesture, RaycastBase):
    def __init__(self, cv_canvas: CvCanvas, modifier_flags: int = 0, *args, **kwargs):
        sc.DragGesture.__init__(self, modifiers=modifier_flags, manager=RaycastPreventOthers(), *args, **kwargs)
        RaycastBase.__init__(self, cv_canvas, True)

        self._input = carb.input.acquire_input_interface()
        self._began = False

    def process(self):
        if (self.state == sc.GestureState.PREVENTED or self.state == sc.GestureState.CANCELED) and self._began:
            self.on_ended()

        super().process()

    def on_began(self):
        if self._began:
            return

        ctrl_down = self._input.get_keyboard_value(
            None, carb.input.KeyboardInput.LEFT_CONTROL
        ) + self._input.get_keyboard_value(None, carb.input.KeyboardInput.RIGHT_CONTROL)
        # exclude ctrl + shift + drag which is merge marquee selection
        if not ctrl_down:
            self._begin_snap()
            self._on_mouse(True, False)
            self._began = True

    def on_changed(self):
        if self._began:
            self._on_mouse(True, False)

    def on_ended(self):
        if self._began:
            self._on_mouse(False, True)
            self._began = False
            self._end_snap()


class RaycastHoverGesture(sc.HoverGesture, RaycastBase):
    def __init__(self, cv_canvas: CvCanvas, *args, **kwargs):
        sc.HoverGesture.__init__(self, *args, **kwargs)
        RaycastBase.__init__(self, cv_canvas, False)

        self._input = carb.input.acquire_input_interface()
        self._began = False

    def on_began(self):
        ctrl_down = self._input.get_keyboard_value(
            None, carb.input.KeyboardInput.LEFT_CONTROL
        ) + self._input.get_keyboard_value(None, carb.input.KeyboardInput.RIGHT_CONTROL)

        # exclude ctrl + shift + drag which is merge marquee selection
        if not ctrl_down:
            self._on_mouse(False)
            self._began = True

    def on_changed(self):
        if self._began:
            self._on_mouse(False)

    def on_ended(self):
        if self._began:
            self._on_mouse(True)
            self._began = False

    def _on_mouse(self, end: bool):
        # Do not proceed if LMB is down
        if self._input.get_mouse_button_flags(None, carb.input.MouseInput.LEFT_BUTTON) & carb.input.BUTTON_FLAG_DOWN:
            return

        super()._on_mouse(False, end)


class MarqueeGesture(sc.DragGesture):
    def __init__(self, cv_canvas: CvCanvas, *args, **kwargs):
        super().__init__(manager=PreventOthers(), *args, **kwargs)
        self._cv_canvas = cv_canvas
        self._input = carb.input.acquire_input_interface()
        self._start = None

    def on_began(self):
        shift_down = self._input.get_keyboard_value(
            None, carb.input.KeyboardInput.LEFT_SHIFT
        ) + self._input.get_keyboard_value(None, carb.input.KeyboardInput.RIGHT_SHIFT)
        ctrl_down = self._input.get_keyboard_value(
            None, carb.input.KeyboardInput.LEFT_CONTROL
        ) + self._input.get_keyboard_value(None, carb.input.KeyboardInput.RIGHT_CONTROL)
        alt_down = self._input.get_keyboard_value(
            None, carb.input.KeyboardInput.LEFT_ALT
        ) + self._input.get_keyboard_value(None, carb.input.KeyboardInput.RIGHT_ALT)

        # Do not marquee if SHIFT is down and CTRL is up (sampling mode)
        if shift_down > 0 and ctrl_down == 0:
            return

        # Do not marquee if moving camera (alt down)
        if alt_down > 0:
            return

        self._start = self.sender.gesture_payload.mouse
        self._cv_canvas._on_marquee_changed(self._start, self._start, False)

    def on_changed(self):
        if self._start is not None:
            self._cv_canvas._on_marquee_changed(self._start, self.sender.gesture_payload.mouse, False)

    def on_ended(self):
        if self._start is not None:
            self._cv_canvas._on_marquee_changed(self._start, self.sender.gesture_payload.mouse, True)
            self._start = None


class CvCanvas(sc.Manipulator):
    FLAG_TO_KEYS = {
        carb.input.KEYBOARD_MODIFIER_FLAG_ALT: set(
            [
                carb.input.KeyboardInput.LEFT_ALT,
                carb.input.KeyboardInput.RIGHT_ALT,
            ]
        ),
        carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL: set(
            [
                carb.input.KeyboardInput.LEFT_CONTROL,
                carb.input.KeyboardInput.RIGHT_CONTROL,
            ]
        ),
        carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT: set(
            [
                carb.input.KeyboardInput.LEFT_SHIFT,
                carb.input.KeyboardInput.RIGHT_SHIFT,
            ]
        ),
    }

    def __del__(self):
        self.destroy()

    def __init__(
        self,
        enabled: bool = True,
        curve_context: CurveManipulatorContext = None,
        viewport_api=None,
        selection: CvSelection = None,
        basis_curves_list: List[UsdGeom.BasisCurves] = [],
        edit_modifier_flag: int = 0,
        append_modifier_flag: int = 0,
    ):
        super().__init__()
        self._append_modifier_flag = append_modifier_flag if append_modifier_flag in CvCanvas.FLAG_TO_KEYS else 0
        self._enabled = enabled
        self._curve_context = curve_context
        self._edit_modifier_flag = edit_modifier_flag if edit_modifier_flag in CvCanvas.FLAG_TO_KEYS else 0
        self._viewport_api = viewport_api
        self._selection = selection
        self._basis_curves_list = basis_curves_list
        self._input = carb.input.acquire_input_interface()
        self._settings = carb.settings.get_settings()
        self._scene_marquee_rect_item = None
        self._marquee_root = None
        self._marquee_screen = None
        self._marquee_start = None
        self._marquee_end = None
        self._snap_manager = SnapProviderManager(viewport_api=viewport_api)
        self._snap_settings_listener = SnapSettingsListener(
            enabled_setting_path=None,
            move_x_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_y_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_z_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            rotate_setting_path=snap_c.SNAP_ROTATE_SETTING_PATH,
            scale_setting_path=snap_c.SNAP_SCALE_SETTING_PATH,
            provider_setting_path=snap_c.SNAP_PROVIDER_NAME_SETTING_PATH,
        )
        self._sub_setting = self._settings.subscribe_to_node_change_events(
            CURVE_DRAW_POINTS_SETTING, lambda *_: self.update_gestures()
        )

    def append_modifier_keys(self) -> Set[carb.input.KeyboardInput]:
        if self._append_modifier_flag in CvCanvas.FLAG_TO_KEYS:
            return CvCanvas.FLAG_TO_KEYS[self._append_modifier_flag]
        return set()

    def destroy(self):
        if self._sub_setting is not None:
            self._settings.unsubscribe_to_change_events(self._sub_setting)
            self._sub_setting = None

    def is_append_modifier_down(self) -> bool:
        if self._append_modifier_flag in CvCanvas.FLAG_TO_KEYS:
            for key in CvCanvas.FLAG_TO_KEYS[self._append_modifier_flag]:
                if self._input.get_keyboard_value(None, key) > 0:
                    return True
        return False

    def on_build(self):
        if not self.enabled or not self._basis_curves_list:
            return

        self._marquee_screen = sc.Screen()
        self._marquee_root = sc.Transform(look_at=sc.Transform.LookAt.CAMERA)
        self._scene_marquee_rect_item = None
        self.update_gestures()

    def update_gestures(self):
        if self._marquee_screen:
            drawing = self._settings.get(CURVE_DRAW_POINTS_SETTING)
            gestures = []
            if self._edit_modifier_flag or not drawing:
                # marquee selection overlay to get mouse input
                gestures.append(MarqueeGesture(weakref.proxy(self)))
            if self._viewport_api is not None:
                if self._edit_modifier_flag:
                    gestures.append(RaycastGesture(weakref.proxy(self), modifier_flags=self._edit_modifier_flag))
                    gestures.append(
                        RaycastGesture(
                            weakref.proxy(self), modifier_flags=self._append_modifier_flag | self._edit_modifier_flag
                        )
                    )
                elif drawing:
                    gestures.append(RaycastGesture(weakref.proxy(self)))
                    gestures.append(RaycastGesture(weakref.proxy(self), modifier_flags=self._append_modifier_flag))
                    gestures.append(RaycastHoverGesture(weakref.proxy(self)))
            self._marquee_screen.gestures = gestures

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if value != self._enabled:
            if self._marquee_screen:
                self._marquee_screen.visible = False

            if self._marquee_root:
                self._marquee_root.visible = False

            self._enabled = value

        if self._enabled:
            self._snap_manager = SnapProviderManager(viewport_api=self._viewport_api)
            self._snap_settings_listener = SnapSettingsListener(
                enabled_setting_path=None,
                move_x_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
                move_y_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
                move_z_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
                rotate_setting_path=snap_c.SNAP_ROTATE_SETTING_PATH,
                scale_setting_path=snap_c.SNAP_SCALE_SETTING_PATH,
                provider_setting_path=snap_c.SNAP_PROVIDER_NAME_SETTING_PATH,
            )
        else:
            if self._snap_settings_listener:
                self._snap_settings_listener.destroy()
                self._snap_settings_listener = None
            if self._snap_manager:
                self._snap_manager.destroy()
                self._snap_manager = None

    @property
    def curve_context(self) -> CurveManipulatorContext:
        return self._curve_context

    @curve_context.setter
    def curve_context(self, value: CurveManipulatorContext):
        self._curve_context = value

    @property
    def viewport_api(self):
        return self._viewport_api

    @viewport_api.setter
    def viewport_api(self, value):
        if self._viewport_api == value:
            return

        self._viewport_api = value
        if self._snap_manager:
            self._snap_manager.destroy()
            self._snap_manager = SnapProviderManager(viewport_api=self._viewport_api)

    @property
    def basis_curves_list(self) -> List[UsdGeom.BasisCurves]:
        return self._basis_curves_list

    @basis_curves_list.setter
    def basis_curves_list(self, value):
        if self._basis_curves_list != value:
            self._basis_curves_list = value

            self.invalidate()

    @property
    def selection(self) -> CvSelection:
        return self._selection

    @selection.setter
    def selection(self, value: CvSelection):
        self._selection = value

    @property
    def snap_manager(self) -> SnapProviderManager:
        return self._snap_manager

    @carb.profiler.profile
    def _on_marquee_changed(self, ndc_start, ndc_end, finished: bool):
        if self._marquee_start != ndc_start or self._marquee_end != ndc_end:
            self._marquee_start = ndc_start
            self._marquee_end = ndc_end

            if ndc_start is not None and ndc_end is not None:

                ndc_depth = 1
                start = self._marquee_root.transform_space(
                    sc.Space.NDC, sc.Space.OBJECT, (ndc_start[0], ndc_start[1], ndc_depth)
                )
                end = self._marquee_root.transform_space(
                    sc.Space.NDC, sc.Space.OBJECT, (ndc_end[0], ndc_end[1], ndc_depth)
                )

                avg_z = (start[2] + end[2]) * 0.5
                points = (
                    (start[0], start[1], avg_z),
                    (end[0], start[1], avg_z),
                    (end[0], end[1], avg_z),
                    (start[0], end[1], avg_z),
                )
                npoints = len(points)
                faces = [x for x in range(npoints)]

                if not self._scene_marquee_rect_item:
                    with self._marquee_root:
                        self._scene_marquee_rect_item = sc.PolygonMesh(
                            points,
                            [cl.white] * npoints,
                            [npoints],
                            faces,
                            wireframe=True,
                            thicknesses=[1] * npoints,
                            visible=True,
                        )

                self._scene_marquee_rect_item.positions = points
                self._scene_marquee_rect_item.visible = True

        if finished:
            selected_cvs: Set[Tuple[UsdGeom.BasisCurves, int]] = set()

            if self._marquee_start is not None and self._marquee_end is not None:
                min_x = min(ndc_start[0], ndc_end[0])
                min_y = min(ndc_start[1], ndc_end[1])
                max_x = max(ndc_start[0], ndc_end[0])
                max_y = max(ndc_start[1], ndc_end[1])
                xform_cache = UsdGeom.XformCache()
                for basis_curves in self._basis_curves_list:
                    points = basis_curves.GetPointsAttr().Get()
                    if not points:
                        continue

                    xform = xform_cache.GetLocalToWorldTransform(basis_curves.GetPrim())
                    for id, position in enumerate(points):
                        world_pos = xform.Transform(position)
                        ndc_pos = self.transform_space(
                            sc.Space.WORLD, sc.Space.NDC, [world_pos[0], world_pos[1], world_pos[2]]
                        )

                        if min_x <= ndc_pos[0] <= max_x and min_y <= ndc_pos[1] <= max_y:
                            selected_cvs.add((basis_curves, id))

            selected_cvs_set = self._selection.get_selected_cvs().copy()
            select_mode = self._get_selection_mode()
            if select_mode == SelectMode.MERGE_SELECTION:
                selected_cvs_set.update(selected_cvs)
            elif select_mode == SelectMode.INVERT_SELECTION:
                for pair in selected_cvs:
                    if pair in selected_cvs_set:
                        selected_cvs_set.discard(pair)
                    else:
                        selected_cvs_set.add(pair)
            else:
                selected_cvs_set = selected_cvs

            omni.kit.commands.execute("SetCvSelection", selection=self._selection, selected_cvs=selected_cvs_set)

            if self._scene_marquee_rect_item:
                self._scene_marquee_rect_item.visible = False

            self._marquee_start = None
            self._marquee_end = None

    def _get_selection_mode(self):
        def test_down(key_a, key_b):
            return bool(
                (self._input.get_keyboard_button_flags(None, key_a) & carb.input.BUTTON_FLAG_DOWN)
                or (self._input.get_keyboard_button_flags(None, key_b) & carb.input.BUTTON_FLAG_DOWN)
            )

        KeyboardInput = carb.input.KeyboardInput
        shift_down = test_down(KeyboardInput.LEFT_SHIFT, KeyboardInput.RIGHT_SHIFT)
        if shift_down:
            return SelectMode.MERGE_SELECTION
        ctrl_down = test_down(KeyboardInput.LEFT_CONTROL, KeyboardInput.RIGHT_CONTROL)
        if ctrl_down:
            return SelectMode.INVERT_SELECTION
        return SelectMode.RESET_AND_SELECT
