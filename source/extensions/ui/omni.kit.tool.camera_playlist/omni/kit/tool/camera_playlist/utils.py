# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Optional

import carb
import omni.usd
from omni.kit.widgets.custom import Singleton
from pxr import Usd, UsdGeom


def get_icon_path(icon_file):
    path = Path(__file__).parent
    count = 7
    while count > 0:
        if Path.exists(path.joinpath("icons")):
            return path.joinpath(f"icons/{icon_file}").as_posix()
        path = path.parent
        count = count - 1

    carb.log_error(f"Can not find icon path for {__file__}")
    return ""


@Singleton
class WaypointCheck(object):  # pragma: no cover -- this is no longer used
    """The singleton that checks if the waypoint is available."""

    def __init__(self):
        # Check if kit::IEditor is present, if not, we're in kit-mini
        try:
            import omni.kit.waypoint.core

            waypoint = omni.kit.waypoint.core.get_instance()
            self._has_waypoint = waypoint is not None
        except (ModuleNotFoundError, RuntimeError):
            self._has_waypoint = None

    @property
    def has_waypoint(self):
        return self._has_waypoint

    def is_waypoint_prim(self, prim_path):
        if self._has_waypoint:
            return omni.kit.waypoint.core.get_instance().is_waypoint_prim(prim_path)
        else:
            return False

    def get_waypoint(self, prim_path: str) -> Optional["ViewportWaypoint"]:
        if self._has_waypoint:
            return omni.kit.waypoint.core.get_instance().get_waypoint_from_prim_path(prim_path)
        else:
            return None

    def get_name(self, prim_path: str):
        if self._has_waypoint:
            waypoint = self.get_waypoint(prim_path)
            if waypoint:
                return waypoint.name
            else:
                return "(Unknown Waypoint)"
        else:
            return "(Unknown Waypoint)"

    def recall(self, name, without_camera=False):
        if self._has_waypoint:
            waypoint = omni.kit.waypoint.core.get_instance().get_waypoint(name)
            if waypoint:
                waypoint.recall(without_camera=without_camera)
            else:
                carb.log_error(f'[Playlist] Invalid waypoint "{name}". It may be renamed or deleted.')

    def clean(self, name, without_camera=False):
        if self._has_waypoint:
            waypoint = omni.kit.waypoint.core.get_instance().get_waypoint(name)
            if waypoint:
                waypoint.stop_recalling()
            else:
                carb.log_error(f'[Playlist] Invalid waypoint "{name}". It may be renamed or deleted.')
