# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.kit.playlist.core import SystemPlaylistModel
from omni.kit.waypoint.core import ViewportWaypoint, WaypointCard, WaypointChangeCallbacks, WaypointModel
from omni.kit.waypoint.core import get_instance as get_waypoint_instance


class AllWaypointPlaylistModel(SystemPlaylistModel):
    def __init__(self):
        super().__init__("All Waypoints", WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT)

        self._waypoint_instance = get_waypoint_instance()
        self._ext_callback = WaypointChangeCallbacks(
            on_waypoint_created=self._on_waypoint_changed,
            on_waypoint_deleted=self._on_waypoint_changed,
            on_waypoint_changed=self._on_waypoint_changed,
        )
        self._waypoint_instance.register_callback(self._ext_callback)

        self.check_update()

    def destroy(self):
        self._waypoint_instance.deregister_callback(self._ext_callback)
        self._waypoint_instance = None

    def check_update(self):
        self.clear()

        # Get all waypoints
        self._children = []
        self._waypoints = self._waypoint_instance.get_waypoints()
        for waypoint in self._waypoints:
            card = WaypointCard(WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT, waypoint.camera_prim.GetPath().pathString)
            self.insert_item(card, notify=False)

    def _on_waypoint_changed(self, waypoint: ViewportWaypoint) -> None:
        if waypoint:
            self.check_update()
            self._item_changed(None)
