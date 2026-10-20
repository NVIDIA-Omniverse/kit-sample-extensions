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
from omni.kit.playlist.core import PlaylistCard
from pxr import Usd

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


class WaypointCard(PlaylistCard):
    """A class for displaying a waypoint as a playlist card in omni.kit.waypoint.core. This class retrieves the waypoint from the WAYPOINT_EXTENSION_INSTANCE using the provided prim path and sets the card name and path based on the actual waypoint data. It exposes properties for menu text, the camera prim reference, and the icon file location. The active method recalls the waypoint to make it current, while the clean method is an alias that triggers the active method.

    Args:
        type (str): A string denoting the card type for the waypoint.
        path (str): A file path or identifier used to locate the waypoint prim.
        name (str): A user-friendly name for the waypoint. If the waypoint does not exist, a default label is assigned.
    """

    PLAYLIST_CARD_TYPE_WAYPOINT = "waypoint"
    """str: Identifies the waypoint playlist card type."""
    WAYPOINT_EXTENSION_INSTANCE = None
    """object: Holds the waypoint extension instance for operations."""

    # Waypoint playlist card
    def __init__(self, type: str, path: str, name: str = None):
        super().__init__(type, path, name=name)

        self._waypoint = WaypointCard.WAYPOINT_EXTENSION_INSTANCE.get_waypoint_from_prim_path(self.path)
        self.name = self._waypoint.name if self._waypoint else "(Unknown Waypoint)"
        self.path = self._waypoint.path if self._waypoint else self.path

    @classmethod
    def accept(cls, camera_path: str) -> bool:
        """Determines whether the provided camera_path corresponds to a waypoint prim using the waypoint extension instance.

        Args:
            camera_path (str): The camera path to verify as a waypoint prim.

        Returns:
            bool: True if camera_path is a waypoint prim; otherwise, False.
        """
        return WaypointCard.WAYPOINT_EXTENSION_INSTANCE.is_waypoint_prim(camera_path)

    @property
    def menu_text(self) -> str:
        """Gets the menu text label for the waypoint card.

        Returns:
            str: The displayed menu text.
        """
        return "Waypoints"

    @property
    def camera_prim(self):
        """Gets the camera prim associated with the waypoint if it exists.

        Returns:
            object: The camera prim or None if not available.
        """
        if self._waypoint is None:
            return None
        else:
            return self._waypoint.camera_prim

    @property
    def icon(self):
        """Gets the file path for the waypoint icon.

        Returns:
            str: The icon file path string.
        """
        return f"{ICON_PATH}/Waypoint_Light.svg"

    def active(self, without_camera=False):
        """Activates the corresponding waypoint by invoking recall_waypoint on the waypoint extension instance. Logs an error if the waypoint is not found.

        Args:
            without_camera (bool): Flag to recall the waypoint without the camera if True.
        """
        waypoint = WaypointCard.WAYPOINT_EXTENSION_INSTANCE.get_waypoint(self.name)
        if waypoint:
            # Use recall_waypoint instead of waypoint.recall to set active waypoint
            # When playing, first recall without camera, next recall to set camera
            # Here use force=True to make sure second recall work
            WaypointCard.WAYPOINT_EXTENSION_INSTANCE.recall_waypoint(
                waypoint, without_camera=without_camera, force=True, recall_timeline=False
            )
        else:
            carb.log_error(f'[Playlist] Invalid waypoint "{self.name}". It may be renamed or deleted.')

    def clean(self, without_camera=False):
        """Activates the waypoint by calling active with the specified without_camera flag.

        Args:
            without_camera (bool): Flag to activate the waypoint without the camera if True.
        """
        self.active(without_camera=without_camera)
