# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional, Union

import omni.ext
from omni.kit.playlist.core import PlayManager, PlayMode
from omni.kit.waypoint.core import ViewportWaypoint

from .play_control import PlayControl
from .playlist_model import AllWaypointPlaylistModel

_extension_instance = None


class WaypointPlaylistExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._waypoint_playlist = WaypointPlaylist()
        self._waypoint_playlist.on_startup(ext_id)

    def on_shutdown(self):
        self._waypoint_playlist.on_shutdown()


class WaypointPlaylist:
    def on_startup(self, ext_id):
        self.__waypoint_playlist_model = AllWaypointPlaylistModel()
        self.__play_control = PlayControl(self.__waypoint_playlist_model)
        self.__play_manager: Optional[PlayManager] = None
        self.__navigation_model: Optional[AllWaypointPlaylistModel] = None

        try:
            from omni.kit.tool.camera_playlist import PlaylistManager

            PlaylistManager.get_instance().register(self.__waypoint_playlist_model)
        except ImportError:
            pass

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        try:
            from omni.kit.tool.camera_playlist import PlaylistManager

            PlaylistManager.get_instance().deregister(self.__waypoint_playlist_model)
        except ImportError:
            pass

        if self.__play_manager:
            self.__play_manager.destroy()
            self.__play_manager = None
        if self.__navigation_model:
            self.__navigation_model.destroy()
            self.__navigation_model = None
        self.__play_control.destroy()
        self.__waypoint_playlist_model.destroy()

        global _extension_instance
        _extension_instance = None

    def navigate(self, waypoint: Union[str, ViewportWaypoint], transition_time: Optional[float] = 5) -> None:
        """
        Smooth navigate to waypoint.

        Args:
            waypoint (Union[str, ViewportWaypoint]): Waypoint to navigate.
            transition_time (float): Transition time for navigation, in seconds.
        """
        if self.__navigation_model is None:
            self.__navigation_model = AllWaypointPlaylistModel()
            self.__navigation_model.transition_type = PlayMode.TRANSITION_SMOOTH
        if self.__play_manager is None:
            self.__play_mananger = PlayManager(self.__navigation_model)

        name = waypoint.name if isinstance(waypoint, ViewportWaypoint) else waypoint
        items = self.__navigation_model.get_item_children()
        for item in items:
            if item.data.name == name:
                if transition_time > 0:
                    self.__navigation_model.transition_time = transition_time
                self.__play_mananger.navigate(item=item)


def get_instance():
    global _extension_instance
    return _extension_instance
