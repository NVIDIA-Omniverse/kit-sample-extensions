# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TeleportScene"]
import asyncio
import weakref

import carb
import carb.events
import carb.settings
import omni.kit.app
from carb import eventdispatcher
from omni.kit.manipulator.camera import CameraGestureBase, LookGesture, ViewportCameraManipulator, ZoomGesture
from omni.ui import scene as sc

from .cursor import CursorLookGesture, reset_cursor  # , TeleportCursor
from .scene_camera import CameraModel
from .teleport import TELE_ENABLED_GLOBAL_EVENT, TELE_SIMPLE_CAMERA, Teleport
from .teleport_manipulator import TeleportManipulator

GIZMO_VIS_CHANGED_EVT = "teleport.tool.gizmo_vis.CHANGED"

GIZMO_VIS_EVT_PAYLOAD_KEY = "visibility"
SETTING_SECTION_ENABLED = "/rtx/sectionPlane/enabled"
SETTING_SECTION_PLANE = "/rtx/sectionPlane/plane"


class _SurfaceHit:
    """A viewport pick hit with the fields the teleport reads: valid, hit_position, normal and the target path."""

    def __init__(self, path: str = "", hit_position=(0.0, 0.0, 0.0), normal=None):
        self.valid = bool(path)
        self.hit_position = hit_position
        self.normal = normal
        self._path = path

    def get_target_usd_path(self) -> str:
        return self._path


def _request_surface_hit(viewport_api, ndc, query, query_name: str) -> None:
    """Find the surface under *ndc* with the viewport pick query and call ``query(None, _SurfaceHit)``.

    ``request_query`` returns the hit prim, its world position and, when the viewport provides it, the surface normal.
    """
    pixel, in_viewport = viewport_api.map_ndc_to_texture_pixel(ndc)
    if not in_viewport:
        query(None, _SurfaceHit())
        return

    def on_query_complete(path, world_pos, *args):
        # With include_normal=True the callback receives (path, world_pos, pixel, normal or None).
        normal = args[1] if len(args) > 1 else None
        if not path or world_pos is None:
            query(None, _SurfaceHit())
            return
        query(None, _SurfaceHit(str(path), (world_pos[0], world_pos[1], world_pos[2]), normal))

    try:
        viewport_api.request_query(pixel, on_query_complete, query_name=query_name, include_normal=True)
    except TypeError:
        # A viewport whose pick query has no include_normal option: positions only.
        viewport_api.request_query(pixel, on_query_complete, query_name=query_name)


class PreventOthers(sc.GestureManager):
    """
    Hide other gestures
    """

    def __init__(self):
        self._teleport = Teleport.get_instance()
        self._model = self._teleport.get_model()
        self._settings = carb.settings.get_settings()
        super().__init__()

    def __del__(self):
        self._teleport = None
        self._model = None

    def can_be_prevented(self, gesture):
        return not self._teleport.get_active()

    def should_prevent(self, gesture, preventer):
        if preventer.state == sc.GestureState.BEGAN or preventer.state == sc.GestureState.CHANGED:
            if self._settings.get_as_bool(TELE_SIMPLE_CAMERA):
                # For simple camera mode, only zoom is allowed
                if isinstance(gesture, ZoomGesture):
                    return False
            else:
                # For non-simple camera mode, all default camera gestures are allowed
                if isinstance(gesture, CameraGestureBase):
                    return False

            return True


class TeleportCameraManipulator(ViewportCameraManipulator):
    def __init__(self, enabled=False, *args, **kwargs):
        self._enabled = enabled
        super().__init__(*args, **kwargs)
        self._gestures = []
        self.__transform = None
        self._screen = None

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if value != self._enabled:
            self._enabled = value

            if self._screen is not None:
                self._screen.visible = self._enabled
            else:
                self.invalidate()

    def on_build(self):
        if not self._enabled:
            return

        self.__transform = sc.Transform()
        with self.__transform:
            self._screen = sc.Screen(gestures=self._gestures)

    def assign_gestures(self, gestures):
        self._gestures = gestures

    def destroy(self):
        if self.__transform:
            self.__transform.clear()
            self.__transform = None

        if self._screen:
            self._screen.visible = False
            self._screen = None

        super().destroy()


