# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple

import carb.input
import carb.settings
from carb.input import KeyboardInput
from omni import ui
from omni.ui import scene as sc
from pxr import UsdGeom

from ...common import (
    MeasureCreationState,
    MeasureMode,
    MeasureState,
    Precision,
    SnapMode,
    UnitType,
    convert_area_to_units,
    convert_distance_and_units,
    get_stage_units,
)
from ...manager import ReferenceManager, StateMachine
from ..manipulator_items import *
from ..snap.manager import MeasureSnapProviderManager


class GesturePreventionManager(sc.GestureManager):
    """
    Hide Other Gestures
    """

    def __init__(self):
        super().__init__()

    def __del__(self):
        pass

    def can_be_prevented(self, gesture: sc.AbstractGesture) -> bool:
        return True

    def should_prevent(self, gesture: sc.AbstractGesture, preventer: sc.AbstractGesture) -> bool:
        if StateMachine().tool_state == MeasureState.NONE or StateMachine().tool_mode == MeasureMode.NONE:
            return True
        if gesture.name.endswith(StateMachine().tool_mode.name):
            return False
        return True


class CameraManipModeWatcher:
    __instance = None

    CAMERA_MANIP_MODE = "/exts/omni.kit.manipulator.camera/viewportMode"

    def __init__(self):
        self._camera_manip_mode_active = False

        self._settings = carb.settings.get_settings()
        self._camera_manip_mode_sub_0 = self._settings.subscribe_to_node_change_events(
            f"{CameraManipModeWatcher.CAMERA_MANIP_MODE}/0", self._cam_manip_mode_changed
        )
        self._camera_manip_mode_sub_1 = self._settings.subscribe_to_node_change_events(
            f"{CameraManipModeWatcher.CAMERA_MANIP_MODE}/1", self._cam_manip_mode_changed
        )
        self._input = carb.input.acquire_input_interface()
        self._check_current_state()

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._camera_manip_mode_sub_0:
            self._settings.unsubscribe_to_change_events(self._camera_manip_mode_sub_0)
            self._camera_manip_mode_sub_0 = None

        if self._camera_manip_mode_sub_1:
            self._settings.unsubscribe_to_change_events(self._camera_manip_mode_sub_1)
            self._camera_manip_mode_sub_1 = None

    def _cam_manip_mode_changed(self, item, event_type):
        self._check_current_state()

    def _check_current_state(self):
        cam_manip_active = self._settings.get(CameraManipModeWatcher.CAMERA_MANIP_MODE)
        if cam_manip_active and len(cam_manip_active) > 1:
            self._camera_manip_mode_active = cam_manip_active[1] != ""

    def is_camera_manip_mode_active(self):
        if self._camera_manip_mode_active:
            return True

        # Backup, if for whatever reason the settings listener doesn't work
        # Like, for example the very first camera manipulation after launching kit
        # only sets this setting for the first time on mouse release .. every time after that it
        # works fine.
        #
        # But just in case there are more such cases .. let's keep this as a backup for now :)
        #
        for key in [carb.input.KeyboardInput.LEFT_ALT, carb.input.KeyboardInput.RIGHT_ALT]:
            if bool(self._input.get_keyboard_button_flags(None, key) & carb.input.BUTTON_FLAG_DOWN):
                return True

        return False

    @staticmethod
    def get_instance():
        if not CameraManipModeWatcher.__instance:
            CameraManipModeWatcher.__instance = CameraManipModeWatcher()
        return CameraManipModeWatcher.__instance

    @staticmethod
    def delete_instance():
        if CameraManipModeWatcher.__instance is not None:
            CameraManipModeWatcher.__instance.destroy()
        CameraManipModeWatcher.__instance = None


class _PickHit:
    """A viewport pick hit in the shape the snap providers read (target path, hit position and normal).

    It has no ``primitive_id``: pick hits carry no mesh face, so the Vertex, Edge and Mid Point snaps are unsupported.
    """

    def __init__(self, path: str, hit_position, normal):
        self.valid = True
        self.hit_position = hit_position
        self.normal = normal
        self._path = path

    def get_target_usd_path(self) -> str:
        return self._path


