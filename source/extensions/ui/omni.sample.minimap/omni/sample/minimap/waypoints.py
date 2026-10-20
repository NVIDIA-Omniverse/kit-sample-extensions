# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["WaypointsLayer", "close_markup_if_active", "get_waypoints_layer"]

import logging
import time

import carb
import carb.eventdispatcher
import carb.settings
import omni.kit.app
import omni.usd
from omni.kit.prim.icon import IconScene
from omni.ui import scene as sc

from .settings import S_PATH
from .window import MINIMAP_UI_EVENT, get_window_instance

logger = logging.getLogger(__name__)

WAYPOINT_LIST_WINDOW_VISIBLE = "/exts/omni.kit.viewport.menubar.waypoint/list_window_visible"
MARKUP_LIST_WINDOW_VISIBLE = "/exts/omni.kit.viewport.menubar.markup/list_window_visible"
SETTINGS_WAYPOINT_ACTIVE = "/exts/omni.kit.waypoint.core/active_waypoint"

# Global singleton reference
g_waypoints_layer = None


def get_waypoints_layer():
    """Get the global WaypointsLayer instance."""
    return g_waypoints_layer


def close_markup_if_active():
    """Closes markup mode if currently active."""
    try:
        import omni.kit.markup.core.extension as markup_extension

        markup_ext_instance = markup_extension.get_instance()
        if markup_ext_instance and markup_ext_instance.current_markup:
            markup_ext_instance.editing_markup = None
            markup_ext_instance.current_markup = None
    except Exception:
        # this is expected to fail if not using usd_explorer
        pass


class WaypointsLayer:
    def __init__(self):
        """Initialize waypoints and markup icon layer."""
        global g_waypoints_layer
        g_waypoints_layer = self

        self._icon_scene = None
        self._scene_view = None
        self._gen_window = None
        self._settings = carb.settings.get_settings()
        self._last_waypoint_visible = None
        self._last_markup_visible = None
        self._last_update_time = 0
        self._update_sub = None
        self._waypoint_active_sub = None
        self._event_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=MINIMAP_UI_EVENT,
            on_event=self.handle_event,
            observer_name="omni.sample.minimap.waypoints.ui_event",
        )

        # Subscribe to active_waypoint setting changes
        if self._settings:
            self._waypoint_active_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_waypoint_active_changed,
                observer_name="omni.sample.minimap.waypoints.waypoint_active_monitor",
            )

    def handle_event(self, e: carb.eventdispatcher.Event):
        """Handle UI ready event for minimap initialization and rebuilds."""
        if e.payload.get("ui_ready", False):
            self._gen_window = get_window_instance()
            if not self._gen_window:
                return

            if self._scene_view:
                self._scene_view = None
                self._icon_scene = None

            self._frame = self._gen_window.get_frame("point_icon_frame")
            if self._frame:
                self._init_frame()
                if not self._update_sub:
                    self._setup_update_loop()

    def _setup_update_loop(self):
        """Setup periodic visibility monitoring."""
        self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=self._on_update,
            observer_name="omni.sample.minimap.waypoints.visibility_monitor",
        )

    def _on_update(self, e):
        """Monitor waypoint/markup window visibility."""
        if not self._settings:
            return
        current_time = time.time()
        # Get waypoint throttle from settings (default to 0.2 seconds if not set)
        waypoint_throttle = self._settings.get(S_PATH.WAYPOINT_THROTTLE) or 0.2
        if current_time - self._last_update_time < waypoint_throttle:
            return
        self._last_update_time = current_time
        waypoint_visible = self._settings.get(WAYPOINT_LIST_WINDOW_VISIBLE) is True
        markup_visible = self._settings.get(MARKUP_LIST_WINDOW_VISIBLE) is True
        if waypoint_visible != self._last_waypoint_visible:
            self._last_waypoint_visible = waypoint_visible
            self._update_icons()
        if markup_visible != self._last_markup_visible:
            self._last_markup_visible = markup_visible
            self._update_icons()

    def _update_icons(self):
        """Refresh icon display by invalidating scene view and window."""
        if self._scene_view and hasattr(self._scene_view, "invalidate_raster"):
            self._scene_view.invalidate_raster()
        if self._gen_window:
            self._gen_window._refresh_ui("waypoints_update")

    def _init_frame(self):
        """Initialize icon scene view with minimap's transformation model."""
        model = self._gen_window._simple_model if hasattr(self._gen_window, "_simple_model") else None

        with self._frame:
            self._scene_view = sc.SceneView(model)
        self._gen_window.add_scene_view(self._scene_view)

        with self._scene_view.scene:
            usd_context = omni.usd.get_context()
            self._icon_scene = IconScene(icon_scale=2, usd_context_name=usd_context.get_name())

        if self._settings:
            self._last_waypoint_visible = self._settings.get(WAYPOINT_LIST_WINDOW_VISIBLE) is True
            self._last_markup_visible = self._settings.get(MARKUP_LIST_WINDOW_VISIBLE) is True
            self._last_active_waypoint = self._settings.get(SETTINGS_WAYPOINT_ACTIVE)

    def set_icons_visible(self, visible: bool) -> None:
        if self._icon_scene:
            self._icon_scene.visible = visible

    def _reset_camera_center(self):
        """Reset minimap view center to current camera position to resync IconScene."""
        try:
            from omni.kit.viewport.utility import get_active_viewport
            from pxr import Gf, Usd, UsdGeom

            viewport_api = get_active_viewport()
            if not viewport_api:
                return

            stage = omni.usd.get_context().get_stage()
            if not stage:
                return

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
            cam_pos = world_mtx.ExtractTranslation()

            up_axis = UsdGeom.GetStageUpAxis(stage)
            up_index = 1 if up_axis == UsdGeom.Tokens.y else 2

            if self._gen_window and hasattr(self._gen_window, "_minimap_view_center"):
                self._gen_window._minimap_view_center = Gf.Vec3d(cam_pos)
                self._gen_window._minimap_view_center[up_index] = 5000
        except Exception as e:
            logger.warning(f"Error resetting camera center: {e}")

    def _on_waypoint_active_changed(self, e):
        """Monitor active_waypoint setting changes to handle waypoint/markup interactions."""
        try:
            if not self._settings:
                return

            current_active = self._settings.get(SETTINGS_WAYPOINT_ACTIVE)

            if not hasattr(self, "_last_active_waypoint"):
                self._last_active_waypoint = current_active
                return

            if current_active != self._last_active_waypoint:
                if current_active and current_active.strip():
                    close_markup_if_active()
                elif not current_active and self._last_active_waypoint:
                    self._settings.set(MARKUP_LIST_WINDOW_VISIBLE, True)
                    if self._gen_window and not self._gen_window.rotate_actor:
                        self._reset_camera_center()
                    self._update_icons()

                self._last_active_waypoint = current_active
        except Exception as e:
            logger.warning(f"Error monitoring active_waypoint: {e}")

    def destroy(self):
        """Clean up resources."""
        global g_waypoints_layer
        g_waypoints_layer = None

        self._update_sub = None
        self._event_sub = None
        self._waypoint_active_sub = None
        self._settings = None
        self._gen_window = None

        if self._icon_scene:
            try:
                self._icon_scene.destroy()
            except Exception as e:
                logger.warning(f"Error destroying icon scene: {e}")

        self._icon_scene = None
        self._scene_view = None
