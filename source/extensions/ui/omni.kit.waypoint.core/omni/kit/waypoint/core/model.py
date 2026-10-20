# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Dict, List

from omni import ui
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem

from . import ViewportWaypoint, WaypointChangeCallbacks
from . import get_instance as get_waypoint_instance


class WaypointItem(DetailItem):
    """
    Represent a detail item for a waypoint in a stage.
    Args:
        waypoint (ViewportWaypoint): Waypoint object.
    """

    def __init__(self, waypoint: ViewportWaypoint):
        self.waypoint = waypoint

        self.thumbnail_provider = ui.ByteImageProvider()
        thumbnail_data = waypoint.thumbnail_data
        if thumbnail_data is not None:
            byte_data, width, height = thumbnail_data
            if byte_data and width > 0 and height > 0:
                self.thumbnail_provider.set_bytes_data(bytearray(byte_data), [width, height])

        super().__init__(waypoint.name, waypoint.path, None)


class WaypointModel(AbstractBrowserModel):
    """
    Represent waypoints in opened stage.

    Args:
        on_waypoint_changed_fn: Callback when waypoint created/deleted/changed. Function signaure::

            def on_waypoint_changed_fn() -> None
    """

    def __init__(self, on_waypoint_changed_fn: callable = None):
        self._on_waypoint_changed_fn = on_waypoint_changed_fn
        self._waypoint_instance = get_waypoint_instance()
        self._waypoints: List[ViewportWaypoint] = []
        self._cached_detail_items: Dict[str, WaypointItem] = {}
        self._collection_item = CollectionItem("Stage", "stage")

        self._waypoint_callback = WaypointChangeCallbacks(
            self.on_waypoint_changed, self.on_waypoint_changed, self.on_waypoint_changed, self.on_waypoint_changed
        )
        self._waypoint_instance.register_callback(self._waypoint_callback)

        super().__init__()

    def destroy(self) -> None:
        """Deregister the waypoint callback and clear the waypoint instance."""
        self._waypoint_instance.deregister_callback(self._waypoint_callback)
        self._waypoint_instance = None

    def execute(self, item: WaypointItem) -> None:
        """Recall a waypoint.

        Args:
            item (WaypointItem): WaypointItem to recall.
        """
        self._waypoint_instance.recall_waypoint(item.waypoint)

    def get_collection_items(self) -> List[CollectionItem]:
        """Return a list containing the collection item for stage.

        Returns:
            List[CollectionItem]: List with a single stage collection item.
        """
        return [self._collection_item]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        """Fetch category items for stage based on the provided collection item. Updates the waypoint list and returns a category item with count equal to the number of waypoints.

        Args:
            item (CollectionItem): Collection item to obtain category items for.

        Returns:
            List[CategoryItem]: List containing a single category item for stage.
        """
        self._waypoints = self._waypoint_instance.get_waypoints()
        count = len(self._waypoints) if self._waypoints else 0
        return [CategoryItem("Stage", count)]

    def get_detail_items(self, item: CategoryItem) -> List[WaypointItem]:
        """Generate and return a sorted list of detail items for each waypoint. Caches detail items before sorting by name.

        Args:
            item (CategoryItem): Category item to obtain detail items for.

        Returns:
            List[WaypointItem]: Sorted list of waypoint detail items.
        """
        detail_items = []
        self._cached_detail_items = {}
        if self._waypoints:
            for waypoint in self._waypoints:
                self._cached_detail_items[waypoint] = WaypointItem(waypoint)
                detail_items.append(self._cached_detail_items[waypoint])
            detail_items.sort(key=lambda item: item.name)

        return detail_items

    def on_waypoint_changed(self, *_) -> None:
        """Handle waypoint change events by updating the collection item and invoking an external callback if set."""
        self._item_changed(self._collection_item)
        if self._on_waypoint_changed_fn is not None:
            self._on_waypoint_changed_fn()