class TeleportScene:
    """The window with the manupulator"""

    def __init__(self, vp_args: dict):
        self._settings = carb.settings.get_settings()
        self._vp_api = vp_args["viewport_api"]
        self._manipulater = None
        self._teleport = Teleport.get_instance()
        self._model = self._teleport.get_model()
        # self._cursor = TeleportCursor()
        prevent_others = PreventOthers()
        move_gesture = sc.HoverGesture(
            name="teleport_move", on_changed_fn=lambda sender: self._on_moved(sender), manager=prevent_others
        )
        click_gesture = sc.ClickGesture(
            name="teleport_click",
            on_ended_fn=lambda sender: self._on_clicked(sender),
            manager=prevent_others,
        )

        # OM-99523 - Support "Google Maps" style mouse-look
        # widget_drag_gesture = sc.DragGesture(
        #     name="teleport_widget_drag",
        #     on_began_fn=self._hide_widget,
        #     on_ended_fn=self._show_widget,
        #     manager=prevent_others,
        # )

        widget_drag_gesture_lmb = sc.DragGesture(
            name="teleport_widget_drag_lmb", on_ended_fn=self._show_gizmo, manager=prevent_others, mouse_button=0
        )

        widget_drag_gesture_mmb = sc.DragGesture(
            name="teleport_widget_drag_mmb", on_ended_fn=self._show_gizmo, manager=prevent_others, mouse_button=2
        )

        widget_drag_gesture_rmb = sc.DragGesture(
            name="teleport_widget_drag_rmb", on_ended_fn=self._show_gizmo, manager=prevent_others, mouse_button=1
        )

        self._camera_manipulator = TeleportCameraManipulator(enabled=False, viewport_api=self._vp_api)

        teleport_look_gesture = CursorLookGesture(
            self._camera_manipulator.model,
            self._camera_manipulator._on_began,
            "TeleportLookGesture",
            mouse_button=0,
            modifiers=0 | 0xFFFFFFFF,
            manager=prevent_others,
        )

        # self._camera_manipulator.assign_gestures([teleport_look_gesture, move_gesture, click_gesture, widget_drag_gesture])
        self._camera_manipulator.assign_gestures(
            [
                teleport_look_gesture,
                move_gesture,
                click_gesture,
                widget_drag_gesture_lmb,
                widget_drag_gesture_mmb,
                widget_drag_gesture_rmb,
            ]
        )
        # Flip the speeds to invert the camera dragging.
        look_speed = self._camera_manipulator.model.get_item("look_speed")
        vals = self._camera_manipulator.model.get_as_floats(look_speed)
        self._camera_manipulator.model.set_floats(look_speed, [-v for v in vals])

        def on_speed_changed(*args, _self=weakref.ref(self)):
            self = _self()
            if self and self._camera_manipulator:
                look_speed = self._camera_manipulator.model.get_item("look_speed")
                vals: list[float] = self._settings.get("/persistent/exts/omni.kit.manipulator.camera/lookSpeed")  # type: ignore
                if vals:
                    self._camera_manipulator.model.set_floats(
                        look_speed, [-v / 180 if v > 0 else v / 180 for v in vals]
                    )

        self._speed_changed = self._settings.subscribe_to_tree_change_events(
            "/persistent/exts/omni.kit.manipulator.camera/lookSpeed", on_speed_changed
        )

        self._manipulater = TeleportManipulator(model=self._model)

        self._camera_manipulator.manager = prevent_others
        self._teleport_enabled_sub = eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.tool.teleport.TeleportScene",
            event_name=TELE_ENABLED_GLOBAL_EVENT,
            on_event=self._on_teleport_tool_enabled,
        )

        self._coords = None
        self._mouse = None

    def _hide_widget(self, *args) -> None:  # pragma: no cover -- currently unused
        if self._teleport.get_active():
            # OM-99523 - Hide widget on 'Google Maps' style look event.
            payload = {GIZMO_VIS_EVT_PAYLOAD_KEY: False}
            omni.kit.app.queue_event(GIZMO_VIS_CHANGED_EVT, payload)

    def _show_widget(self, *args) -> None:  # pragma: no cover -- currently unused
        if self._teleport.get_active():
            # OM-99523 - Show widget after 'Google Maps' style look event.
            payload = {GIZMO_VIS_EVT_PAYLOAD_KEY: True}
            omni.kit.app.queue_event(GIZMO_VIS_CHANGED_EVT, payload)

    def _show_gizmo(self, *args):
        if self._teleport.get_active():
            self._model.visible = True

    def _move(self, coords, mouse):
        @carb.profiler.profile
        def query(ray, result, *args, **kwargs):

            # we don't need skip none path here, for we also want to teleport on the grid ground
            prim_path = result.get_target_usd_path() if result.valid else ""
            if prim_path.startswith("/Teleport"):
                return
            if self._teleport.get_active():
                self._teleport.on_moved(mouse, result)

        try:
            _request_surface_hit(self._vp_api, mouse, query, "teleport_move")
        except Exception as e:
            carb.log_error(e)

    def _on_moved(self, sender):
        if self._teleport.get_active():
            self.visible = True
            coords, valid = self._vp_api.map_ndc_to_texture(sender.gesture_payload.mouse)
            if valid:
                mouse = sender.gesture_payload.mouse
                self._move(coords, mouse)
                # self._cursor.show_teleport_cursor(True)
            else:
                self._model.visible = False
                # self._cursor.show_teleport_cursor(False)
                pass

    def _on_clicked(self, sender):
        def query(ray, result, *args, **kwargs):
            if self._teleport.get_active():
                self._teleport.on_clicked(self._mouse, result)

                # force a move event so after camera moves, the teleport gizmo shows up at correct location again
                # It has to happen AFTER viewport's view and projection matrix has updated
                future = asyncio.Future()

                def view_changed(*args, **kwargs):
                    # Must discard the first callback since subscribe_to_view_change calls back immediately
                    nonlocal scoped_sub, counter
                    counter += 1
                    if counter == 2 and not future.done():
                        future.set_result(True)
                        scoped_sub = None

                counter = 0
                scoped_sub = self._vp_api.subscribe_to_view_change(view_changed)

                async def __delayed_move_after_click(future: asyncio.Future):
                    await future
                    await omni.kit.app.get_app().next_update_async()
                    self._move(self._coords, self._mouse)

                asyncio.ensure_future(__delayed_move_after_click(future))

        if self._teleport.get_active():
            self.visible = True
            self._coords = self._vp_api.map_ndc_to_texture_pixel(sender.gesture_payload.mouse)[0]
            self._mouse = sender.gesture_payload.mouse
            if self._coords:
                try:
                    _request_surface_hit(self._vp_api, sender.gesture_payload.mouse, query, "teleport_click")
                except:
                    pass
                # OM-95873: Force eye height lock after teleport jump.
                carb.settings.get_settings().set("/persistent/exts/omni.kit.manipulator.camera/flyViewLock", True)

    def _on_drag(self, sender):  # pragma: no cover -- currently unused
        def query(ray, result, *args, **kwargs):
            # if prim_path.startswith("/Teleport"):
            #    return
            if self._teleport.get_active():
                self._teleport.on_drag(result)

        if self._teleport.get_active():
            self.visible = True
            coords = self._vp_api.map_ndc_to_texture_pixel(sender.gesture_payload.mouse)[0]
            if coords and coords[0] > 0 and coords[1] > 0:
                try:
                    _request_surface_hit(self._vp_api, sender.gesture_payload.mouse, query, "teleport_drag")
                except:
                    pass

    def _end_drag(self, sender):  # pragma: no cover -- currently unused
        def query(ray, result, *args, **kwargs):
            # if prim_path.startswith("/Teleport"):
            #    return
            if self._teleport.get_active():
                self._teleport.end_drag(result)

        if self._teleport.get_active():
            self.visible = True
            coords = self._vp_api.map_ndc_to_texture_pixel(sender.gesture_payload.mouse)[0]
            if coords and coords[0] > 0 and coords[1] > 0:
                try:
                    _request_surface_hit(self._vp_api, sender.gesture_payload.mouse, query, "teleport_end_drag")
                except:
                    pass

    def _on_teleport_tool_enabled(self, event):
        enabled = event["enabled"]
        if enabled:
            self._camera_manipulator.enabled = True
            # don't need it if using TeleportCursor
            reset_cursor()
        else:
            self._camera_manipulator.enabled = False

    def destroy(self):
        self.clear()

        if self._manipulater is not None:
            self._manipulater.clear()
            self._manipulater = None
        self._teleport = None
        if self._camera_manipulator is not None:
            self._camera_manipulator.destroy()
            self._camera_manipulator = None

        self._teleport_enabled_sub = None
        # self._cursor = None

    def __del__(self):
        self.destroy()

    def clear(self):
        if self._manipulater:
            self._manipulater.clear()
        if self._camera_manipulator:
            self._camera_manipulator.clear()

    def __build_scene(self):  # pragma: no cover -- currently unused
        """Called to build the widgets of the window"""
        # PRESERVE_ASPECT_HORIZONTAL and 1280 / 720 are defaults for the Kit
        # viewport
        self._scene_view = None
        self._manipulater = None
        self._scene_view = sc.SceneView(
            model=CameraModel(),
            aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_HORIZONTAL,
            screen_aspect_ratio=1280 / 720,
        )

        with self._scene_view.scene:
            self._manipulater = TeleportManipulator(model=self._model)

    @property
    def visible(self):
        return self._camera_manipulator.visible

    @visible.setter
    def visible(self, value: bool):
        value = bool(value)
        # self._model.beam_visible = value
        self._camera_manipulator.visible = value