class ViewportModeModel(sc.AbstractManipulatorModel):
    """
    The model tracks attributes and functionality for drawing
    for the specified mode create and edit states.
    """

    def __init__(self, viewport_api, mode: MeasureMode = MeasureMode.NONE):
        from ._scene_widget import SnapMarker  # Import here to prevent circular imports

        super().__init__()
        self._api = viewport_api
        self._snap: MeasureSnapProviderManager = MeasureSnapProviderManager()
        self._snap_data: Optional[Dict[str, Any]] = {}
        self._camera_manip_mode_watcher = CameraManipModeWatcher.get_instance()
        self._ignore_current_drag = False

        self._mode: MeasureMode = mode
        self._state: ui.SimpleIntModel = ui.SimpleIntModel()
        self._creation_state: ui.SimpleIntModel = ui.SimpleIntModel()
        self._enabled_model: ui.SimpleBoolModel = ui.SimpleBoolModel()

        self._state.add_value_changed_fn(self.__on_tool_state_changed)
        self._creation_state.add_value_changed_fn(self.__on_creation_state_changed)
        self._enabled_model.add_value_changed_fn(self.__on_enabled_changed)

        # Scene UI
        self.__base: sc.Transform = sc.Transform()
        with self.__base:
            self._snap_marker: SnapMarker = SnapMarker()
            self._screen: sc.Screen = self.__build_screen()
            self._root: sc.Transform = sc.Transform()
            self._label_root: sc.Transform = sc.Transform()

        ReferenceManager().gesture_screen = self._screen

        self._key_sub = StateMachine().subscribe_to_key_pressed_event(self.__on_key_pressed)

    def __build_screen(self) -> sc.Screen:
        gesture_manager: GesturePreventionManager = GesturePreventionManager()

        move_gesture = sc.HoverGesture(
            name=f"move_{self._mode.name}",
            on_changed_fn=lambda sender: self.__on_moved(sender),
            manager=gesture_manager,
        )
        drag_gesture = sc.DragGesture(
            name=f"drag_{self._mode.name}",
            on_began_fn=lambda sender: self.__on_begin_drag(sender),
            on_changed_fn=lambda sender: self.__on_drag(sender),
            on_ended_fn=lambda sender: self.__on_end_drag(sender),
            manager=gesture_manager,
        )

        ## Unfortuantely the ClickGesture is really agressive in regards to what it treats as a click and what not.
        ## If the user ever so slightly moves the mouse between mouse down and up, it is no longer treated as a click
        ## and instead *only* as a drag.
        ##
        ## However, every single click is *always* also a drag .. therefore, we are no longer watching for the
        ## ClickGesture for the left mouse button, but are instead using the DragGesture's on_ended and treat
        ## that one as a left click :)
        ##
        ## The better solution would be to fix the ClickGesture, so it always triggers - no matter how far the mouse has
        ## moved between press and release. Or at the very least allow for a little threshold of mouse movement.
        ##
        ##  - Daniela

        # left_click_gesture = sc.ClickGesture(
        #     name=f"left_click_{self._mode.name}",
        #     mouse_button=0,
        #     on_ended_fn=lambda sender: self.__on_clicked(sender, 0),
        #     manager=gesture_manager
        # )

        right_click_gesture = sc.ClickGesture(
            name=f"right_click_{self._mode.name}",
            mouse_button=1,
            on_ended_fn=lambda sender: self.__on_clicked(sender, 1),
            manager=gesture_manager,
        )
        middle_click_gesture = sc.ClickGesture(
            name=f"middle_click_{self._mode.name}",
            mouse_button=2,
            on_ended_fn=lambda sender: self.__on_clicked(sender, 2),
            manager=gesture_manager,
        )

        return sc.Screen(
            gestures=[
                move_gesture,
                drag_gesture,
                # left_click_gesture, ## See long comment a few lines above
                right_click_gesture,
                middle_click_gesture,
            ]
        )

    @property
    def enabled(self) -> bool:
        return self._enabled_model.as_bool

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled_model.as_bool = value

    @property
    def state(self) -> MeasureState:
        return MeasureState(self._state.as_int)

    @state.setter
    def state(self, state: MeasureState) -> None:
        self._state.as_int = state.value

    @property
    def creation_state(self) -> MeasureCreationState:
        return MeasureCreationState(self._creation_state.as_int)

    @creation_state.setter
    def creation_state(self, state: MeasureCreationState) -> None:
        self._creation_state.as_int = state.value

    # Model Callbacks
    def __on_tool_state_changed(self, model: ui.AbstractValueModel) -> None:
        tool_state: MeasureState = MeasureState(model.as_int)
        if tool_state == MeasureState.CREATE:
            self.creation_state = MeasureCreationState.START_SELECTION
        elif tool_state == MeasureState.EDIT:
            pass
        else:
            self.reset()

    def __on_creation_state_changed(self, model: ui.AbstractValueModel) -> None:
        creation_state: MeasureCreationState = MeasureCreationState(model.as_int)
        StateMachine().tool_creation_state = creation_state
        if creation_state == MeasureCreationState.NONE:  # May be redundant? Potentially just need to return
            self.reset()
            return

        if creation_state == MeasureCreationState.START_SELECTION:
            # set snaps active
            MeasureSnapProviderManager().enabled = True
            ReferenceManager().ui_placement_panel.lock_properties(False)
            ReferenceManager().ui_display_panel.lock_properties(False)
        elif creation_state in [MeasureCreationState.INTERMEDIATE_SELECTION, MeasureCreationState.END_SELECTION]:
            ReferenceManager().ui_placement_panel.lock_properties(True)
            ReferenceManager().ui_display_panel.lock_properties(True)
            self.draw()
        elif creation_state == MeasureCreationState.FINALIZE:
            # deactivate snaps
            MeasureSnapProviderManager().enabled = False
            self.draw()

    def __on_enabled_changed(self, model: ui.AbstractValueModel) -> None:
        value = model.as_bool
        self._root.clear() if value else self.draw()

    def _set_snap_marker_position(self, coord: Optional[Gf.Vec3d], mode: SnapMode = SnapMode.SURFACE):
        self._snap_marker.set_snap_marker(coord, mode)
        # self._snap_marker.positions = [[*coord]] if coord else []

    # Gesture Callbacks
    def __coords_in_viewport(self, coords: Sequence[float]) -> bool:
        return self._api.map_ndc_to_texture(coords)[-1] is not None

    def __on_moved(self, sender):
        if self._camera_manip_mode_watcher.is_camera_manip_mode_active():
            return

        ndc_location = sender.gesture_payload.mouse

        # The viewport's pick query returns the hit prim, the world position and, when the viewport provides it,
        # the surface normal. An empty path is a miss.
        def on_query_complete(path, world_pos, *args):
            if not path or world_pos is None:
                self._set_snap_marker_position(None)
                return
            normal = args[1] if len(args) > 1 else None
            if normal is None:
                stage = self._api.stage
                up_axis = UsdGeom.GetStageUpAxis(stage) if stage else UsdGeom.Tokens.y
                normal = (0.0, 1.0, 0.0) if up_axis == UsdGeom.Tokens.y else (0.0, 0.0, 1.0)
            hit = _PickHit(str(path), (world_pos[0], world_pos[1], world_pos[2]), (normal[0], normal[1], normal[2]))
            self._on_moved(ndc_location, hit)

        if self.__coords_in_viewport(ndc_location):
            coords = self._api.map_ndc_to_texture_pixel(ndc_location)[0]
            if coords:
                try:
                    self._api.request_query(coords, on_query_complete, query_name="measure_snap", include_normal=True)
                except TypeError:
                    # A viewport whose pick query has no include_normal option: positions only.
                    self._api.request_query(coords, on_query_complete, query_name="measure_snap")

    def _generate_picking_ray(self, ndc_location: Sequence[float]) -> Tuple[Sequence[float], Sequence[float], float]:
        """
        A helper function to generate picking ray from ndc cursor location.
        """
        ndc_near = (ndc_location[0], ndc_location[1], -1)
        ndc_far = (ndc_location[0], ndc_location[1], 1)
        view = self._api.view
        proj = self._api.projection
        view_proj_inv = (view * proj).GetInverse()

        origin = view_proj_inv.Transform(ndc_near)
        dir = view_proj_inv.Transform(ndc_far) - origin
        dist = dir.Normalize()

        # Don't use (*origin) to unpack Gf Types. Very Slow
        return ((origin[0], origin[1], origin[2]), (dir[0], dir[1], dir[2]), dist)

    def __on_begin_drag(self, sender):
        if self._camera_manip_mode_watcher.is_camera_manip_mode_active():
            self._ignore_current_drag = True
            return

        self._ignore_current_drag = False
        ndc_coord = sender.gesture_payload.mouse
        if self.__coords_in_viewport(ndc_coord):
            self._on_begin_drag(ndc_coord)

    def __on_drag(self, sender):
        if self._camera_manip_mode_watcher.is_camera_manip_mode_active():
            self._ignore_current_drag = True
            return

        if self._ignore_current_drag:
            return

        ndc_coord = sender.gesture_payload.mouse
        if self.__coords_in_viewport(ndc_coord):
            self._on_drag(ndc_coord)

    def __on_end_drag(self, sender):
        if self._camera_manip_mode_watcher.is_camera_manip_mode_active():
            return

        if self._ignore_current_drag:
            # The Camera Manipulation Gesture's drag ends before ours, so we have to check if it was
            # active during on_begin_drag or on_drag, and if so then ignore our on_drag_end here.
            return

        ndc_coord = sender.gesture_payload.mouse
        if self.__coords_in_viewport(ndc_coord):
            self._on_end_drag(ndc_coord)

            # Treating a drag end as a click
            self._on_clicked(ndc_coord, 0)

    def __on_clicked(self, sender, mouse_button: int):
        if self._camera_manip_mode_watcher.is_camera_manip_mode_active():
            return

        ndc_coord = sender.gesture_payload.mouse
        if self.__coords_in_viewport(ndc_coord):
            self._on_clicked(ndc_coord, mouse_button)

    def __on_key_pressed(self, key: KeyboardInput):
        match key:
            case KeyboardInput.ENTER | KeyboardInput.NUMPAD_ENTER:
                self._try_auto_complete_and_save()
        return

    # Generic functions
    def _get_unit_type(self) -> UnitType:
        disp_panel = ReferenceManager().ui_display_panel
        return disp_panel.unit or get_stage_units(as_enum=True)

    def _value_to_unit(self, value, is_area: bool = False) -> Tuple[float, str]:
        unit_type = self._get_unit_type().value.lower()
        if is_area:
            return convert_area_to_units(value, unit_type), unit_type
        return convert_distance_and_units(value, unit_type)

    def _get_precision_value(self) -> int:
        disp_panel = ReferenceManager().ui_display_panel
        return list(Precision).index(disp_panel.precision.value)

    def _get_display_color(self) -> List[float]:
        color = ReferenceManager().ui_display_panel.color
        return [color[0], color[1], color[2], color[3]]  # Convert from Gf.Vec4f to List

    # Abstract methods
    @abstractmethod
    def reset(self):
        """
        Reset the data tied to the model
        """
        self.state = MeasureState.NONE
        self.creation_state = MeasureCreationState.NONE
        self._set_snap_marker_position(None, SnapMode.SURFACE)

    @abstractmethod
    def draw(self):
        """
        Draw based on the state and mode
        """
        return

    def _try_auto_complete_and_save(self):
        return

    @abstractmethod
    def _on_save(self):
        """
        Step when ready to save a measurement
        """
        return

    @abstractmethod
    def _on_moved(self, coords: Sequence[float], prim_path: str):
        return

    @abstractmethod
    def _on_clicked(self, coords: Sequence[float], mouse_button: int = 0):
        return

    # These drag methods can be overwritten by derived classes, but
    # due to how Kit treats a click as a drag when he mouse cursor ever
    # so slightly moved during mouse down and up, we aren't using these
    # and instead handle on_drag_end as a click :)
    def _on_begin_drag(self, coords: Sequence[float]):
        return

    def _on_drag(self, coords: Sequence[float]):
        return

    def _on_end_drag(self, coords: Sequence[float]):
        return
