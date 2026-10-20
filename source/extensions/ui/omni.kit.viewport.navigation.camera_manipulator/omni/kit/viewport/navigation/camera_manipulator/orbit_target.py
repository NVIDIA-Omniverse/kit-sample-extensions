import asyncio
import time
from typing import Callable, Optional

import carb
import carb.eventdispatcher
import carb.input
import carb.settings
import omni.appwindow
import omni.kit.app
import omni.kit.commands
import omni.kit.viewport.utility as vp_util
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility.camera_state import ViewportCameraState as VpCamera
from omni.ui import scene as sc
from pxr import Gf, Sdf, Usd, UsdGeom

PHYSICS_WAIT_FRAMES = 20
MAINTAIN_DISTANCE_SETTING_PATH = (
    "/persistent/exts/omni.kit.viewport.navigation.camera_manipulator/orbitMaintainDistanceToFocal"
)
DEFAULT_ORBIT_DISTANCE_SETTING_PATH = "exts/omni.kit.viewport.navigation.camera_manipulator/defaultOrbitDistance"
SETTING_SECTION_ENABLED = "/rtx/sectionPlane/enabled"
SETTING_SECTION_PLANE = "/rtx/sectionPlane/plane"


def Singleton(class_):
    """
    A singleton decorator.

    TODO: It's also available in other extensions. Do we have a utility extension where we can put the utilities
    like this?
    """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


def can_dispatch_event():
    return hasattr(carb.events.IEventStream, "dispatch")


def subscribe_to_event_stream_by_type(stream: carb.events.IEventStream, type: int, on_event: Callable):
    if can_dispatch_event():
        return stream.create_subscription_to_pop_by_type(type, on_event)
    else:
        return stream.create_subscription_to_push_by_type(type, on_event)


class OrbitTargetIndicatorModel(sc.AbstractManipulatorModel):
    """
    A model to hold orbit target position value
    """

    class ModelItem(sc.AbstractManipulatorItem):
        def __init__(self, value):
            super().__init__()
            self.value = value

    def __init__(self):
        super().__init__()
        self._visible_item = OrbitTargetIndicatorModel.ModelItem(False)
        self._display_item = OrbitTargetIndicatorModel.ModelItem(None)

    def get_item(self, identifier):
        if identifier == "visible":
            return self._visible_item
        elif identifier == "display":
            return self._display_item

        return None

    def get_as_floats(self, item):
        return item.value

    def set_floats(self, item, value):
        item.value = value
        self._item_changed(item)

    def set_bool(self, item, value: bool):
        item.value = value
        self._item_changed(item)

    @property
    def visible(self) -> bool:
        return self._visible_item.value

    @visible.setter
    def visible(self, value: bool):
        self.set_bool(self._visible_item, value)

    @property
    def display_position(self):
        return self._display_item.value

    @display_position.setter
    def display_position(self, value):
        self.set_floats(self._display_item, value)


