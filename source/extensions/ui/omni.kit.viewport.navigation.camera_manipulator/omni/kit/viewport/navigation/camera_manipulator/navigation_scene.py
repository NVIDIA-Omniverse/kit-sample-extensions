import time
from functools import partial
from typing import Dict

import carb
import carb.events
import omni.kit.app
import omni.kit.viewport.utility as vp_util
import omni.timeline
from omni import ui
from omni.kit.manipulator.camera import ViewportCameraManipulator
from omni.kit.viewport.navigation.core import NAVIGATION_TOOL_OPERATION_ACTIVE
from omni.kit.window.cursor import get_main_window_cursor
from omni.ui import scene as sc
from pxr import Gf

from .common import *
from .gesture import (
    NaviBarBindings,
    NaviBarLookGesture,
    NaviBarPanGesture,
    NaviBarTumbleGesture,
    NaviBarZoomGesture,
    build_gestures,
)
from .icons import Icons
from .navigation_engine import NavigationEngine
from .orbit_target import OrbitTarget


class PreventOthers(sc.GestureManager):
    """
    Hide other gestures
    """

    def __init__(self):
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._white_list = ["PanGesture", "TumbleGesture", "LookGesture", "ZoomGesture", "ZoomScrollGesture"]
        self._prev_click_time = None

    def __del__(self):
        pass

    def amend_input(self, input):
        current_navigation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        if current_navigation == "orbit":
            # OMFP-3097: Accept double click with longer interval between clicks
            if input.double_clicked == 0 and input.clicked == 1:
                # Clicked position between current and previous click will be validated in gesture's preprocess
                curr_time = time.time()

                if self._prev_click_time is not None:
                    # Convert to millisecond to compare
                    time_delta = (curr_time - self._prev_click_time) * 1000
                    max_interval = self._settings.get("/exts/omni.ui/clickGesture/multiClickWait")
                    if time_delta < max_interval:
                        input.double_clicked = 1

                self._prev_click_time = curr_time

        return super().amend_input(input)

    def can_be_prevented(self, gesture):
        current_navigation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        return current_navigation == "none"

    def should_prevent(self, gesture, preventer):
        current_navigation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        if current_navigation == "none":
            return False

        # OM-58779: Navigation should not prevent right click
        if isinstance(gesture, sc.ClickGesture):
            if gesture.name == "":
                return False

        op_table = {
            "pan": "NaviBarPanGesture",
            "orbit": "NaviBarTumbleGesture",
            "look": "NaviBarLookGesture",
            "dolly": "NaviBarZoomGesture",
        }
        name = op_table.get(current_navigation, "none")
        if current_navigation in op_table.keys():
            return (gesture.name != name) and (gesture.name not in self._white_list)
        else:
            return gesture.name not in self._white_list


class OrbitTargetIndicator(sc.Manipulator):
    """
    An indicator to show where the orbit target is
    """

    def __init__(self, enabled, **kwargs):
        super().__init__(**kwargs)
        self._enabled = enabled
        self._orbit_target_xform = None

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if self._enabled != value:
            self._enabled = value

            if not self._enabled:
                if self._orbit_target_xform is not None:
                    self._orbit_target_xform.visible = False
            else:
                self.invalidate()

    def destroy(self):  # pragma: no cover
        if self._orbit_target_xform:
            self._orbit_target_xform.clear()
            self._orbit_target_xform = None

        self.clear()

    def on_build(self):
        if not self._enabled:
            return

        self._orbit_target_xform = sc.Transform()

        if not self.model.visible:
            self._orbit_target_xform.visible = False
        else:
            target_position = self.model.display_position
            if target_position is not None:
                self._orbit_target_xform.transform = sc.Matrix44.get_translation_matrix(
                    target_position[0], target_position[1], target_position[2]
                )

        with self._orbit_target_xform:
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                with sc.Transform(scale_to=sc.Space.SCREEN):
                    sc.Image(Icons().get("cursorFocalPoint"), 50, 50)

    def on_model_updated(self, item):
        # Update indicator position
        if not self._enabled or self._orbit_target_xform is None:
            return

        if item == self.model.get_item("visible"):
            self._orbit_target_xform.visible = item.value

        elif item == self.model.get_item("display"):
            target_position = item.value

            if target_position is not None:
                self._orbit_target_xform.transform = sc.Matrix44.get_translation_matrix(
                    target_position[0], target_position[1], target_position[2]
                )


