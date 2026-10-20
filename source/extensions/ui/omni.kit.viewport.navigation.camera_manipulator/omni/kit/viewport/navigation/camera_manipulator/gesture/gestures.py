# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = [
    "NaviBarBindings",
    "build_gestures",
    "NaviBarPanGesture",
    "NaviBarTumbleGesture",
    "NaviBarLookGesture",
    "NaviBarZoomGesture",
]

from typing import Callable, Sequence

import carb
import carb.settings
from omni.kit.manipulator.camera import LookGesture, PanGesture, TumbleGesture, ZoomGesture
from omni.kit.viewport.navigation.core import NAVIGATION_TOOL_OPERATION_ACTIVE
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.window.cursor import get_main_window_cursor
from omni.ui import scene as sc
from pxr import Gf

from ..common import (
    EXTEND_CURSOR_GRAB_CLOSE,
    EXTEND_CURSOR_ORBIT,
    NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE,
    NAVIGATION_TOOL_MIN_COI_DISTANCE,
)
from ..orbit_target import OrbitTarget

DEFAULT_MIN_COI_DISTANCE = 1.0
DEFAULT_MAX_NAVIGATION_MAGNITUDE = 2000.0


def _get_min_navigation_magnitude():
    settings = carb.settings.acquire_settings_interface()
    return settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or DEFAULT_MIN_COI_DISTANCE


def _get_max_navigation_magnitude():
    settings = carb.settings.acquire_settings_interface()
    return settings.get(NAVIGATION_TOOL_MAX_NAVIGATION_MAGNITUDE) or DEFAULT_MAX_NAVIGATION_MAGNITUDE


def _clamp_components(values):
    """Clamp vector-like components to configured absolute-value bounds.

    This keeps navigation scaling from collapsing to a near-zero value after
    dolly-close or other camera states that produce extremely small factors,
    while also capping oversized components.
    """
    if not values:
        return values

    min_mag = _get_min_navigation_magnitude()
    max_mag = max(_get_max_navigation_magnitude(), min_mag)
    if all(min_mag <= abs(v) <= max_mag for v in values):
        return values

    clamped_values = []
    for value in values:
        sign = -1 if value < 0 else 1
        abs_value = abs(value)
        if abs_value < min_mag:
            clamped_values.append(sign * min_mag)
        elif abs_value > max_mag:
            clamped_values.append(sign * max_mag)
        else:
            clamped_values.append(value)
    return clamped_values


def _clamp_ndc_scale(ndc_scale):
    """Clamp ndc_scale components to configured absolute-value bounds.

    When the camera's center-of-interest distance is very small (e.g. after
    dolly-close), ndc_scale becomes tiny and navigation speed drops to near
    zero. This clamp ensures a usable minimum speed without allowing
    oversized navigation magnitudes.
    """
    return _clamp_components(ndc_scale)


def _clamp_world_speed(world_speed):
    """Clamp final world_speed so pan/dolly never stall on tiny values."""
    if world_speed is None:
        return None
    return Gf.Vec3d(*_clamp_components([world_speed[0], world_speed[1], world_speed[2]]))


NaviBarBindings = {
    "NaviBarPanGesture": "Any LeftButton",
    "NaviBarTumbleGesture": "Any LeftButton",
    "NaviBarZoomGesture": "Any LeftButton",
    "NaviBarLookGesture": "Any LeftButton",
    "NaviBarOrbitLookGesture": "Any RightButton",
}


def build_gestures(
    model: sc.AbstractManipulatorModel,
    bindings: dict = None,
    manager: sc.GestureManager = None,
    configure_model: Callable = None,
):
    def _parse_binding(binding_str: str):
        keys = binding_str.split(" ")
        button = {"LeftButton": 0, "RightButton": 1, "MiddleButton": 2}.get(keys.pop())

        modifiers = 0
        for mod_str in keys:
            mod_bit = {
                "Shift": carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
                "Ctrl": carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
                "Alt": carb.input.KEYBOARD_MODIFIER_FLAG_ALT,
                "Super": carb.input.KEYBOARD_MODIFIER_FLAG_SUPER,
                "Any": 0xFFFFFFFF,
            }.get(mod_str)
            if not mod_bit:
                raise RuntimeError(f"Unparseable binding: {binding_str}")
            modifiers = modifiers | mod_bit

        return (button, modifiers)

    if not bindings:
        bindings = NaviBarBindings
    gestures = []
    for gesture, binding in bindings.items():
        instantiator = globals().get(gesture)
        if not instantiator:
            carb.log_warn(f'Gesture "{gesture}" was not found for key-binding: "{binding}"')
            continue
        button, modifers = _parse_binding(binding)
        gestures.append(instantiator(model, configure_model, mouse_button=button, modifiers=modifers, manager=manager))
    return gestures


def get_current_navigation() -> str:
    settings = carb.settings.acquire_settings_interface()
    return settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)


