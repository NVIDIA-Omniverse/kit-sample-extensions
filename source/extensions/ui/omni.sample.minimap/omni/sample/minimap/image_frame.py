# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["ImageFrame"]

import asyncio

import carb.events
import carb.profiler
import omni.kit.app
from omni.ui import scene as sc

from .generator import MinimapGenerator, MinimapGeneratorEventTypes
from .window import MinimapWindow

USE_OPENGL = False


class ImageFrame:
    def __init__(self, generator: MinimapGenerator, window: MinimapWindow):
        """Initialize image frame with tile rendering."""
        self._provider = generator
        self._window = window
        self._frame = window.get_frame("minimap_image_frame")
        self._gen_evt_sub_id = generator.get_event_stream().create_subscription_to_pop(
            self._on_generate_event, name="ImageFrame"
        )
        self._window_evt_sub_id = None
        self._built_tiles = None
        self._async_tasks = []
        self._init_frame()

    def destroy(self):
        """Clean up image frame resources."""
        if hasattr(self, "_destroyed") and self._destroyed:
            return
        self._destroyed = True
        if hasattr(self, "_async_tasks"):
            for task in self._async_tasks:
                if not task.done():
                    task.cancel()
            self._async_tasks.clear()
        self._gen_evt_sub_id = None
        self._window_evt_sub_id = None
        self._provider = None
        self._window = None
        self._scene_view = None
        self._frame = None

    def _init_frame(self):
        """Initialize scene view for tile display."""
        if hasattr(self, "_frame") and self._frame:
            self._frame.clear()
        with self._frame:
            if USE_OPENGL:
                from omni.kit.scene_view.opengl import OpenGLSceneView

                self._scene_view = OpenGLSceneView()
            else:
                self._scene_view = sc.SceneView()
            self._window.add_scene_view(self._scene_view)
            with self._scene_view.scene:
                self._tile_transform = sc.Transform()
        self._update_tiles()

    def _on_generate_event(self, event: carb.events.IEvent):
        """Handle minimap generation events."""
        if event.type == int(MinimapGeneratorEventTypes.CLEAR):
            # Clear the frame without updating tiles (tiles are already cleared)
            if hasattr(self, "_tile_transform") and self._tile_transform:
                self._tile_transform.clear()
            self._built_tiles = None
            # Hide camera arcs when tiles are cleared
            if self._window:
                self._window._update_arc_visibility()
        if event.type == int(MinimapGeneratorEventTypes.UPDATE):
            if self._window:
                self._window._refresh_ui("tiles_update")

                camera_within_bounds = self._window.is_camera_within_bounds()

                if camera_within_bounds:
                    # Camera is within bounds
                    if self._window.rotate_actor:
                        # Locked mode: center viewport on camera if not visible (keeps zoom)
                        if not self._window.is_camera_visible_in_viewport():
                            self._window.center_viewport_on_camera()
                    # Unlocked mode: do nothing - camera stays exactly where it is
                else:
                    # Camera is outside bounds - adjust zoom to fit map
                    self._window.auto_fit_zoom()
                    # Only teleport camera in unlocked mode; in locked mode let user manually teleport
                    if not self._window.rotate_actor:
                        # Unlocked mode: teleport camera to center of bounds
                        self._window.check_and_center_camera()

                # Update camera arc visibility based on whether tiles exist
                self._window._update_arc_visibility()
            # Update tiles after handling camera adjustments (if any)
            self._update_tiles()

    @carb.profiler.profile
    def _update_tiles(self):
        """Update tile display based on current view."""
        if not hasattr(self, "_tile_transform") or not self._tile_transform:
            return

        view_center = self._window.get_minimap_view_center()
        tiles = self._provider.get_tiles(view_center)
        if self._built_tiles is tiles and tiles is not None:
            return
        self._tile_transform.clear()
        up_axis = self._provider.get_up_axis()
        if tiles:
            with self._tile_transform:
                vertex_indices = [0, 1, 2, 3]
                uvs = [[0.0, 1.0], [0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]
                colors = [[1, 1, 1, 1]] * 4
                for tile in tiles:
                    if not tile:
                        continue
                    if not hasattr(tile, "tile_width") or not hasattr(tile, "tile_height"):
                        continue
                    h_w = tile.tile_width * 0.5
                    h_h = tile.tile_height * 0.5
                    c_w = tile.tile_center[0]
                    c_h = tile.tile_center[1]
                    if up_axis == "Y":
                        points = [
                            (c_w - h_w, 0, c_h - h_h),
                            (c_w - h_w, 0, c_h + h_h),
                            (c_w + h_w, 0, c_h + h_h),
                            (c_w + h_w, 0, c_h - h_h),
                        ]
                    else:
                        points = [
                            (c_h - h_h, c_w - h_w, 0),
                            (c_h + h_h, c_w - h_w, 0),
                            (c_h + h_h, c_w + h_w, 0),
                            (c_h - h_h, c_w + h_w, 0),
                        ]
                    sc.TexturedMesh(
                        tile.image_provider, uvs, points, colors, [4], vertex_indices, legacy_flipped_v=False
                    )
        self._built_tiles = tiles
