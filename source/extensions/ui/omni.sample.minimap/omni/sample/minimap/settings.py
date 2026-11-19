# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = [
    "IoHelper",
    "S_PATH",
    "MULTI_LEVEL_SUPPORT",
    "DUMP_GPU",
    "GPU_CLEANUP_INTERVAL",
    "R_SHADOWS",
    "R_GRID",
    "DEV_MODE",
]

import os
import posixpath
import subprocess
import sys
from pathlib import Path

import carb.settings
import omni.kit.app

# Settings path prefixes for carb.settings storage
EXTPATH = "/exts/omni.sample.minimap"  # Base path for session settings (non-persistent)
PERSIST = "/persistent" + EXTPATH  # Base path for persistent settings (saved between sessions)

# Feature flags
MULTI_LEVEL_SUPPORT = False  # Enable multi-level/multi-floor support (experimental)
DUMP_GPU = False  # trigger GPU memory release after all tiles are built (experimental)
GPU_CLEANUP_INTERVAL = 3  # Clean GPU memory every N tiles (1=slowest/safest, higher=faster but more VRAM)

# Render Overrides
R_SHADOWS = False  # Render shadows during minimap generation (False = cleaner output)
R_GRID = False  # Render grid during minimap generation (False = cleaner output)


class IoHelper:
    @staticmethod
    def get_extension_path(append: str = None) -> str:
        """Get extension directory path."""
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = manager.get_extension_id_by_module(__name__)
        out_path = manager.get_extension_path(ext_id)
        if append is not None:
            out_path = posixpath.join(out_path, append)
        return out_path

    @staticmethod
    def open_path(url: str):
        """Open path in system file browser."""
        if not os.path.exists(url):
            url = Path(url).parent
        if not os.path.exists(url):
            return
        if sys.platform == "win32":
            os.startfile(os.normpath(url))
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, url])


class S_PATH:
    """Settings paths for minimap configuration - using carb.settings storage."""

    # Persistent settings (saved between sessions)
    OPEN_ON_STARTUP = f"{PERSIST}/openOnStartup"  # Show minimap window on application startup

    # Session settings (reset on restart)
    CAPTURE_ON_STAGE_OPENED = f"{EXTPATH}/captureOnStageOpen"  # Auto-generate minimap when stage opens
    JOB_LIMIT = f"{EXTPATH}/jobLimit"  # Maximum concurrent tile generation jobs (1-8)
    DEFAULT_FLOOR = f"{EXTPATH}/defaultFloor"  # Default floor height in meters for new minimaps
    DEFAULT_CEILING = f"{EXTPATH}/defaultCeiling"  # Default ceiling height in meters for new minimaps
    POLLING_THROTTLE = f"{EXTPATH}/pollingThrottle"  # Camera position polling interval in seconds
    WAYPOINT_THROTTLE = f"{EXTPATH}/waypointThrottle"  # Waypoint/markup visibility check interval in seconds
    MAX_TILES = f"{EXTPATH}/maxTiles"  # Maximum number of tiles allowed for generation
    MAX_TILE_SIZE = f"{EXTPATH}/maxTileSize"  # Maximum tile size in meters allowed for generation
    DEFAULT_TILE_SIZE = f"{EXTPATH}/defaultTileSize"  # Default tile size in meters for new minimaps
    BUILD_DELAY = f"{EXTPATH}/buildDelay"  # Delay in seconds before starting tile generation
    RESOLUTION = f"{EXTPATH}/resolution"  # Tile render resolution (pixels per tile edge)
    CAM_ZOOM = f"{EXTPATH}/camZoom"  # Camera zoom level for minimap view
    VIEW_CENTER = f"{EXTPATH}/viewCenter"  # Minimap view center position (serialized)
    ROTATE_ACTOR = f"{EXTPATH}/rotateActor"  # Lock/unlock view mode (True=locked, False=unlocked)
    SHOW_SETTINGS = f"{EXTPATH}/showSettings"  # Whether settings panel is visible
    FLOOR = f"{EXTPATH}/floor"  # Current floor height for active minimap
    CEILING = f"{EXTPATH}/ceiling"  # Current ceiling height for active minimap
    CAM_SIZE = f"{EXTPATH}/camSize"  # Camera FOV indicator size multiplier
    DEV_MODE = f"{EXTPATH}/devMode"  # Developer mode for performance monitoring
    NUM_TILES = f"{EXTPATH}/numTiles"  # Current number of tiles in active minimap
    BOUNDS = f"{EXTPATH}/bounds"  # Current minimap bounds (serialized string)
    TILE_SIZE = f"{EXTPATH}/tileSize"  # Current tile size for active minimap


# DEV_MODE - Development logging switch (single source of truth from carb.settings)
# Always reads from carb.settings to ensure consistency
# Can be toggled at runtime via UI - all code sees the same value
# Make DEV_MODE accessible as settings.DEV_MODE (reads from carb on each access)
class _DevModeAccessor:
    """Helper class to make DEV_MODE read from carb.settings on every access."""

    def __bool__(self):
        return carb.settings.get_settings().get(S_PATH.DEV_MODE) or False

    def __repr__(self):
        return str(bool(self))


DEV_MODE = _DevModeAccessor()