class NaviBarPanGesture(PanGesture):
    @property
    def world_speed(self):
        model = self.model
        ndc_scale = _optional_floats(model, "ndc_scale")
        world_speed_vals = _optional_floats(model, "world_speed")
        if ndc_scale:
            ndc_scale = _clamp_ndc_scale(ndc_scale)
        if world_speed_vals and ndc_scale:
            return _clamp_world_speed(
                Gf.Vec3d(
                    world_speed_vals[0] * ndc_scale[0],
                    world_speed_vals[1] * ndc_scale[1],
                    world_speed_vals[2] * ndc_scale[2],
                )
            )
        if world_speed_vals:
            return _clamp_world_speed(Gf.Vec3d(world_speed_vals[0], world_speed_vals[1], world_speed_vals[2]))
        if ndc_scale:
            return _clamp_world_speed(Gf.Vec3d(ndc_scale[0], ndc_scale[1], ndc_scale[2]))
        return _clamp_world_speed(super().world_speed)

    def on_mouse_move(self, mouse_moved):
        current_navigation = get_current_navigation()
        if current_navigation != "pan":
            return
        model = self.model
        item = model.get_item("fly_speed")
        if item:
            values = model.get_as_floats(item)
        else:
            values = [1]
        super().on_mouse_move([mouse_moved[0] * values[0], mouse_moved[1] * values[0]])


class NaviBarTumbleGesture(TumbleGesture):
    def __init__(self, model, configure_model=None, name: str = None, *args, **kwargs):
        super().__init__(model, configure_model, name, *args, **kwargs)
        self._orbit_target_validated = False
        self._current_orbit_target = None

    def on_began(self):
        # Store the orbit target on began, because it might change before moving mouse (double click may happen)
        self._current_orbit_target = OrbitTarget().target_indicator_model.display_position
        super().on_began()

    def on_mouse_move(self, mouse_moved):
        current_navigation = get_current_navigation()
        if current_navigation != "orbit":
            return

        if not self._orbit_target_validated:
            orbit_target = OrbitTarget()
            if not orbit_target.target_valid:
                # Set focus distance to 5M even without an orbit target
                orbit_target.set_default_focus_distance()
                super().on_began()

                orbit_target.handle_notification(True)
            else:
                # Check if orbit target is still the same as on_began, if not, need to re-run on_began()
                current_target = orbit_target.target_indicator_model.display_position
                if current_target != self._current_orbit_target:
                    super().on_began()
                    self._current_orbit_target = current_target

            get_main_window_cursor().override_cursor_shape_extend(EXTEND_CURSOR_GRAB_CLOSE)

            self._orbit_target_validated = True

        super().on_mouse_move(mouse_moved)

    def on_ended(self):
        self._orbit_target_validated = False
        self._current_orbit_target = None
        super().on_ended()
        # Set cursor back to previous state
        cursor = get_main_window_cursor()
        cursor.override_cursor_shape_extend(EXTEND_CURSOR_ORBIT)


class NaviBarOrbitLookGesture(sc.DragGesture):
    """
    A dummy look gesture for orbit tool, we need invalidate orbit target after look
    """

    def __init__(self, *args, **kwargs):
        super().__init__(name="NaviBarOrbitLookGesture", **kwargs)
        self._prev_cam_z_dir = None
        self._viewport_api = get_active_viewport()

    def on_changed(self):
        current_navigation = get_current_navigation()
        if current_navigation != "orbit":
            return

        orbit_target = OrbitTarget()

        if orbit_target.target_valid:
            z_dir = self._viewport_api.transform.GetRow3(2)
            if self._prev_cam_z_dir is None:
                orbit_target.lock_target = True
                self._prev_cam_z_dir = z_dir
            else:
                # Any changes to camera facing direction by dragging mouse or pressing Q/E/A/D
                # will make the orbit target invalid
                if not Gf.IsClose(self._prev_cam_z_dir, z_dir, 1e-3):
                    orbit_target.target_valid = False
                else:
                    self._prev_cam_z_dir = z_dir

    def on_ended(self):
        self._prev_cam_z_dir = None

        current_navigation = get_current_navigation()
        if current_navigation != "orbit":
            return

        # If target turns invalid in on_changed, we need to hide the target
        orbit_target = OrbitTarget()
        orbit_target.lock_target = False
        orbit_target.validate_target_on_end()
        if not orbit_target.target_valid:
            orbit_target.target_indicator_model.visible = False


class NaviBarLookGesture(LookGesture):
    def on_mouse_move(self, mouse_moved):
        current_navigation = get_current_navigation()
        if current_navigation != "look":
            return
        super().on_mouse_move(mouse_moved)


def _optional_floats(model: sc.AbstractManipulatorModel, item: str, default_value: Sequence[float] = None):
    item = model.get_item(item)
    if item:
        values = model.get_as_floats(item)
        if values:
            return values
    return default_value


class NaviBarZoomGesture(ZoomGesture):
    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.__orth_zoom = False

    @property
    def world_speed(self):
        model = self.model
        fly_speed = _optional_floats(model, "fly_speed", [1.0])
        ndc_scale = _optional_floats(model, "ndc_scale")
        world_speed = _optional_floats(model, "world_speed")
        if ndc_scale:
            ndc_scale = _clamp_ndc_scale(ndc_scale)
        if world_speed and ndc_scale:
            return _clamp_world_speed(
                Gf.Vec3d(
                    world_speed[0] * ndc_scale[0] * fly_speed[0],
                    world_speed[1] * ndc_scale[1] * fly_speed[0],
                    world_speed[2] * ndc_scale[2] * fly_speed[0],
                )
            )
        if world_speed:
            return _clamp_world_speed(Gf.Vec3d(world_speed[0], world_speed[1], world_speed[2]))
        if ndc_scale:
            return _clamp_world_speed(Gf.Vec3d(ndc_scale[0], ndc_scale[1], ndc_scale[2]))

        return _clamp_world_speed(Gf.Vec3d(1, 1, 1))

    def on_mouse_move(self, mouse_moved):
        current_navigation = get_current_navigation()
        if current_navigation != "dolly":
            return

        super().on_mouse_move(mouse_moved)