@Singleton
class OrbitTarget:  # need simulate for doublclick gesture to test
    def __init__(self, usd_context_name: str = ""):
        self._usd_context = omni.usd.get_context()
        self._stage_update = omni.stageupdate.get_stage_update_interface()
        self._viewport_window = vp_util.get_active_viewport_window()
        self._viewport_api = vp_util.get_active_viewport()
        self._settings = carb.settings.get_settings()
        self._input = carb.input.acquire_input_interface()
        self._meshPaths = []
        self._rootPath = None
        self._bboxcache = None
        self._current_target_prim = None
        self._vp_view_change_sub = None
        self._keyboard_sub = None

        # Model for orbit target manipulator
        self._target_indicator_model = OrbitTargetIndicatorModel()
        self._enabled = False

        # Toast notifcation to notify user target is invalid
        self._target_notification = None
        # Flag to control if current target is valid
        self._target_valid: bool = False
        # Flag to indicate if current target is locked, happens in RMB drag/WASD (LookGesture)
        self._lock_target = False
        # Use 5M default distance when target became valid
        self._use_default_orbit_distance = True

        usd_context = omni.usd.get_context(usd_context_name)
        self._stage_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.viewport.navigation.camera_manipulator.OrbitTarget",
            event_name=usd_context.stage_event_name(omni.usd.StageEventType.OPENING),
            on_event=self._on_stage_opening,
        )

        if self._enabled:
            self._subcribe_to_vp_and_inputs()

    @property
    def target_valid(self):
        return self._target_valid

    @target_valid.setter
    def target_valid(self, value):
        self._target_valid = value

        if not value:
            # When target become invalid, set self._use_default_orbit_distance
            # Next time when target is set, default distance will be used
            self._use_default_orbit_distance = True

    @property
    def lock_target(self):
        return self._lock_target

    @lock_target.setter
    def lock_target(self, value: bool):
        self._lock_target = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if self._enabled != value:
            self._enabled = value

            # Reset status
            self.target_valid = False
            self._lock_target = False
            self._target_indicator_model.visible = False
            self._target_indicator_model.display_position = None

            if value is False:
                self._vp_view_change_sub = None
                self._section_tool_sub = None

                if self._keyboard_sub:
                    keyboard = omni.appwindow.get_default_app_window().get_keyboard()
                    self._input.unsubscribe_to_keyboard_events(keyboard, self._keyboard_sub)
                    self._keyboard_sub = None

                self.handle_notification(show=False)
            else:
                self._subcribe_to_vp_and_inputs()

    @property
    def target_indicator_model(self):
        return self._target_indicator_model

    def _subcribe_to_vp_and_inputs(self):
        self._vp_view_change_sub = self._viewport_api.subscribe_to_view_change(self.on_view_changed)
        keyboard = omni.appwindow.get_default_app_window().get_keyboard()
        self._keyboard_sub = self._input.subscribe_to_keyboard_events(keyboard, self._on_keyboard_event)
        self._section_tool_sub = omni.kit.app.SettingChangeSubscription(
            SETTING_SECTION_ENABLED, lambda *_: self._on_section_tool_enabled()
        )

    def _on_stage_opening(self, *args, **kwargs):
        self._current_target_prim = None

    def _on_section_tool_enabled(self):
        # If section tool is enabled, invalidate the orbit target
        section_tool_enabled = self._settings.get_as_bool(SETTING_SECTION_ENABLED)
        if section_tool_enabled:
            self.target_valid = False
            self._target_indicator_model.visible = False

    def destroy(self):  # pragma: no cover
        self._current_target_prim = None
        self._stage_sub = None
        self._vp_view_change_sub = None
        self._section_tool_sub = None

        if self._keyboard_sub:
            keyboard = omni.appwindow.get_default_app_window().get_keyboard()
            self._input.unsubscribe_to_keyboard_events(keyboard, self._keyboard_sub)
            self._keyboard_sub = None

    def _change_camera_target(self, world_pos):
        # No world position: nothing hit
        if not world_pos:
            return
        # No camera: nothing to do
        cam_path = vp_util.get_viewport_window_camera_path()
        if not cam_path:
            return
        cam_state = VpCamera()
        # Get the current position and forward
        cam_pos = cam_state.position_world
        cam_target = cam_state.target_world
        cam_fwd = cam_target - cam_pos
        distance = Gf.Vec3d(cam_pos[0] - world_pos[0], cam_pos[1] - world_pos[1], cam_pos[2] - world_pos[2]).GetLength()
        # Set the target to pos + dir * d
        target = cam_pos + cam_fwd.GetNormalized() * distance
        # OM-103904: Set rotate flag to False when call set_target_world here,
        # otherwise it will change the camera's position in sometime
        cam_state.set_target_world(target, False)
        self._set_camera_focus_distance(cam_path, distance)
        asyncio.ensure_future(self._await_next_event(2))

    async def _await_next_event(self, n=4):
        while n > 0:
            await omni.kit.app.get_app().next_update_async()
            n = n - 1

    def _on_keyboard_event(self, event, *args, **kwargs):
        mouse = omni.appwindow.get_default_app_window().get_mouse()
        mouse_value = self._input.get_mouse_value(mouse, carb.input.MouseInput.RIGHT_BUTTON)

        if mouse_value:
            if (
                event.input == carb.input.KeyboardInput.A
                or event.input == carb.input.KeyboardInput.D
                or event.input == carb.input.KeyboardInput.Q
                or event.input == carb.input.KeyboardInput.E
            ) and (
                event.type == carb.input.KeyboardEventType.KEY_PRESS
                or event.type == carb.input.KeyboardEventType.KEY_REPEAT
            ):
                # If any of these keys are pressed, orbit target will become invalid
                self.target_valid = False

        return True

    def _get_default_focus_distance(self, stage):
        # Unit is in "cm", convert to stage unit
        default_distance = self._settings.get(DEFAULT_ORBIT_DISTANCE_SETTING_PATH)
        stage_unit = UsdGeom.GetStageMetersPerUnit(stage)
        converted_distance = (0.01 / stage_unit) * default_distance
        return converted_distance

    def _set_coi_and_focus_distance(self, active_camera_path: Sdf.Path, coi: Gf.Vec3d, focus_distance: float):
        coi_attr_path = active_camera_path.AppendProperty("omni:kit:centerOfInterest")
        omni.kit.commands.create(
            "ChangePropertyCommand",
            prop_path=coi_attr_path,
            value=coi,
            prev=Gf.Vec3d(0),  # doesn't matter since no undo
            usd_context_name=self._viewport_api.usd_context_name,
            type_to_create_if_not_exist=Sdf.ValueTypeNames.Vector3d,  # auto create if not already exist
        ).do()

        # even if maintain distance, this could be the first time target becomes valid, so set focus distance nonetheless
        focus_distance_path = active_camera_path.AppendProperty("focusDistance")
        omni.kit.commands.create(
            "ChangePropertyCommand",
            prop_path=focus_distance_path,
            value=focus_distance,
            prev=0,  # doesn't matter since no undo
            usd_context_name=self._viewport_api.usd_context_name,
            type_to_create_if_not_exist=Sdf.ValueTypeNames.Float,  # auto create if not already exist
        ).do()

    def _set_camera_focus_distance(self, camera_path, distance):
        stage = omni.usd.get_context().get_stage()
        with Usd.EditContext(stage):
            camera_prim = stage.GetPrimAtPath(camera_path)
            camera_prim.GetAttribute("focusDistance").Set(distance)

    def set_world_center(self):
        self.set_orbit_target(0, 0)

    def query(self, double_click, prim_path: str, pos: Optional[Gf.Vec3d], *args, **kwargs):
        """Handle the answer to the pick that ``set_orbit_target`` requested.

        ``prim_path`` is the picked prim path and ``pos`` its world-space hit position; an empty
        ``prim_path`` is a miss and leaves the orbit target unchanged.
        """
        if not prim_path:
            return

        viewport_api = vp_util.get_active_viewport()
        stage = None
        active_camera = vp_util.get_active_viewport_camera_path()
        if viewport_api:
            stage = viewport_api.stage
        if not stage:
            return
        cam_prim = stage.GetPrimAtPath(active_camera)
        if not cam_prim.IsValid():
            return

        if double_click:
            if pos:
                maintain_distance = self._settings.get(MAINTAIN_DISTANCE_SETTING_PATH)

                self._current_target_prim = prim_path
                vp_camera_state = VpCamera()
                prev_pos = vp_camera_state.position_world
                prev_target = vp_camera_state.target_world
                prev_dir = prev_target - prev_pos
                prev_target_dist = prev_dir.Normalize()

                t_pos = Gf.Vec3d(pos[0], pos[1], pos[2])
                self._target_indicator_model.display_position = t_pos
                self.target_valid = True
                self._target_indicator_model.visible = True

                self.handle_notification(False)

                new_dir = (t_pos - prev_pos).GetNormalized()
                if self._use_default_orbit_distance:
                    # Use default orbit distance when setting orbit target for the first time
                    default_distance = self._get_default_focus_distance(stage)

                    c_pos = t_pos - new_dir * default_distance
                    self._use_default_orbit_distance = False
                else:
                    if maintain_distance:
                        c_pos = t_pos - new_dir * prev_target_dist
                    else:
                        c_pos = prev_pos

                parent_xform = vp_camera_state.usd_camera.ComputeParentToWorldTransform(viewport_api.time)
                parent_xform_inv = parent_xform.GetInverse()

                cam_up = vp_camera_state.get_world_camera_up(cam_prim.GetStage())
                new_c_transform = Gf.Matrix4d(1).SetLookAt(c_pos, t_pos, cam_up).GetInverse()
                new_c_transform.SetTranslateOnly(c_pos)
                new_c_local_transform = new_c_transform * parent_xform_inv

                t_pos_local = (new_c_transform * parent_xform).GetInverse().Transform(t_pos)

                omni.kit.commands.create(
                    "TransformPrimCommand",
                    path=active_camera,
                    new_transform_matrix=new_c_local_transform,
                    old_transform_matrix=Gf.Matrix4d(1),  # doesn't matter since no undo
                    usd_context_name=viewport_api.usd_context_name,
                ).do()

                self._set_coi_and_focus_distance(active_camera, t_pos_local, (t_pos - c_pos).GetLength())
        else:
            # use the mesh's center point
            if not pos:
                return
            if self._current_target_prim == prim_path:
                return

            hit_prim = stage.GetPrimAtPath(prim_path)
            if hit_prim:
                self._current_target_prim = prim_path
                bboxcache = self._get_bboxcache()
                # OM-103230: Use ComputeWorldBound instead of  ComputeLocalBound to get the orbit target mesh's bound
                bound = bboxcache.ComputeWorldBound(hit_prim).ComputeAlignedRange()
                self._change_camera_target(bound.GetMidpoint())

    def set_orbit_target(self, mx, my, double_click=False):
        # Get center position
        if mx is None or my is None:
            return

        try:
            # Pick the surface under (mx, my) with the viewport's pick query. It answers on a later frame
            # through on_query_complete(path, world_pos); an empty path is a miss.
            pixel, in_viewport = self._viewport_api.map_ndc_to_texture_pixel((mx, my))
            if not in_viewport:
                # Outside the rendered image: answer like a pick that hit nothing.
                self.query(double_click, "", None)
                return

            def on_query_complete(path, world_pos, *args):
                prim_path = str(path) if path else ""
                pos = self._to_vec3d(world_pos) if prim_path else None
                if pos is None or self._is_sectioned_out(pos):
                    prim_path, pos = "", None
                self.query(double_click, prim_path, pos)

            self._viewport_api.request_query(
                pixel, on_query_complete, query_name="omni.kit.viewport.navigation.camera_manipulator.orbit_target"
            )

        except Exception as e:
            carb.log_error(e)

    @staticmethod
    def _to_vec3d(world_pos) -> Optional[Gf.Vec3d]:
        if world_pos is None:
            return None
        if hasattr(world_pos, "x"):
            return Gf.Vec3d(world_pos.x, world_pos.y, world_pos.z)
        return Gf.Vec3d(world_pos[0], world_pos[1], world_pos[2])

    def _is_sectioned_out(self, pos: Gf.Vec3d) -> bool:
        """
        Whether a picked world position lies in the region removed by the section plane, so a section
        never lets the orbit target land on geometry it hides.
        """
        if not self._settings.get_as_bool(SETTING_SECTION_ENABLED):
            return False
        # Note: section_plane = [normal.x, normal_y, normal.z, -dot(section_plane_center, normal)]
        section_plane = self._settings.get(SETTING_SECTION_PLANE)
        if not section_plane or len(section_plane) < 4:
            return False
        section_plane_4d = Gf.Vec4d(section_plane[0], section_plane[1], section_plane[2], section_plane[3])
        # Points with a negative signed distance are sectioned out; allow for hits on the cut itself.
        return Gf.Dot(Gf.Vec4d(pos[0], pos[1], pos[2], 1.0), section_plane_4d) < -1e-4

    def _get_bboxcache(self):
        if self._bboxcache is None:
            purposes = [UsdGeom.Tokens.default_]
            self._bboxcache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes)
        return self._bboxcache

    def handle_notification(self, show=True):
        if (self._target_notification is None or self._target_notification.dismissed) and show:
            try:
                import omni.kit.notification_manager as nm

                type = nm.NotificationStatus.WARNING

                self._target_notification = nm.post_notification(
                    "There is currently no Focus set to Orbit, please double click an object to set a focus.",
                    hide_after_timeout=False,
                    duration=0,
                    status=type,
                )
            except ModuleNotFoundError:
                pass

        elif (self._target_notification is not None and not self._target_notification.dismissed) and not show:
            self._target_notification.dismiss()

    def on_view_changed(self, vp_api):
        if self._target_valid:
            # Place the indicator in front of the camera, it will always appear at the center of the screen
            # Use viewport_api.transform instead of camera's xform attribute, because viewport_api value is slightly delayed
            # and viewport_api value is used in scene views, so jittering will happen if using actual camera's xform
            curr_cam_transform = self._viewport_api.transform
            cam_prim = self._viewport_api.stage.GetPrimAtPath(self._viewport_api.get_active_camera())

            coi_pos = None
            coi_attr = cam_prim.GetAttribute("omni:kit:centerOfInterest")
            if coi_attr:
                coi_pos = coi_attr.Get()
            if coi_pos is not None:
                if self._lock_target and self._target_indicator_model.display_position is not None:
                    # if target is locked, force updating camera's Center of Interest to match locked target
                    curr_target = self._target_indicator_model.display_position

                    view_mtx = self._viewport_api.view
                    curr_target_view = view_mtx.Transform(curr_target)
                    # Focus distance is expected to be negative value
                    focus_distance = min(0, curr_target_view[2])
                    new_coi = Gf.Vec3d(0, 0, focus_distance)

                    active_camera = vp_util.get_active_viewport_camera_path()
                    self._set_coi_and_focus_distance(active_camera, new_coi, abs(focus_distance))

                else:
                    self._target_indicator_model.display_position = curr_cam_transform.Transform(coi_pos)
            else:
                self.target_valid = False

    def validate_target_on_end(self):
        # Check if target is still valid on end of a drag gesture, e.g. NaviBarOrbitLookGesture
        curr_target = self._target_indicator_model.display_position
        if curr_target is not None:
            view_mtx = self._viewport_api.view
            curr_target_view = view_mtx.Transform(curr_target)
            # Z value of COI is expected to be negative value
            focus_distance = curr_target_view[2]

            if focus_distance >= 0:
                self.target_valid = False

    def set_default_focus_distance(self):
        # When there is no orbit target, force focus distance to 5M
        # This prevents unexpected behavior when orbiting camera with long focus distance and no orbit target
        stage = self._viewport_api.stage
        if not stage:
            return

        default_focus_distance = self._get_default_focus_distance(stage)
        default_coi = Gf.Vec3d(0, 0, -default_focus_distance)

        active_camera = vp_util.get_active_viewport_camera_path()
        self._set_coi_and_focus_distance(active_camera, default_coi, default_focus_distance)
