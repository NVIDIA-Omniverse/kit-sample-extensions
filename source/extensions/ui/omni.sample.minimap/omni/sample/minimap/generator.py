# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Minimap Generator for Omniverse Kit.

This module provides functionality for generating and managing minimaps in Omniverse applications.
Supports:
- Automatic minimap generation from stage geometry
- Custom floor/ceiling bounds definition
- Tile-based rendering with configurable resolution
- Real-time navigation and orientation tracking
"""

__all__ = [
    "MinimapGeneratorEventTypes",
    "MapTile",
    "MapTileSaved",
    "MapTileGroup",
    "CaptureJobDesc",
    "MinimapGenerator",
]

import asyncio
import base64
import ctypes
import gc
import io
import logging
import math
import pickle
import secrets
import sys
import time
from dataclasses import asdict, dataclass
from enum import IntEnum, auto
from typing import Sequence, Union

import carb.eventdispatcher
import carb.events
import carb.profiler
import carb.settings
import omni.kit.app
import omni.ui as ui
import omni.usd
import warp as wp
from omni.kit.viewport.utility import capture_viewport_to_buffer, create_viewport_window
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom

from . import settings
from .settings import DUMP_GPU, GPU_CLEANUP_INTERVAL, MULTI_LEVEL_SUPPORT, R_GRID, R_SHADOWS, S_PATH

# Version number for the minimap data format
DATA_VERSION = 2
IS_LINUX = sys.platform.startswith("linux")
GPU_TEXTURE = False  # GPU texture storage (disabled for compatibility)
USE_MT = True  # Enable multi-threading support

logger = logging.getLogger(__name__)


def _cleanup_gpu_resources(tiles: list = None, force_gc: bool = True, sync_cuda: bool = True):
    """
    Clean up GPU resources and synchronize CUDA operations.

    Args:
        tiles: List of tiles to clean up
        force_gc: Whether to force garbage collection
        sync_cuda: Whether to synchronize CUDA operations
    """
    try:
        if tiles:
            for tile in tiles:
                if hasattr(tile, "cleanup"):
                    tile.cleanup()
        if sync_cuda and GPU_TEXTURE:
            wp.synchronize()
        if force_gc:
            gc.collect()
    except Exception as e:
        if settings.DEV_MODE:
            logger.warning(f"DEV: Error during GPU cleanup: {e}")


def _gpu_cleanup_sync(aggressive: bool = None):
    """
    Perform GPU cleanup with platform-specific behavior.

    Args:
        aggressive: If None, uses platform default (aggressive on Linux). If True, performs
                   multiple synchronization passes and cache clearing.
    """
    use_aggressive = IS_LINUX if aggressive is None else aggressive
    if use_aggressive:
        wp.synchronize()
        gc.collect()
        wp.synchronize()
        gc.collect()
        try:
            cuda_device = wp.get_device("cuda")
            if cuda_device and hasattr(cuda_device, "context"):
                cuda_device.context.synchronize()
                if hasattr(cuda_device, "clear_cache"):
                    cuda_device.clear_cache()
        except Exception as e:
            if settings.DEV_MODE:
                logger.warning(f"DEV: Error during CUDA cleanup: {e}")
        gc.collect()
    else:
        wp.synchronize()
        gc.collect()


def _get_axis_indices(up_axis):
    """
    Get axis indices and camera rotation based on stage up axis.

    Args:
        up_axis: The up axis token (Y or Z)

    Returns:
        tuple: (h_axis, v_axis, d_axis, cam_rot_axis, cam_rot_degrees)
    """
    return (0, 2, 1, 0, -90) if up_axis == UsdGeom.Tokens.y else (1, 0, 2, 2, 90)


# Stage metadata keys for storing minimap data
CDATA_KEY = "customLayerData"
ROOT_KEY = "omni_minimap"
VERSION_KEY = "omni_minimap:version"
UP_AXIS_KEY = "omni_minimap:up_axis"
GROUP_KEY = "omni_minimap:groups"
FLOOR_KEY = "omni_minimap:floor"
CEIL_KEY = "omni_minimap:ceil"
BOUNDS_KEY = "omni_minimap:bounds"
NUM_TILES_KEY = "omni_minimap:num_tiles"
TILE_SIZE_KEY = "omni_minimap:tile_size"
RESOLUTION_KEY = "omni_minimap:resolution"
BOUND_PRIMS_KEY = "omni_minimap:bound_prims"
CAM_SIZE_KEY = "omni_minimap:cam_size"

if USE_MT:
    import concurrent.futures


class MinimapGeneratorEventTypes(IntEnum):
    """Event types for minimap updates."""

    UPDATE = auto()  # Dispatched when tiles are updated
    CLEAR = auto()  # Dispatched when tiles are cleared


class MapTile:
    """A single minimap tile with system memory storage after GPU generation."""

    __slots__ = (
        "tile_width",
        "tile_height",
        "tile_center",
        "image_data",
        "image_width",
        "image_height",
        "image_provider",
        "_cleaned",
        "_system_data",
    )

    def __init__(self):
        """Initialize tile storage."""
        self._cleaned = False
        self._system_data = None

    def transfer_to_system_memory(self):
        """Transfer GPU data to system memory and clean up GPU resources."""
        if hasattr(self, "image_data") and self.image_data is not None:
            try:
                wp.synchronize()
                self._system_data = self.image_data.numpy().copy()
                del self.image_data
                self.image_data = None
                gc.collect()
                if hasattr(self, "image_provider") and self.image_provider:
                    self.image_provider.set_bytes_data(
                        self._system_data.tobytes(), [self.image_width, self.image_height]
                    )
            except Exception as e:
                if settings.DEV_MODE:
                    logger.warning(f"DEV: Error transferring tile to system memory: {e}")

    def cleanup(self):
        """Clean up all resources held by this tile."""
        if self._cleaned:
            return
        try:
            if hasattr(self, "image_provider"):
                self.image_provider = None
            if hasattr(self, "image_data"):
                del self.image_data
                self.image_data = None
            if hasattr(self, "_system_data"):
                self._system_data = None
            self._cleaned = True
        except Exception as e:
            if settings.DEV_MODE:
                logger.warning(f"DEV: Error during tile cleanup: {e}")

    @carb.profiler.profile
    @staticmethod
    def from_saved(saved_tile: "MapTileSaved") -> "MapTile":
        """
        Create a MapTile instance from saved tile data.

        Args:
            saved_tile: The saved tile data to restore from

        Returns:
            MapTile: A new MapTile instance with the restored data
        """
        tile = MapTile()
        tile.tile_width = saved_tile.tile_width
        tile.tile_height = saved_tile.tile_height
        tile.tile_center = saved_tile.tile_center
        image = Image.open(io.BytesIO(saved_tile.image_data))
        tile.image_width = image.width
        tile.image_height = image.height
        tile._system_data = bytearray(image.tobytes())
        tile.image_provider = ui.ByteImageProvider()
        tile.image_provider.set_bytes_data(tile._system_data, [tile.image_width, tile.image_height])
        return tile


@dataclass
class MapTileSaved:
    """
    Serializable version of MapTile for saving to disk.

    Stores the same geometric data as MapTile but with image data as bytes
    rather than GPU arrays.

    Attributes:
        tile_width: Width of the tile in stage units
        tile_height: Height of the tile in stage units
        tile_center: Center position of the tile in stage space
        image_data: PNG-encoded image data
    """

    tile_width: int
    tile_height: int
    tile_center: Sequence[float]
    image_data: bytes

    @carb.profiler.profile
    @staticmethod
    def from_tile(tile: MapTile) -> "MapTileSaved":
        """
        Create a serializable MapTileSaved instance from a MapTile.

        Converts the system memory image data to PNG-encoded bytes for serialization.

        Args:
            tile: The tile to save

        Returns:
            MapTileSaved: A new serializable instance with the tile's data
        """
        if hasattr(tile, "_system_data") and tile._system_data is not None:
            image_data_source = tile._system_data
        elif hasattr(tile, "image_data") and tile.image_data is not None:
            image_data_source = tile.image_data.numpy()
        else:
            raise ValueError("No image data available in tile")
        image = Image.frombytes("RGBA", (tile.image_width, tile.image_height), image_data_source)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_data = image_bytes.getvalue()
        image_bytes.close()
        return MapTileSaved(tile.tile_width, tile.tile_height, tile.tile_center, image_data)


@dataclass(init=False)
class MapTileGroup:
    """
    A group of map tiles that share a common bounding box.

    Used to organize tiles by spatial location for efficient rendering and memory management.
    """

    def __init__(self, bbox: Gf.BBox3d, tiles: list[MapTile] = None):
        """
        Initialize tile group with bounding box.

        Args:
            bbox: The bounding box that defines when this group should be displayed
            tiles: Optional list of tiles belonging to this group
        """
        self._bbox = bbox
        self._tiles = tiles if tiles else []

    @property
    def tiles(self) -> list[MapTile]:
        """Get tiles in this group."""
        return self._tiles

    @property
    def bbox(self) -> Gf.BBox3d:
        """Get bounding box for this group."""
        return self._bbox

    def intersects(self, pos: Gf.Vec3d) -> bool:
        """
        Check if a position intersects this group's bounding box.

        Args:
            pos: Position to check

        Returns:
            bool: True if position is within bounds
        """
        if self._bbox.GetRange().IsEmpty():
            return True
        inv_mtx = self._bbox.GetInverseMatrix()
        pos = inv_mtx.Transform(pos)
        if not MULTI_LEVEL_SUPPORT:
            from omni.usd import get_context
            from pxr import UsdGeom

            stage = get_context().get_stage()
            if stage:
                up_axis = UsdGeom.GetStageUpAxis(stage)
                up_axis_idx = 1 if up_axis == UsdGeom.Tokens.y else 2
                bbox_range = self._bbox.GetRange()
                bbox_min, bbox_max = bbox_range.GetMin(), bbox_range.GetMax()
                for i in range(3):
                    if i == up_axis_idx:
                        continue
                    if not (bbox_min[i] <= pos[i] <= bbox_max[i]):
                        return False
                return True
        return self._bbox.GetRange().Contains(pos)


@dataclass
class CaptureJobDesc:
    """
    Description of a minimap capture job.

    Contains all the parameters needed to capture a single tile, including camera
    positioning, bounds, and rendering settings.
    """

    h_min: float  # Horizontal minimum bound
    h_max: float  # Horizontal maximum bound
    v_min: float  # Vertical minimum bound
    v_max: float  # Vertical maximum bound
    h_axis_idx: int  # Horizontal axis index (0=X, 1=Y, 2=Z)
    v_axis_idx: int  # Vertical axis index
    d_axis_idx: int  # Depth axis index
    cam_rot_axis: int  # Camera rotation axis
    cam_rot: float  # Camera rotation in degrees
    job_limit: int  # Maximum number of concurrent jobs
    capture_height_min_meters: float  # Minimum capture height
    capture_height_max_meters: float  # Maximum capture height
    mpu: float  # Meters per unit (stage unit to meters conversion)
    tile_size: float  # Size of each tile in meters
    index: int  # Job index for tracking


class MinimapGenerator:
    """
    Main class for generating and managing minimaps.

    Handles tile generation, caching, serialization, and UI updates. Generates top-down
    orthographic views of the scene broken into tiles for efficient rendering.
    """

    def __init__(self, usd_context_name: str = "", window: ui.Window = None):
        """
        Initialize minimap generator.

        Args:
            usd_context_name: Name of the USD context to use (empty for default)
            window: UI window reference for updates
        """
        self._app = omni.kit.app.get_app()
        self._window = window
        self._settings = carb.settings.get_settings()
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._stage: Usd.Stage = None
        self._map_tile_groups: list[MapTileGroup] = []
        self._map_tiles_up_axis: str = None
        self._menu_group = None
        self._event_stream = carb.events.get_events_interface().create_event_stream()
        self._task: asyncio.Task = None
        self._stage_init_task: asyncio.Task = None  # Track stage initialization task
        self._floor = self._ceiling = self._tile_size = self._resolution = self._range = None
        self._bounds_top = self._bounds_bottom = None
        self._async_tasks = []
        self._tile_counter = 0  # Track tiles for GPU cleanup interval
        if USE_MT:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=None)
        self._stage_sub = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.sample.minimap.MinimapGenerator",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in [
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closing()),
                (omni.usd.StageEventType.CLOSED, lambda _: self._on_stage_closed()),
            ]
        ]
        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

    async def _restore_camera(self, original_camera_path, original_camera_transform, original_camera_fov):
        """Restore original camera after minimap generation."""
        if not (original_camera_path and self._stage):
            return

        try:
            from omni.kit.viewport.utility import get_active_viewport

            viewport_api = get_active_viewport()
            if not viewport_api:
                return

            # Switch camera if needed
            if viewport_api.get_active_camera() != original_camera_path:
                viewport_api.set_active_camera(original_camera_path)
                await self._app.next_update_async()

            if not self._stage:  # Re-validate after await
                return

            # Restore transform and FOV if changed
            if (
                original_camera_transform
                and (prim := self._stage.GetPrimAtPath(original_camera_path))
                and prim.IsValid()
            ):
                if xform_api := UsdGeom.XformCommonAPI(prim):
                    translation, rotation, scale, pivot, rot_order = xform_api.GetXformVectors(Usd.TimeCode.Default())
                    orig_trans, orig_rot, orig_scale, orig_pivot, orig_rot_order = original_camera_transform

                    pos_diff = (translation - orig_trans).GetLength() if translation and orig_trans else 0
                    rot_diff = (rotation - orig_rot).GetLength() if rotation and orig_rot else 0

                    if pos_diff > 0.001 or rot_diff > 0.001:
                        xform_api.SetXformVectors(
                            orig_trans, orig_rot, orig_scale, orig_pivot, orig_rot_order, Usd.TimeCode.Default()
                        )
                        await self._app.next_update_async()

                if original_camera_fov and (camera := UsdGeom.Camera(prim)):
                    if abs(camera.GetHorizontalApertureAttr().Get() - original_camera_fov) > 0.001:
                        camera.GetHorizontalApertureAttr().Set(original_camera_fov)
        except Exception:
            pass

    def destroy(self):
        """Clean up generator resources."""
        if hasattr(self, "_destroyed") and self._destroyed:
            return
        self._destroyed = True

        # Cancel stage init task first
        if hasattr(self, "_stage_init_task") and self._stage_init_task and not self._stage_init_task.done():
            self._stage_init_task.cancel()
            self._stage_init_task = None

        # Cancel all async tasks
        if hasattr(self, "_async_tasks"):
            for task in self._async_tasks:
                if not task.done():
                    task.cancel()
            self._async_tasks.clear()

        # Cancel main task
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
        if hasattr(self, "_cleanup_tiles"):
            self._cleanup_tiles()
        for _ in range(5):
            _gpu_cleanup_sync()
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

        # Clean up subscriptions
        self._stage_sub = None

        # Clear references
        self._window = None
        self._stage = None
        self._usd_context = None
        self._event_stream = None

    def _get_cached_property(self, cache_attr: str, metadata_key: str, settings_path: str, default_path: str = None):
        """
        Get property value with metadata and settings fallback.

        Checks cache first, then stage metadata, then settings.

        Args:
            cache_attr: Name of the cache attribute
            metadata_key: Stage metadata key
            settings_path: Settings path
            default_path: Optional fallback settings path

        Returns:
            The property value from the first available source
        """
        cached_value = getattr(self, cache_attr, None)
        if cached_value is None:
            # Access customLayerData directly from root layer
            metadata_val = None
            if self._stage:
                root_layer = self._stage.GetRootLayer()
                if root_layer.customLayerData:
                    metadata_val = root_layer.customLayerData.get(metadata_key)

            # Read from settings_path first (current session value), then fall back to default_path
            settings_val = self._settings.get(settings_path)
            if settings_val is None and default_path:
                settings_val = self._settings.get(default_path)

            cached_value = metadata_val if metadata_val is not None else settings_val
            setattr(self, cache_attr, cached_value)

        return cached_value

    def _set_cached_property(self, cache_attr: str, settings_path: str, value):
        """
        Set property value with caching and settings persistence.

        Args:
            cache_attr: Name of the cache attribute
            settings_path: Settings path to persist to
            value: Value to set
        """
        setattr(self, cache_attr, value)
        self._settings.set(settings_path, value)

    @property
    def ceiling(self) -> float:
        """Get ceiling height."""
        return self._get_cached_property("_ceiling", CEIL_KEY, S_PATH.CEILING, S_PATH.DEFAULT_CEILING)

    @ceiling.setter
    def ceiling(self, value: float):
        """Set ceiling height."""
        self._set_cached_property("_ceiling", S_PATH.CEILING, value)

    @property
    def floor(self) -> float:
        """Get floor height."""
        return self._get_cached_property("_floor", FLOOR_KEY, S_PATH.FLOOR, S_PATH.DEFAULT_FLOOR)

    @floor.setter
    def floor(self, value: float):
        """Set floor height."""
        self._set_cached_property("_floor", S_PATH.FLOOR, value)

    @property
    def tile_size(self) -> int:
        """Get tile size in meters."""
        # Check cache first
        if self._tile_size is None:
            # Check stage metadata
            metadata_val = None
            if self._stage:
                root_layer = self._stage.GetRootLayer()
                if root_layer.customLayerData:
                    metadata_val = root_layer.customLayerData.get(TILE_SIZE_KEY)
            # Fall back to settings (default: 256)
            default_tile_size = self._settings.get(S_PATH.DEFAULT_TILE_SIZE) or 256
            self._tile_size = metadata_val if metadata_val is not None else default_tile_size
        return self._tile_size

    @tile_size.setter
    def tile_size(self, value: int):
        """Set tile size in meters."""
        # Only cache the value, don't persist to settings (defaults come from settings)
        self._tile_size = value

    @property
    def resolution(self) -> int:
        """Get render resolution (pixels per tile)."""
        return self._get_cached_property("_resolution", RESOLUTION_KEY, S_PATH.RESOLUTION)

    @resolution.setter
    def resolution(self, value: int):
        """Set render resolution (pixels per tile)."""
        self._set_cached_property("_resolution", S_PATH.RESOLUTION, value)

    @property
    def range(self) -> Gf.Range3d:
        """
        Get minimap bounds.

        Priority order:
        1. Cached value (if explicitly set via setter)
        2. Bounds from stage metadata (if saved with minimap)
        3. Bounds from settings (if set)
        4. Calculated from scene geometry via prim_bounds()

        Returns:
            Gf.Range3d: 3D range representing minimap coverage area
        """
        if not self._stage:
            return self.prim_bounds()

        # Check cached value first (highest priority)
        if self._range is not None:
            return self._range

        # Try to get bounds from metadata or settings
        bounds_str = None
        root_layer = self._stage.GetRootLayer()
        if root_layer.customLayerData:
            bounds_str = root_layer.customLayerData.get(BOUNDS_KEY)
        if not bounds_str:
            bounds_str = self._settings.get(S_PATH.BOUNDS)

        if bounds_str:
            bounds_list = bounds_str.split(",")
            if len(bounds_list) == 6:
                try:
                    floats = list(map(float, bounds_list))
                    bounds_min = tuple(floats[:3])
                    bounds_max = tuple(floats[3:])
                    cached_range = Gf.Range3d(bounds_min, bounds_max)
                    self._range = cached_range  # Cache it
                    return cached_range
                except ValueError:
                    pass

        # Fall back to calculating from scene geometry
        return self.prim_bounds()

    @range.setter
    def range(self, value: Gf.Range3d | None):
        """Set minimap bounds."""
        if value is None:
            self._range = None
            self._settings.set(S_PATH.BOUNDS, "")
            # Don't clear stage metadata on load - only when explicitly requested
            # This prevents marking the stage as dirty just from loading
        else:
            min_vals, max_vals = value.GetMin(), value.GetMax()
            range_str = f"{min_vals[0]:.5f},{min_vals[1]:.5f},{min_vals[2]:.5f},{max_vals[0]:.5f},{max_vals[1]:.5f},{max_vals[2]:.5f}"
            self._range = value
            self._settings.set(S_PATH.BOUNDS, range_str)

            # Clear bounds cache to force recalculation
            self._bounds_top = None
            self._bounds_bottom = None

    @property
    def bounds_top(self) -> float:
        """Get top boundary."""
        if self._bounds_top is None:
            self._update_bounds()
        return self._bounds_top

    @property
    def bounds_bottom(self) -> float:
        """Get bottom boundary."""
        if self._bounds_bottom is None:
            self._update_bounds()
        return self._bounds_bottom

    def _update_bounds(self):
        """Update bounds from range."""
        if self._stage:
            mpu = UsdGeom.GetStageMetersPerUnit(self._stage)
            up_component = 2 if UsdGeom.GetStageUpAxis(self._stage) == UsdGeom.Tokens.z else 1
            range_max, range_min = self.range.GetMax(), self.range.GetMin()
            self._bounds_top, self._bounds_bottom = range_max[up_component] * mpu, range_min[up_component] * mpu

    def prim_bounds(self, selected_paths: Union[str, list[str]] = None) -> Gf.Range3d:
        """
        Calculate bounding box from scene geometry.

        Args:
            selected_paths: Prim path(s) to calculate bounds for.
                          Defaults to "/" (entire scene).
                          Can be a string path, comma-separated paths, or list of paths.

        Returns:
            Gf.Range3d: Combined bounding box of all specified prims.
                       Returns default 100x100 unit box if no geometry found.
        """
        selected_paths = ["/"] if selected_paths is None else selected_paths
        selected_paths = selected_paths.split(",") if isinstance(selected_paths, str) else selected_paths

        # Get bounds of first prim
        first_bound = self._usd_context.compute_path_world_bounding_box(selected_paths[0])
        if not first_bound:
            # No geometry found - return a sensible default
            carb.log_warn("No geometry found in stage. Using default bounds: 100x100 units centered at origin.")
            return Gf.Range3d(Gf.Vec3d(-50, -50, -50), Gf.Vec3d(50, 50, 50))

        # Union with remaining prims' bounds
        combined_bounds = Gf.Range3d(tuple(first_bound[0]), tuple(first_bound[1]))
        for path in selected_paths[1:]:
            bound = self._usd_context.compute_path_world_bounding_box(path)
            if bound:
                prim_bounds = Gf.Range3d(tuple(bound[0]), tuple(bound[1]))
                combined_bounds = Gf.Range3d.GetUnion(combined_bounds, prim_bounds)

        return combined_bounds

    def calculate_tile_count(self) -> int:
        """
        Calculate the number of tiles needed to cover the scene at the current tile size.

        Returns:
            int: Number of tiles needed (minimum 1)
        """
        if not self._stage:
            return 1

        try:
            _ = self._stage.GetPseudoRoot()
        except Exception:
            return 1

        current_range = self.range
        if not current_range or current_range.IsEmpty():
            return 1

        up_axis = UsdGeom.GetStageUpAxis(self._stage)
        mpu = UsdGeom.GetStageMetersPerUnit(self._stage)
        dimension = current_range.GetMax() - current_range.GetMin()
        h_axis_idx, v_axis_idx, _, _, _ = _get_axis_indices(up_axis)

        # Calculate area in stage units
        area = dimension[h_axis_idx] * dimension[v_axis_idx]

        # Calculate how many tiles at current tile_size
        tile_size_in_stage_units = self.tile_size / mpu
        tiles_needed = area / math.pow(tile_size_in_stage_units, 2) * 2

        return max(int(tiles_needed), 1)

    def calculate_tile_size(self, target_count: int) -> int:
        """
        Calculate the tile size (in meters) needed to achieve a specific tile count.

        For a single tile, returns the minimum size to enclose the entire scene bounds.
        For multiple tiles, calculates optimal tile size to achieve approximately that count.

        Args:
            target_count: Desired number of tiles

        Returns:
            int: Tile size in meters (minimum 64)
        """
        default_tile_size = self._settings.get(S_PATH.DEFAULT_TILE_SIZE) or 256

        if not self._stage:
            return default_tile_size

        try:
            _ = self._stage.GetPseudoRoot()
        except Exception:
            return default_tile_size

        current_range = self.range
        if not current_range or current_range.IsEmpty():
            return default_tile_size

        up_axis = UsdGeom.GetStageUpAxis(self._stage)
        mpu = UsdGeom.GetStageMetersPerUnit(self._stage)
        dimension = current_range.GetMax() - current_range.GetMin()
        h_axis_idx, v_axis_idx, _, _, _ = _get_axis_indices(up_axis)

        if target_count == 1:
            # Special case: single tile should fit entire bounds
            # Use the larger horizontal dimension
            max_dimension_stage_units = max(dimension[h_axis_idx], dimension[v_axis_idx])
            size_in_meters = max_dimension_stage_units * mpu
            return max(int(math.ceil(size_in_meters)), 64)
        else:
            # Calculate tile size for multiple tiles
            area = dimension[h_axis_idx] * dimension[v_axis_idx]
            tile_size_stage_units = math.sqrt(area / target_count * 2)
            size_in_meters = tile_size_stage_units * mpu
            return max(int(size_in_meters), 64)

    def _get_all_tiles(self) -> list:
        """Get all tiles from all groups."""
        return [tile for group in self._map_tile_groups for tile in group.tiles]

    def _transfer_all_tiles_to_system_memory(self):
        """Transfer all tiles from GPU to system memory."""
        all_tiles = self._get_all_tiles()
        gpu_tiles_count = 0

        for tile in all_tiles:
            if hasattr(tile, "image_data") and tile.image_data is not None:
                gpu_tiles_count += 1
                tile.transfer_to_system_memory()

        if gpu_tiles_count > 0:
            wp.synchronize()
            gc.collect()

    def _toggle_features(self, restore_dict: dict = None) -> dict:
        """
        Toggle render features (shadows, grid) for cleaner minimap output.
        If restore_dict is None, disables features and returns dict for restoration.
        If restore_dict is provided, restores original settings.

        Args:
            restore_dict: If provided, restores settings from this dict. If None, disables features.

        Returns:
            dict: Map of setting path to original value (disable mode only), or empty dict (restore mode)
        """
        try:
            if restore_dict is None:
                # Disable mode: save and disable features
                feature_settings = {
                    # Shadow settings (if R_SHADOWS is False)
                    "/rtx/shadows/enabled": None if not R_SHADOWS else "skip",
                    "/rtx/raytracing/shadows/enabled": None if not R_SHADOWS else "skip",
                    # Grid settings (if R_GRID is False)
                    "/app/viewport/grid/enabled": None if not R_GRID else "skip",
                    "/persistent/app/viewport/grid/enabled": None if not R_GRID else "skip",
                    "/app/viewport/displayOptions": None if not R_GRID else "skip",
                    # Always disable viewport display overlays (lights, cameras, etc.)
                    # to prevent gizmos from appearing in captured tiles
                    "/persistent/app/viewport/displayOptions": None,
                }

                for path, _ in feature_settings.items():
                    if _ == "skip":  # Skip if feature not being toggled
                        continue
                    feature_settings[path] = self._settings.get(path)
                    # Set disabled state
                    if "grid" in path or "display" in path:
                        self._settings.set(path, False if "enabled" in path else 0)
                    else:
                        self._settings.set(path, False)

                if settings.DEV_MODE:
                    features = []
                    if not R_SHADOWS:
                        features.append("shadows")
                    if not R_GRID:
                        features.append("grid")
                    if features:
                        carb.log_info(f"DEV: Disabled features: {', '.join(features)}")
                return {k: v for k, v in feature_settings.items() if v != "skip"}

            else:
                # Restore mode: restore original settings
                for path, value in restore_dict.items():
                    if value is not None:
                        self._settings.set(path, value)
                    else:
                        self._settings.destroy_item(path)

                if settings.DEV_MODE:
                    carb.log_info(f"DEV: Restored render features")
                return {}

        except Exception as e:
            carb.log_warn(f"Error toggling features: {e}")
            return {}

    def _cleanup_tiles(self):
        """Clean up all tiles and GPU resources."""
        _cleanup_gpu_resources(self._get_all_tiles())
        self._map_tile_groups.clear()
        # GPU cleanup
        _gpu_cleanup_sync()

    def get_event_stream(self) -> carb.events.IEventStream:
        """Get event stream for minimap updates."""
        return self._event_stream

    def get_tiles(self, actor_pos: Gf.Vec3d) -> list[MapTile]:
        """Get tiles for given position."""
        if not self._map_tile_groups:
            return None

        for group in self._map_tile_groups:
            if group.intersects(actor_pos):
                return group.tiles

        return None

    def get_up_axis(self) -> str:
        """Get up axis for tile orientation."""
        return self._map_tiles_up_axis

    def generate_minimap(
        self,
        height_min: int | None = None,
        height_max: int | None = None,
        tile_size: int | None = None,
        tile_count: int | None = None,
        job_limit: int = 3,
        preview: bool = False,
        bounds: Gf.BBox3d | None = None,
        rebuild: bool = True,
    ):
        """Generate minimap tiles."""
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

        # Start new generation task
        self._task = asyncio.ensure_future(
            self._generate_minimap_async(
                height_min, height_max, tile_size, tile_count, job_limit, preview, bounds, rebuild
            )
        )
        # Track the main generation task
        self._async_tasks.append(self._task)

        # Clean up completed tasks to prevent memory leaks
        self._async_tasks = [t for t in self._async_tasks if not t.done()]

    async def _post_viewport_cleanup(self):
        """Cleanup after viewport destruction - GPU memory management per tile.

        Performs GPU cleanup every N tiles (controlled by GPU_CLEANUP_INTERVAL)
        to balance speed vs memory usage during large minimap generation.
        """
        if DUMP_GPU:
            self._tile_counter += 1
            # Only clean every N tiles (configurable via GPU_CLEANUP_INTERVAL)
            if self._tile_counter % GPU_CLEANUP_INTERVAL == 0:
                _gpu_cleanup_sync()
                # Wait for viewport update to ensure cleanup completes
                await self._app.next_update_async()
                if settings.DEV_MODE:
                    carb.log_info(f"DEV: GPU cleanup at tile #{self._tile_counter}")

    def _get_metadata_target(self):
        """Get stage for metadata operations."""
        return self._stage

    async def clear_minimap(self):
        """Clear all minimap tiles with comprehensive GPU cleanup and UI notification."""
        # Use centralized cleanup method
        self._cleanup_tiles()

        # Wait for app update to allow cleanup to process
        await self._app.next_update_async()

        # Dispatch clear event to notify listeners (triggers black screen flash)
        if self._window and self._event_stream:
            self._event_stream.dispatch(MinimapGeneratorEventTypes.CLEAR)

        # Multiple sync passes to ensure GPU resources are freed (critical for resolution changes)
        for _ in range(2):
            _gpu_cleanup_sync()

        # Final app update to complete cleanup
        await self._app.next_update_async()

    def load_tiles(self) -> bool:
        """Load minimap tiles from stage metadata."""
        try:
            # Validate stage before loading
            if not self._stage:
                return False

            start_time = time.perf_counter()

            # Access customLayerData directly from root layer (not through stage API)
            root_layer = self._stage.GetRootLayer()
            if not root_layer.customLayerData:
                return False

            custom_data = root_layer.customLayerData

            if not custom_data.get(ROOT_KEY):
                # No metadata found - let property getters handle defaults dynamically
                # Don't cache values here to allow dynamic calculation of tiles based on bounds
                return False

            self._map_tile_groups.clear()

            data_version = custom_data.get(VERSION_KEY)
            if data_version != DATA_VERSION:
                return False

            # Load nested group structure (matches save_tiles format)
            group_data = custom_data.get(GROUP_KEY)
            if not group_data:
                if settings.DEV_MODE:
                    logger.warning("DEV: Minimap metadata exists but no tile data found")
                return False

            @carb.profiler.profile
            def load_fn(index, encoded_data, tile_group: MapTileGroup) -> MapTile:
                index = int(index)

                carb.profiler.begin(0, "decode")
                decoded = base64.standard_b64decode(encoded_data)
                carb.profiler.end(0)

                deserialized_tile_data = pickle.loads(decoded)
                tile_saved = MapTileSaved(**deserialized_tile_data)
                tile = MapTile.from_saved(tile_saved)

                tile_group.tiles.append(tile)

            if USE_MT:
                jobs = []
                for group_index, group in group_data.items():
                    range_min = group.get("range_min")
                    range_max = group.get("range_max")
                    range_transform = group.get("range_transform")
                    group_in = MapTileGroup(Gf.BBox3d(Gf.Range3d(range_min, range_max), range_transform))
                    self._map_tile_groups.append(group_in)

                    tile_data = group.get("tiles")
                    if tile_data:
                        jobs += [
                            self._executor.submit(load_fn, index, encoded_data, group_in)
                            for index, encoded_data in tile_data.items()
                        ]
                concurrent.futures.wait(jobs)
            else:
                for group_index, group in group_data.items():
                    range_min = group.get("range_min")
                    range_max = group.get("range_max")
                    range_transform = group.get("range_transform")
                    group_in = MapTileGroup(Gf.BBox3d(Gf.Range3d(range_min, range_max), range_transform))
                    self._map_tile_groups.append(group_in)

                    tile_data = group.get("tiles")
                    if tile_data:
                        for index, encoded_data in tile_data.items():
                            load_fn(index, encoded_data, group_in)

            if self._map_tile_groups:
                self._map_tiles_up_axis = custom_data.get(UP_AXIS_KEY)

                # Initialize floor/ceiling from metadata or bounds if not present
                floor_metadata = custom_data.get(FLOOR_KEY)
                ceiling_metadata = custom_data.get(CEIL_KEY)

                # Clear cached values to force reload from metadata
                self._floor = None
                self._ceiling = None
                self._tile_size = None
                self._resolution = None
                self._range = None

                # IMPORTANT: Explicitly read resolution from metadata to ensure it's cached
                # This prevents fallback to settings when metadata exists
                resolution_in_metadata = custom_data.get(RESOLUTION_KEY)
                if resolution_in_metadata is not None:
                    self._resolution = resolution_in_metadata

                load_time = time.perf_counter() - start_time
                if settings.DEV_MODE:
                    carb.log_info(f"Successfully loaded {len(self._map_tile_groups)} tile groups in {load_time:.2f}s")

            return True
        except Exception as e:
            import traceback

            carb.log_error(f"Failed to load minimap tiles: {str(e)}")
            carb.log_error(traceback.format_exc())
            self._map_tile_groups.clear()
            return False

    @carb.profiler.profile
    def save_tiles(self):
        """
        Write minimap tiles to stage metadata (in-memory).
        User must manually save the stage (File -> Save) to persist changes to disk.

        Note: Tile groups are cleared during build (rebuild=True) to ensure only
        current tiles are saved. No need to clear here.
        """
        start_time = time.perf_counter()

        if not self._stage:
            return

        # Validate tiles before saving
        total_tiles = 0
        valid_tiles = 0
        invalid_tiles = []
        for group_idx, group in enumerate(self._map_tile_groups):
            for tile_idx, tile in enumerate(group.tiles):
                total_tiles += 1
                has_system_data = hasattr(tile, "_system_data") and tile._system_data is not None
                has_image_data = hasattr(tile, "image_data") and tile.image_data is not None
                if has_system_data or has_image_data:
                    valid_tiles += 1
                else:
                    invalid_tiles.append((group_idx, tile_idx, tile))

        results: dict[str, bytes] = {}

        @carb.profiler.profile
        def process_fn(i, tiles, group_idx) -> tuple[int, bytes, int, Exception]:
            """Process a single tile and return encoded data or error."""
            try:
                tile = tiles[i]
                tile_saved = MapTileSaved.from_tile(tile)
                serialized_data = pickle.dumps(asdict(tile_saved))
                encoded = base64.standard_b64encode(serialized_data)
                return i, encoded, group_idx, None
            except Exception as e:
                return i, None, group_idx, e

        failed_tiles = []
        if USE_MT:
            jobs = []
            for group_idx, group in enumerate(self._map_tile_groups):
                jobs += [self._executor.submit(process_fn, i, group.tiles, group_idx) for i in range(len(group.tiles))]
            concurrent.futures.wait(jobs)
            for job in jobs:
                i, encoded, group_idx, error = job.result()
                if error is None:
                    results[f"{GROUP_KEY}:{group_idx}:tiles:{i}"] = encoded
                else:
                    failed_tiles.append((group_idx, i, error))
        else:
            for group_idx, group in enumerate(self._map_tile_groups):
                for i, _ in enumerate(group.tiles):
                    _, encoded, _, error = process_fn(i, group.tiles, group_idx)
                    if error is None:
                        results[f"{GROUP_KEY}:{group_idx}:tiles:{i}"] = encoded
                    else:
                        failed_tiles.append((group_idx, i, error))

        if not self._stage:
            return

        # Check if stage is saveable
        root_layer = self._stage.GetRootLayer()
        if root_layer.anonymous:
            carb.log_error("Cannot save minimap metadata to anonymous stage. Please save the stage to a file first.")
            return

        if root_layer.permissionToEdit == False:
            carb.log_error(f"Cannot save minimap metadata: stage is read-only. Layer: {root_layer.identifier}")
            return

        # Build nested dictionary structure and write directly to layer
        # Structure: groups -> group_idx -> {range_min, range_max, range_transform, tiles -> {tile_idx: data}}
        with Sdf.ChangeBlock():
            # Build nested group structure
            groups_dict = {}
            for group_idx, group in enumerate(self._map_tile_groups):
                bbox = group.bbox
                group_range = bbox.GetRange()

                # Build tiles dictionary for this group
                tiles_dict = {}
                for tile_idx in range(len(group.tiles)):
                    key = f"{GROUP_KEY}:{group_idx}:tiles:{tile_idx}"
                    if key in results:
                        tiles_dict[str(tile_idx)] = results[key]

                # Build group dictionary
                group_dict = {
                    "range_min": group_range.GetMin(),
                    "range_max": group_range.GetMax(),
                    "range_transform": bbox.GetMatrix(),
                    "tiles": tiles_dict,
                }
                groups_dict[str(group_idx)] = group_dict

            # Get existing customLayerData and update it
            existing_data = dict(root_layer.customLayerData) if root_layer.customLayerData else {}

            # Clear old group data from custom layer data
            keys_to_remove = [k for k in existing_data.keys() if k.startswith(GROUP_KEY)]
            for k in keys_to_remove:
                del existing_data[k]

            # Add new data
            existing_data[GROUP_KEY] = groups_dict
            existing_data[ROOT_KEY] = True
            existing_data[UP_AXIS_KEY] = self._map_tiles_up_axis
            existing_data[VERSION_KEY] = DATA_VERSION
            existing_data[FLOOR_KEY] = self.floor
            existing_data[CEIL_KEY] = self.ceiling

            range_min = self.range.GetMin()
            range_max = self.range.GetMax()
            world_tuple = f"{range_min[0]:.5f},{range_min[1]:.5f},{range_min[2]:.5f},{range_max[0]:.5f},{range_max[1]:.5f},{range_max[2]:.5f}"
            existing_data[BOUNDS_KEY] = world_tuple
            existing_data[TILE_SIZE_KEY] = self.tile_size
            existing_data[RESOLUTION_KEY] = self.resolution

            # Write back to layer
            root_layer.customLayerData = existing_data

        save_time = time.perf_counter() - start_time
        if settings.DEV_MODE:
            carb.log_info(f"Successfully saved {len(self._map_tile_groups)} tile groups in {save_time:.2f}s")

        # Notify user to save stage manually
        carb.log_info(
            f"Minimap metadata written successfully. Save the stage (File -> Save or Ctrl+S) to persist changes."
        )
        carb.log_info(f"File path: {root_layer.identifier}")

    def clear_data(self, all: bool = False):
        """
        Clear minimap data from stage metadata.
        First clears the minimap cache (GPU resources), then removes metadata.

        Args:
            all: If True, removes all minimap metadata. If False, only removes tile data.
        """
        if not self._stage:
            return

        # Clear minimap cache first (handles GPU cleanup and UI notification)
        asyncio.ensure_future(self.clear_minimap())

        # Then clear metadata from customLayerData
        root_layer = self._stage.GetRootLayer()
        if root_layer.customLayerData:
            custom_data = dict(root_layer.customLayerData)
            if all:
                # Delete All Metadata: Remove everything
                keys_to_remove = [k for k in custom_data.keys() if k.startswith("omni_minimap")]
                for k in keys_to_remove:
                    del custom_data[k]
                carb.log_info(f"Deleted all minimap metadata ({len(keys_to_remove)} keys)")
            else:
                # Delete Map Data Only: Remove only tile groups, preserve settings
                # Preserves: floor, ceiling, bounds, tile_size, resolution, version, up_axis
                if GROUP_KEY in custom_data:
                    del custom_data[GROUP_KEY]
                    carb.log_info(
                        f"Deleted tile data. Preserved settings: floor, ceiling, bounds, tile_size, resolution"
                    )
            root_layer.customLayerData = custom_data

    def _on_stage_opened(self):
        """Handle stage opened event."""
        # Cancel any pending stage initialization tasks to prevent duplicates
        if self._stage_init_task and not self._stage_init_task.done():
            self._stage_init_task.cancel()
            self._stage_init_task = None

        async def deferred_init():
            try:
                # Wait for stage to fully settle before any operations
                await asyncio.sleep(0.1)

                stage = self._usd_context.get_stage()
                if not stage:
                    return
                # Skip initialization for anonymous stages (e.g., "New Stage")
                # This prevents marking empty stages as dirty
                if stage.GetRootLayer().anonymous:
                    return
                self._stage = stage
                self._cleanup_tiles()

                # Clear ALL cached state from previous stage
                self._bounds_top = None
                self._bounds_bottom = None
                self._floor = None
                self._ceiling = None
                self._tile_size = None
                self._resolution = None
                self._range = None

                # Note: We don't clear carb.settings here to avoid any potential side effects
                # Settings will be overwritten when new metadata is loaded or values are set

                # Try to load metadata from the NEW stage
                tiles_loaded = self.load_tiles()

                # If no tiles were loaded, initialize bounds from stage geometry
                if not tiles_loaded:
                    # Trigger automatic bounds calculation from scene geometry
                    # This populates range, floor, ceiling, and tile information
                    calculated_range = self.range  # Property getter calculates if needed
                    if calculated_range and not calculated_range.IsEmpty():
                        # Access properties to ensure they're calculated and cached
                        _ = self.floor
                        _ = self.ceiling
                        _ = self.tile_size
                        if settings.DEV_MODE:
                            carb.log_info(f"DEV: Initialized bounds from stage geometry")

                # Update carb settings to match current stage (from metadata or calculated)
                # This ensures settings are always in sync with the loaded stage
                if tiles_loaded or (self._range and not self._range.IsEmpty()):
                    self.range = self.range  # Trigger setter to sync to carb settings
                    self.floor = self.floor  # Trigger setter to sync to carb settings
                    self.ceiling = self.ceiling  # Trigger setter to sync to carb settings
                    if settings.DEV_MODE:
                        carb.log_info(f"DEV: Synced bounds/floor/ceiling to carb settings")

                # Show settings panel if no tiles were loaded
                self._window.show_settings = not tiles_loaded

                # Dispatch UPDATE event to refresh UI with loaded tiles/metadata
                await self._app.next_update_async()
                if self._window and self._event_stream:
                    self._event_stream.dispatch(MinimapGeneratorEventTypes.UPDATE)

                # Auto-fit zoom only if zoom not already set (new stage load)
                # Hot reload: CAM_ZOOM persists, skip auto-fit
                # New stage: CAM_ZOOM was cleared in _on_stage_closing, do auto-fit
                saved_zoom = self._settings.get(S_PATH.CAM_ZOOM)
                if settings.DEV_MODE:
                    carb.log_info(f"DEV: Stage opened - saved_zoom={saved_zoom}, tiles_loaded={tiles_loaded}")

                if saved_zoom is None:
                    if self._window and hasattr(self._window, "auto_fit_zoom"):
                        # Ensure bounds are loaded from metadata or calculated before auto-fit
                        # This guarantees auto_fit_zoom has valid bounds to work with
                        if self._range is None or self._range.IsEmpty():
                            _ = self.range  # Force bounds calculation if not already done
                            if settings.DEV_MODE:
                                carb.log_info("DEV: Forced bounds calculation before auto-fit")

                        await self._app.next_update_async()
                        self._window.auto_fit_zoom()
                        if settings.DEV_MODE:
                            new_zoom = self._settings.get(S_PATH.CAM_ZOOM)
                            carb.log_info(f"DEV: Auto-fit zoom complete - new zoom={new_zoom}")
                else:
                    if settings.DEV_MODE:
                        carb.log_info(f"DEV: Skipping auto-fit - using saved zoom={saved_zoom}")

                # Auto-generate if no tiles were loaded and setting is enabled
                if not tiles_loaded:
                    if self._settings.get(S_PATH.CAPTURE_ON_STAGE_OPENED):
                        self.generate_minimap()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if settings.DEV_MODE:
                    logger.warning(f"DEV: Error dispatching update event: {e}")
            finally:
                self._stage_init_task = None

        # Start the deferred initialization and track it separately
        self._stage_init_task = asyncio.ensure_future(deferred_init())
        self._async_tasks.append(self._stage_init_task)
        self._async_tasks = [t for t in self._async_tasks if not t.done()]

    def _destroy_settings_if_exist(self, *setting_paths):
        """Destroy settings if they exist (helper to reduce boilerplate)."""
        for path in setting_paths:
            if self._settings.get(path):
                self._settings.destroy_item(path)

    def _on_stage_closing(self):
        """Handle stage closing event."""
        if settings.DEV_MODE:
            carb.log_info(f"DEV: Stage closing - clearing settings (old zoom={self._settings.get(S_PATH.CAM_ZOOM)})")

        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

        # Reset stage-specific settings to defaults for next stage load
        self._destroy_settings_if_exist(S_PATH.CAM_ZOOM, S_PATH.VIEW_CENTER, S_PATH.BOUNDS)

        # Floor/Ceiling: reset to defaults (new stage will read from metadata or use these)
        self._settings.set(S_PATH.FLOOR, self._settings.get(S_PATH.DEFAULT_FLOOR))
        self._settings.set(S_PATH.CEILING, self._settings.get(S_PATH.DEFAULT_CEILING))

        if settings.DEV_MODE:
            carb.log_info(f"DEV: Settings cleared - CAM_ZOOM now={self._settings.get(S_PATH.CAM_ZOOM)}")

    def _on_stage_closed(self):
        """Handle stage closed event."""
        self._cleanup_tiles()
        # Clear all cached stage-dependent state
        (
            self._stage,
            self._bounds_top,
            self._bounds_bottom,
            self._floor,
            self._ceiling,
            self._tile_size,
            self._resolution,
            self._range,
        ) = (None,) * 8

    def in_vbounds(self, value: float) -> bool:
        """Check if value is within vertical bounds."""
        if not self._stage:
            return True
        return self.bounds_bottom < value < self.bounds_top

    async def _generate_minimap_async(
        self,
        height_min: int = 0,
        height_max: int = 10,
        tile_size: int | None = None,
        tile_count: int | None = None,
        job_limit: int = 3,
        preview: bool = False,
        bounds: Gf.BBox3d | None = None,
        rebuild: bool = True,
    ):
        """Asynchronously generate minimap tiles.

        Creates viewport cameras and captures tile images in parallel up to the
        specified job limit. Handles multi-level support and tile organization.

        Args:
            height_min: Lower height bound in meters
            height_max: Upper height bound in meters
            tile_size: Size of each tile in meters
            tile_count: Target number of tiles
            job_limit: Maximum concurrent generation jobs
            preview: If True, generate a preview tile
            bounds: Custom minimap bounds
            rebuild: If True, clear existing tiles before generation
        """
        start_time = time.perf_counter()

        # Validate stage at the start
        if not self._stage:
            logger.warning("Cannot generate minimap: no valid stage found. Please open or save a USD stage first.")
            return

        # Hide prim icons (lights, cameras, etc.) during tile capture so they don't
        # appear in the minimap viewport while generation is in progress.
        from .waypoints import get_waypoints_layer

        waypoints = get_waypoints_layer()
        if waypoints:
            waypoints.set_icons_visible(False)

        # Reset tile counter for GPU cleanup interval tracking
        self._tile_counter = 0

        build_delay = self._settings.get(S_PATH.BUILD_DELAY) or 0.15
        if build_delay > 0:
            update_cycles = max(3, int(build_delay * 60))
            cycle_delay = build_delay / update_cycles
            for i in range(update_cycles):
                await self._app.next_update_async()
                if cycle_delay > 0:
                    await asyncio.sleep(cycle_delay)

        capture_height_min_meters = height_min if height_min is not None else 0.0  # min at 0m height
        capture_height_max_meters = (
            height_max if height_max is not None else 1.8 + capture_height_min_meters
        )  # max 1.8m height

        world_range = bounds if bounds is not None else self.range
        if not world_range or world_range.IsEmpty():
            return

        # CRITICAL: Save the current active camera before generation so we can restore it later
        # This prevents capture cameras from becoming the active viewport camera
        # Save: camera path, position, orientation (rotation), and FOV
        from omni.kit.viewport.utility import get_active_viewport

        original_camera_path = None
        original_camera_transform = None
        original_camera_fov = None
        try:
            viewport_api = get_active_viewport()
            if viewport_api:
                original_camera_path = viewport_api.get_active_camera()
                if original_camera_path:
                    # Save camera transform (position + orientation) and FOV
                    camera_prim = self._stage.GetPrimAtPath(original_camera_path)
                    if camera_prim and camera_prim.IsValid():
                        xform_api = UsdGeom.XformCommonAPI(camera_prim)
                        if xform_api:
                            translation, rotation, scale, pivot, rot_order = xform_api.GetXformVectors(
                                Usd.TimeCode.Default()
                            )
                            original_camera_transform = (translation, rotation, scale, pivot, rot_order)

                        camera = UsdGeom.Camera(camera_prim)
                        if camera:
                            original_camera_fov = camera.GetHorizontalApertureAttr().Get()
        except Exception as e:
            if settings.DEV_MODE:
                carb.log_warn(f"DEV: Error saving camera state: {e}")

        # Disable render features (shadows, grid) for cleaner minimap output
        restore_settings = self._toggle_features()

        selection = self._usd_context.get_selection()
        prev_selected_paths = selection.get_selected_prim_paths()
        selection.clear_selected_prim_paths()

        await self._app.next_update_async()

        # Wait additional frames for settings to propagate
        for _ in range(3):
            await self._app.next_update_async()

        # Re-validate stage after await (stage could have closed)
        if not self._stage:
            logger.warning("Cannot generate minimap: stage was closed during initialization")
            return

        bbmin = world_range.GetMin()
        bbmax = world_range.GetMax()
        up_axis = UsdGeom.GetStageUpAxis(self._stage)
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(self._stage)
        h_axis_idx, v_axis_idx, d_axis_idx, cam_rot_axis, cam_rot = _get_axis_indices(up_axis)

        dimension = bbmax - bbmin

        self.ceiling = height_max
        self.floor = height_min
        if tile_size is not None:
            self.tile_size = tile_size
        self.range = world_range

        # Prevent generating excessive tiles
        max_tiles = self._settings.get(S_PATH.MAX_TILES) or 128
        tile_count_needed = self.calculate_tile_count()
        if tile_count_needed > max_tiles:
            carb.log_warn(
                f"Tile count ({tile_count_needed}) exceeds maximum limit ({max_tiles}). Please click 'Init' button to initialize stage bounds, increase tile size, or reduce scene bounds."
            )
            return
        if not self.in_vbounds(self.ceiling):
            carb.log_warn("Ceiling is outside bounds. Please adjust ceiling or bounds.")
            return
        if not self.in_vbounds(self.floor):
            carb.log_warn("Floor is outside bounds. Please adjust floor or bounds.")
            return

        # Use specified tile count or current tile size
        if tile_count is not None:
            tile_size = self.calculate_tile_size(tile_count)
        else:
            tile_size = self.tile_size

        tile_size = tile_size / meters_per_unit

        if preview:
            tile_size = max(dimension[h_axis_idx], dimension[v_axis_idx])

        # Clear tile groups to allow new tiles to replace old ones
        # Uses _cleanup_tiles() but does NOT dispatch CLEAR event to avoid black flash
        if rebuild:
            self._cleanup_tiles()

        # Use session layer for all tile captures (temporary edits)
        session_layer = self._stage.GetSessionLayer()

        all_tile_tasks: list[asyncio.Task] = []
        index = 0
        for i in range(math.ceil(dimension[h_axis_idx] / tile_size)):
            for j in range(math.ceil(dimension[v_axis_idx] / tile_size)):
                index += 1
                h_min = bbmin[h_axis_idx] + i * tile_size
                h_max = bbmin[h_axis_idx] + (i + 1) * tile_size
                h_max = min(h_max, bbmax[h_axis_idx])

                v_min = bbmin[v_axis_idx] + j * tile_size
                v_max = bbmin[v_axis_idx] + (j + 1) * tile_size
                v_max = min(v_max, bbmax[v_axis_idx])

                desc = CaptureJobDesc(
                    h_min,
                    h_max,
                    v_min,
                    v_max,
                    h_axis_idx,
                    v_axis_idx,
                    d_axis_idx,
                    cam_rot_axis,
                    cam_rot,
                    job_limit,
                    capture_height_min_meters,
                    capture_height_max_meters,
                    meters_per_unit,
                    tile_size,
                    index,
                )

                task = asyncio.create_task(self.__capture_job(session_layer, desc))
                all_tile_tasks.append(task)

        try:
            completed_tasks = await asyncio.gather(*all_tile_tasks)
            tiles: list[MapTile] = []
            for tile in completed_tasks:
                if tile is not None:  # Skip None tiles from invalid stage
                    tiles.append(tile)

        except (asyncio.CancelledError, Exception) as e:
            # Handle task cancellation or errors - clean up any partial tiles
            partial_tiles = []
            for task in all_tile_tasks:
                if not task.done():
                    task.cancel()
                    while task and not task.done():
                        await asyncio.sleep(0.05)
                elif task.done() and not task.cancelled():
                    try:
                        tile = task.result()
                        if tile:
                            partial_tiles.append(tile)
                    except Exception:
                        pass  # Ignore errors getting partial results

            # Clean up partial tiles and GPU resources
            _cleanup_gpu_resources(partial_tiles)
            # GPU cleanup after error
            _gpu_cleanup_sync()

            self._task = None

            # CRITICAL: Restore original camera even on error (including transform and FOV)
            if original_camera_path and self._stage:
                try:
                    viewport_api = get_active_viewport()
                    if viewport_api:
                        viewport_api.set_active_camera(original_camera_path)

                        # Restore transform and FOV
                        if original_camera_transform:
                            camera_prim = self._stage.GetPrimAtPath(original_camera_path)
                            if camera_prim and camera_prim.IsValid():
                                xform_api = UsdGeom.XformCommonAPI(camera_prim)
                                if xform_api:
                                    orig_trans, orig_rot, orig_scale, orig_pivot, orig_rot_order = (
                                        original_camera_transform
                                    )
                                    xform_api.SetXformVectors(
                                        orig_trans,
                                        orig_rot,
                                        orig_scale,
                                        orig_pivot,
                                        orig_rot_order,
                                        Usd.TimeCode.Default(),
                                    )

                                if original_camera_fov:
                                    camera = UsdGeom.Camera(camera_prim)
                                    if camera:
                                        camera.GetHorizontalApertureAttr().Set(original_camera_fov)
                except Exception:
                    pass

            # Restore render features even on error
            self._toggle_features(restore_settings)
            # Restore prim icon visibility even on error
            if waypoints:
                waypoints.set_icons_visible(True)
            await self._app.next_update_async()
            raise

        if MULTI_LEVEL_SUPPORT:
            import sys

            group_range_min = world_range.GetMin()
            group_range_max = world_range.GetMax()

            group_range_min[h_axis_idx] = -sys.float_info.max
            group_range_max[h_axis_idx] = sys.float_info.max

            group_range_min[v_axis_idx] = -sys.float_info.max
            group_range_max[v_axis_idx] = sys.float_info.max

            group_range_min[d_axis_idx] = capture_height_min_meters / meters_per_unit
            group_range_max[d_axis_idx] = capture_height_max_meters / meters_per_unit
            tile_group_range = Gf.Range3d(group_range_min, group_range_max)
        else:
            # Use the actual world range instead of empty range
            # This ensures valid min/max values that can be saved/loaded properly
            tile_group_range = Gf.Range3d(world_range.GetMin(), world_range.GetMax())

        bbox = Gf.BBox3d(tile_group_range)
        group = MapTileGroup(bbox, tiles)
        self._map_tile_groups.append(group)
        self._map_tiles_up_axis = up_axis

        # Transfer all tiles to system memory and clean up GPU resources
        self._transfer_all_tiles_to_system_memory()

        # GPU cleanup now happens per-tile in _post_viewport_cleanup()
        # This prevents memory exhaustion during large minimap generation

        self._event_stream.dispatch(MinimapGeneratorEventTypes.UPDATE)

        # Final GPU cleanup after all tiles are rendered
        if DUMP_GPU:
            await self._app.next_update_async()
            _gpu_cleanup_sync()
            await self._app.next_update_async()
            if settings.DEV_MODE:
                carb.log_info("DEV: Final GPU cleanup after all tiles rendered")

        selection.set_selected_prim_paths(prev_selected_paths, False)

        # CRITICAL: Clean up all capture cameras from stage and session layer
        try:
            cameras_to_remove = [
                p.GetPath()
                for p in Usd.PrimRange(self._stage.GetPseudoRoot())
                if p and p.IsValid() and "minimap_capture_cam" in p.GetPath().pathString
            ]

            if cameras_to_remove:
                session_layer = self._stage.GetSessionLayer()
                with Usd.EditContext(self._stage, session_layer):
                    for cam_path in cameras_to_remove:
                        if self._stage.GetPrimAtPath(cam_path):
                            self._stage.RemovePrim(cam_path)
                await self._app.next_update_async()

                # Recursively remove camera specs from session layer
                def remove_specs(prim_spec):
                    if "minimap_capture_cam" in prim_spec.path.pathString:
                        session_layer.RemovePrimSpec(prim_spec.path)
                        return True
                    return any(remove_specs(child) for child in list(prim_spec.nameChildren))

                with Sdf.ChangeBlock():
                    for prim_spec in list(session_layer.rootPrims):
                        remove_specs(prim_spec)

                if settings.DEV_MODE:
                    carb.log_info(f"DEV: Final cleanup - removed {len(cameras_to_remove)} capture cameras")
        except Exception as e:
            logger.error(f"Error in final camera cleanup: {e}", exc_info=True)

        # Force viewport to refresh rendering state and camera list after capture completes
        # This prevents geometry from appearing invisible due to Hydra state corruption
        # and ensures camera dropdown updates to remove capture cameras
        try:
            viewport_api = get_active_viewport()
            if viewport_api:
                # Force a render settings change to trigger Hydra refresh
                await viewport_api.wait_for_rendered_frames()
                # Multiple updates to ensure both rendering and UI refresh
                for _ in range(5):
                    await self._app.next_update_async()

                if settings.DEV_MODE:
                    carb.log_info("DEV: Viewport refresh complete after camera cleanup")
        except Exception as e:
            if settings.DEV_MODE:
                logger.warning(f"DEV: Error refreshing viewport: {e}")

        # CRITICAL: Restore the original active camera after generation completes
        await self._restore_camera(original_camera_path, original_camera_transform, original_camera_fov)

        # Restore render features (shadows, grid)
        self._toggle_features(restore_settings)
        await self._app.next_update_async()

        # Restore prim icon visibility after generation completes
        if waypoints and waypoints._icon_scene:
            waypoints._icon_scene.visible = True

        # DEV_MODE: Log generation stats
        if settings.DEV_MODE:
            elapsed = round(time.perf_counter() - start_time, 2)
            logger.warning(f"DEV: Captured Totals: {len(tiles)} tiles in {elapsed}s")

    async def __capture_job(self, session_layer: Sdf.Layer, desc: CaptureJobDesc) -> MapTile:
        """Capture a single minimap tile using session layer."""
        # Validate stage before capture
        if not self._stage:
            return None

        # Use timestamp to ensure completely unique camera path
        unique_id = f"{desc.index}_{int(time.perf_counter() * 1000000)}_{secrets.randbelow(10000)}"

        # Get the default prim path from root layer to generate correct path in temporary layer
        default_prim = self._stage.GetDefaultPrim()
        if default_prim and default_prim.IsValid():
            base_path = default_prim.GetPath()
        else:
            # Fallback to root if no default prim
            base_path = Sdf.Path("/")

        cam_path = base_path.AppendChild(f"minimap_capture_cam_{unique_id}")

        # LINUX VRAM FIX: Don't reuse viewports - always create fresh and destroy to avoid memory leak
        # Create new viewport for each tile (throttled by job_limit via semaphore in the gather)

        # Initialize variables to None in case of early exception
        tile = None
        capture_vp = None
        cam = None
        viewport_api = None
        vp_settings_base = None

        # Create camera in session layer (temporary edits)
        try:
            # Create camera in session layer
            with Usd.EditContext(self._stage, session_layer):
                cam: UsdGeom.Camera = UsdGeom.Camera.Define(
                    self._stage,
                    cam_path,
                )
                prim = cam.GetPrim()
                # Hide camera from UI pickers (stage tree, viewport dropdown, etc.)
                prim.SetMetadata("hide_in_stage_window", True)
                prim.SetMetadata("no_delete", True)
                # Mark as internal/system camera
                prim.SetCustomDataByKey("omni:kit:camera:internal", True)

                # Set rotation with explicit rotation order to ensure consistency
                xform_api = UsdGeom.XformCommonAPI(prim)
                rotate = Gf.Vec3f(0)
                rotate[desc.cam_rot_axis] = desc.cam_rot
                xform_api.SetRotate(rotate, UsdGeom.XformCommonAPI.RotationOrderXYZ)
                xform_api.SetScale((1, 1, 1))
                cam.GetProjectionAttr().Set(UsdGeom.Tokens.orthographic)

            capture_vp = create_viewport_window(
                f"Minimap Capture {desc.index}",
                width=1,
                height=1,
                visible=False,
                flags=ui.WINDOW_FLAGS_NO_FOCUS_ON_APPEARING,
            )
            viewport_api = capture_vp.viewport_api

            # Suppress all scene overlays (light/camera gizmos, guides, grid, HUD)
            # on the capture viewport so tiles contain only rendered geometry.
            vp_name = capture_vp.name if hasattr(capture_vp, "name") else capture_vp.title
            vp_settings_base = f"/persistent/app/viewport/{vp_name}"
            _VP_OVERLAY_KEYS = [
                "displayOptions",
                "guide/grid/visible",
                "guide/axis/visible",
                "guide/light/visible",
                "guide/camera/visible",
                "guide/audio/visible",
                "hud/visible",
                "scene/cameras/visible",
                "scene/lights/visible",
                "scene/audio/visible",
                "scene/skeletons/visible",
            ]
            self._settings.set(f"{vp_settings_base}/displayOptions", 0)
            self._settings.set(f"{vp_settings_base}/guide/grid/visible", False)
            self._settings.set(f"{vp_settings_base}/guide/axis/visible", False)
            self._settings.set(f"{vp_settings_base}/guide/light/visible", False)
            self._settings.set(f"{vp_settings_base}/guide/camera/visible", False)
            self._settings.set(f"{vp_settings_base}/guide/audio/visible", False)
            self._settings.set(f"{vp_settings_base}/hud/visible", False)
            self._settings.set(f"{vp_settings_base}/scene/cameras/visible", False)
            self._settings.set(f"{vp_settings_base}/scene/lights/visible", False)
            self._settings.set(f"{vp_settings_base}/scene/audio/visible", False)
            self._settings.set(f"{vp_settings_base}/scene/skeletons/visible", False)

            viewport_api.set_active_camera(prim.GetPath())

            # Wait for viewport to be ready
            await viewport_api.wait_for_render_settings_change()
            await viewport_api.wait_for_rendered_frames()

            # Add extra frames to ensure geometry is fully loaded
            # This helps prevent black tiles when Hydra is under memory pressure
            for _ in range(5):
                await self._app.next_update_async()

            h_dim = desc.h_max - desc.h_min
            v_dim = desc.v_max - desc.v_min

            h_center = 0.5 * (desc.h_max + desc.h_min)
            v_center = 0.5 * (desc.v_max + desc.v_min)

            tile_center = Gf.Vec2d(h_center, v_center)

            h_aperture = h_dim * 10
            v_aperture = v_dim * 10

            prev_view = viewport_api.view
            # Configure camera aperture and position in session layer
            with Usd.EditContext(self._stage, session_layer):
                cam.GetHorizontalApertureAttr().Set(h_aperture)
                cam.GetVerticalApertureAttr().Set(v_aperture)
                cam_pos = Gf.Vec3d()
                cam_pos[desc.h_axis_idx] = h_center
                cam_pos[desc.v_axis_idx] = v_center
                cam_pos[desc.d_axis_idx] = desc.capture_height_max_meters / desc.mpu
                xform_api.SetTranslate(cam_pos)
                cam.GetClippingRangeAttr().Set(
                    (0, (desc.capture_height_max_meters - desc.capture_height_min_meters) / desc.mpu + 1)
                )

            # make it tiled so for large scene each tile can have reasonable resolution (neither too large nor too small), and only tiles in view should be loaded (TODO)
            # Can also use UDIM if/when TexturedMesh supports it
            # Use resolution from metadata if available, otherwise from carb settings
            # Resolution = pixels per stage unit (higher = better quality, more VRAM)
            resolution_setting = self.resolution
            resolution_scale = resolution_setting / desc.tile_size
            resolution = (h_dim * resolution_scale, v_dim * resolution_scale)
            if viewport_api.resolution != resolution:
                viewport_api.resolution = resolution
                await viewport_api.wait_for_render_settings_change()

            # check view after wait_for_render_settings_change!
            waited_frame = 0
            while viewport_api.view == prev_view:
                await self._app.next_update_async()
                waited_frame += 1

            # View refreshed

            tile = MapTile()

            @carb.profiler.profile
            def on_viewport_captured(
                buffer,
                buffer_size,
                width,
                height,
                format,
                tile_width=h_dim,
                tile_height=v_dim,
                tile_center=tile_center,
                cam=cam,
                vp=capture_vp,
                tile=tile,
            ):
                tile.tile_width = tile_width
                tile.tile_height = tile_height
                tile.tile_center = tile_center
                tile.image_provider = ui.ByteImageProvider()

                if GPU_TEXTURE:
                    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
                    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
                    content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)

                    # Temporarily create GPU array for fast capture
                    tile.image_data = wp.array(content.contents, device="cuda")
                    tile.image_width = width
                    tile.image_height = height
                    # wp.synchronize()
                    tile.image_provider.set_bytes_data_from_gpu(tile.image_data.ptr, [width, height])

                    # Immediately transfer to system memory and clean up GPU
                    tile.transfer_to_system_memory()
                    # Force GPU synchronization after each tile to ensure cleanup
                    wp.synchronize()
                    gc.collect()  # Force garbage collection after each tile

                    # Explicitly clear reference to content pointer (Linux VRAM leak fix)
                    del content
                else:
                    # ByteImageProvider data has to be set right now otherwise buffer will be freed after this callback returns.
                    # Copy buffer to system memory for both display and serialization

                    # Store dimensions needed for serialization
                    tile.image_width = width
                    tile.image_height = height

                    # Extract and copy buffer data to system memory
                    # We need to copy the buffer contents before this callback returns
                    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
                    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
                    content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)

                    # Copy to system memory as bytearray for both display and serialization
                    tile._system_data = bytearray(content.contents)

                    # Set the image provider with our owned copy of the data
                    # This is safer than set_raw_bytes_data since we own the memory
                    tile.image_provider.set_bytes_data(tile._system_data, [width, height])

                    if settings.DEV_MODE:
                        tile_size = f"{round(tile.tile_width * desc.mpu)}x{round(tile.tile_height * desc.mpu)}m"
                        tile_center = (
                            f"({round(tile.tile_center[0] * desc.mpu)}, {round(tile.tile_center[1] * desc.mpu)})"
                        )
                        logger.warning(f"DEV: Captured tile #{desc.index}: {tile_size} at {tile_center}")

            schedule_capture = capture_viewport_to_buffer(viewport_api, on_viewport_captured)

            await schedule_capture.wait_for_result()

            # LINUX VRAM FIX: Immediately destroy viewport after capture to prevent memory leak
            # Note: Some AttributeErrors may occur in viewport widget's background threads during cleanup.
            # These are harmless race conditions in the viewport infrastructure and can be safely ignored.
        except Exception as e:
            # Always log tile capture errors, not just in DEV_MODE
            logger.error(f"Error during tile capture #{desc.index}: {e}")
            import traceback

            logger.error(traceback.format_exc())
        finally:
            # Immediate cleanup to prevent background thread errors and session layer contamination
            try:
                # Detach camera and destroy viewport
                if capture_vp and hasattr(capture_vp, "viewport_api") and capture_vp.viewport_api:
                    capture_vp.viewport_api.camera_path = ""
                if capture_vp:
                    try:
                        capture_vp.destroy()
                    except AttributeError as attr_err:
                        # Handle AttributeError from ExternalDragDrop cleanup race condition
                        # This is a known issue when OVC streaming (fixed in 109.0.1)
                        logger.error(f"Viewport cleanup failed (non-fatal): {attr_err}", exc_info=True)
                # Clean up references
                for ref in [capture_vp, cam, viewport_api]:
                    try:
                        if ref:
                            del ref
                    except:
                        pass
                await self._app.next_update_async()

                # Remove camera prim and spec from session layer
                if self._stage and session_layer:
                    with Usd.EditContext(self._stage, session_layer):
                        if self._stage.GetPrimAtPath(cam_path):
                            self._stage.RemovePrim(cam_path)
                    await self._app.next_update_async()
                    with Sdf.ChangeBlock():
                        if session_layer.GetPrimAtPath(cam_path):
                            session_layer.RemovePrimSpec(cam_path)
                    if settings.DEV_MODE:
                        carb.log_info(f"DEV: Removed camera prim/spec: {cam_path}")
            except Exception as e:
                logger.error(f"Error during camera cleanup: {e}", exc_info=True)

            # Remove persistent per-viewport overlay settings left by this capture viewport
            if vp_settings_base:
                for key in _VP_OVERLAY_KEYS:
                    self._settings.destroy_item(f"{vp_settings_base}/{key}")

            # Platform-specific cleanup after viewport destruction
            await self._post_viewport_cleanup()

        return tile