class NavigationScene:
    def __init__(self, factory_args, *ui_args, **ui_kwargs):
        self._settings = carb.settings.get_settings()
        if factory_args:

            class NaviViewportCameraManipulator(ViewportCameraManipulator):
                def __init__(self, enabled=False, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._enabled = enabled
                    self.__transform = None
                    self._viewport_api = factory_args.get("viewport_api")
                    self._cursor = get_main_window_cursor()
                    self._hover_on_viewport = False
                    self._screen = None

                @property
                def enabled(self):
                    return self._enabled

                @enabled.setter
                def enabled(self, value: bool):
                    if value != self._enabled:
                        self._enabled = value

                        if self._screen is not None:
                            self._screen.visible = self._enabled
                        else:
                            self.invalidate()

                def _on_began(self, model, mouse=None, *args, **kwargs):
                    super()._on_began(model, mouse, *args, **kwargs)
                    self._clamp_minimum_coi(model)

                def _clamp_minimum_coi(self, model):
                    """Clamp center-of-interest to a minimum distance.

                    After dolly-close, the COI stored in USD can be extremely
                    small, causing ndc_scale (and thus navigation speed) to
                    approach zero.  Resetting the COI in the model here ensures
                    that the subsequent ndc_scale calculation in
                    CameraDragGesture.on_began produces a usable value.
                    """
                    coi = model.get_as_floats("center_of_interest")
                    if not coi:
                        return
                    coi_vec = Gf.Vec3d(coi[0], coi[1], coi[2])
                    coi_length = coi_vec.GetLength()
                    settings = carb.settings.get_settings()
                    min_distance = settings.get(NAVIGATION_TOOL_MIN_COI_DISTANCE) or 1.0
                    if 0 < coi_length < min_distance:
                        new_coi = coi_vec.GetNormalized() * min_distance
                        model.set_floats(
                            "center_of_interest",
                            [new_coi[0], new_coi[1], new_coi[2]],
                        )

                def _on_orbit_double_clicked(self, sender):
                    current_navigation = carb.settings.get_settings().get(NAVIGATION_TOOL_OPERATION_ACTIVE)
                    if current_navigation != "orbit":
                        return
                    orbit_target = OrbitTarget()
                    mx, my = sender.gesture_payload.mouse[0], sender.gesture_payload.mouse[1]
                    orbit_target.set_orbit_target(mx, my, True)

                def _on_moved(self, sender):
                    if self._cursor:
                        current_navigation = carb.settings.get_settings().get(NAVIGATION_TOOL_OPERATION_ACTIVE)
                        if current_navigation != "orbit":
                            return

                        is_orbit_cursor = self._cursor.get_cursor_shape_override_extend() in (
                            EXTEND_CURSOR_ORBIT,
                            EXTEND_CURSOR_GRAB_CLOSE,
                        )
                        if self._hover_on_viewport:
                            if not is_orbit_cursor:
                                self._cursor.override_cursor_shape_extend(EXTEND_CURSOR_ORBIT)
                        else:
                            if is_orbit_cursor:
                                self._cursor.override_cursor_shape_extend(CURSOR_DEFAULT)
                                self._cursor.clear_overridden_cursor_shape()

                        self._hover_on_viewport = False  # reset state

                def _on_hover(self, sender):
                    self._hover_on_viewport = True

                def on_build(self):
                    if not self._enabled:
                        return

                    # Need to hold a reference to this or the sc.Screen would be destroyed when out of scope
                    self.__transform = sc.Transform()
                    orbit_double_click_gesture = sc.DoubleClickGesture(
                        name="orbit_double_click",
                        on_ended_fn=lambda sender: self._on_orbit_double_clicked(sender),
                        manager=self.manager,
                    )
                    # Due to no notice for move from viewport to not viewport(outside or covered area)
                    # here we use two gestures to detect this state
                    move_gesture = sc.HoverGesture(
                        name="orbit_move",
                        trigger_on_view_hover=False,
                        on_changed_fn=lambda sender: self._on_moved(sender),
                        manager=self.manager,
                    )
                    hover_gesture = sc.HoverGesture(
                        name="orbit_hover",
                        trigger_on_view_hover=True,
                        on_changed_fn=lambda sender: self._on_hover(sender),
                        manager=self.manager,
                    )
                    new_gestures = build_gestures(self.model, self.bindings, self.manager, self._on_began)
                    new_gestures.append(orbit_double_click_gesture)
                    new_gestures.append(move_gesture)
                    new_gestures.append(hover_gesture)
                    with self.__transform:
                        self._screen = sc.Screen(gestures=new_gestures)

                def destroy(self):  # pragma: no cover
                    self._cursor = None
                    if self._screen:
                        self._screen.visible = False
                        self._screen = None

                    if self.__transform:
                        self.__transform.clear()
                        self.__transform = None

                    self.clear()

                    super().destroy()

            self.__manipulator = NaviViewportCameraManipulator(
                enabled=self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE) in NavigationEngine.get_name_list(),
                viewport_api=factory_args.get("viewport_api"),
            )

            self._prevent_others = PreventOthers()
            self.__manipulator.manager = self._prevent_others

            self._orbit_target_indicator = OrbitTargetIndicator(
                enabled=False, model=OrbitTarget().target_indicator_model
            )

            def setting_changed(value, event_type, set_fn):
                if event_type != carb.settings.ChangeEventType.CHANGED:
                    return
                set_fn(value.get("", None))

            self.__setting_subs = (
                omni.kit.app.SettingChangeSubscription(
                    VP1_CAM_VELOCITY, lambda *args: setting_changed(*args, self.__set_flight_velocity)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP1_CAM_INERTIA_ENABLED, lambda *args: setting_changed(*args, self.__set_inertia_enabled)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP1_CAM_INERTIA_SEC, lambda *args: setting_changed(*args, self.__set_inertia_seconds)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP2_FLY_ACCELERATION, lambda *args: setting_changed(*args, self.__set_flight_acceleration)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP2_FLY_DAMPENING, lambda *args: setting_changed(*args, self.__set_flight_dampening)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP2_LOOK_ACCELERATION, lambda *args: setting_changed(*args, self.__set_look_acceleration)
                ),
                omni.kit.app.SettingChangeSubscription(
                    VP2_LOOK_DAMPENING, lambda *args: setting_changed(*args, self.__set_look_dampening)
                ),
                omni.kit.app.SettingChangeSubscription(
                    NAVIGATION_TOOL_OPERATION_ACTIVE, lambda *args: setting_changed(*args, self.__set_visible)
                ),
            )
            settings = carb.settings.get_settings()
            settings.set_default(VP1_CAM_VELOCITY, 5.0)
            settings.set_default(VP1_CAM_INERTIA_ENABLED, False)
            settings.set_default(VP1_CAM_INERTIA_SEC, 0.55)

            settings.set_default(VP2_FLY_ACCELERATION, 1000.0)
            settings.set_default(VP2_FLY_DAMPENING, 10.0)
            settings.set_default(VP2_LOOK_ACCELERATION, 2000.0)
            settings.set_default(VP2_LOOK_DAMPENING, 20.0)
            settings.set_default(VP2_MOVE_ACCELERATION, 1000.0)
            settings.set_default(VP2_MOVE_DAMPENING, 10.0)
            settings.set_default(VP2_TUMBLE_ACCELERATION, 2000.0)
            settings.set_default(VP2_TUMBLE_DAMPENING, 20.0)

            self.__set_flight_velocity(settings.get(VP1_CAM_VELOCITY))
            self.__set_inertia_enabled(settings.get(VP1_CAM_INERTIA_ENABLED))
            self.__set_inertia_seconds(settings.get(VP1_CAM_INERTIA_SEC))

            self.__set_flight_acceleration(settings.get(VP2_FLY_ACCELERATION))
            self.__set_flight_dampening(settings.get(VP2_FLY_DAMPENING))
            self.__set_look_acceleration(settings.get(VP2_LOOK_ACCELERATION))
            self.__set_look_dampening(settings.get(VP2_LOOK_DAMPENING))
            self.__set_tumble_acceleration(settings.get(VP2_TUMBLE_ACCELERATION))
            self.__set_tumble_dampening(settings.get(VP2_TUMBLE_DAMPENING))
            self.__set_move_acceleration(settings.get(VP2_MOVE_ACCELERATION))
            self.__set_move_dampening(settings.get(VP2_MOVE_DAMPENING))

    def __set_visible(self, value):
        if value is not None:
            if value not in NavigationEngine.get_name_list():
                self.__manipulator.enabled = False
                self._orbit_target_indicator.enabled = False
            else:
                self.__manipulator.enabled = True
                if value == "orbit":
                    self._orbit_target_indicator.enabled = True

    def __set_inertia_enabled(self, value):
        if value is not None:
            self.__manipulator.model.set_ints("inertia_enabled", [1 if value else 0])

    def __set_inertia_seconds(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("inertia_seconds", [value])

    def __set_flight_velocity(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("fly_speed", [value])

    def __set_flight_acceleration(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("fly_acceleration", [value, value, value])

    def __set_flight_dampening(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("fly_dampening", [10, 10, 10])

    def __set_look_acceleration(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("look_acceleration", [value, value, value])

    def __set_look_dampening(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("look_dampening", [value, value, value])

    def __set_tumble_acceleration(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("tumble_acceleration", [value, value, value])

    def __set_tumble_dampening(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("tumble_dampening", [10, 10, 10])

    def __set_move_acceleration(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("move_acceleration", [value, value, value])

    def __set_move_dampening(self, value):
        if value is not None:
            self.__manipulator.model.set_floats("move_dampening", [value, value, value])

    def __vel_changed(self, value, event_type):
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return
        self.__set_flight_velocity(value.get("", None))

    @property
    def categories(self):
        return ["manipulator"]

    @property
    def name(self):
        return "Camera"

    def destroy(self):
        self.__setting_subs = None
        if self.__manipulator:
            self.__manipulator.destroy()
            self.__manipulator = None

        if self._orbit_target_indicator:
            self._orbit_target_indicator.destroy()
            self._orbit_target_indicator = None

    @property
    def visible(self):
        if self.__manipulator is not None:
            return self.__manipulator.visible

    @visible.setter
    def visible(self, value):
        if self.__manipulator is not None:
            self.__manipulator.visible = bool(value)


class WindowFrameRect:
    def __init__(self):
        style = {"Rectangle::position": {"background_color": 0x00000000, "border_width": 0, "border_radius": 0}}
        with ui.Placer(offset_x=0, offset_y=0, draggable=False, style=style):
            self._position = ui.Rectangle(name="position", width=100, height=100, style=style)
