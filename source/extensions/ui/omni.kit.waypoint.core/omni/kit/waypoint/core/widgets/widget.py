# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

from omni import ui
from omni.kit.browser.core import BrowserWidget

from ..model import WaypointModel
from ..style import WAYPOINT_BROWSER_WIDGET_STYLES
from .delegate import WaypointDelegate


class WaypointBrowserWidget(BrowserWidget):
    """
    Represent waypoint browser widget.
    """

    def __init__(
        self,
        model: Optional[WaypointModel] = None,
        delegate: Optional[WaypointDelegate] = None,
        max_thumbnail_size: int = 320,
        on_waypoint_selection_changed: callable = None,
    ):
        self._model = model or WaypointModel()
        self._delegate = delegate or WaypointDelegate(model)

        super().__init__(
            self._model,
            detail_delegate=self._delegate,
            min_thumbnail_size=160,
            max_thumbnail_size=max_thumbnail_size,
            detail_thumbnail_size=160,
            thumbnail_aspect=16.0 / 9.0,
            style=WAYPOINT_BROWSER_WIDGET_STYLES,
        )

        self.show_widgets(collection=False, category=False)
        self.collection_index = 0
        if self._detail_view:
            self._detail_view.set_selection_changed_fn(on_waypoint_selection_changed)
        if self._detail_scrolling_frame:
            self._detail_scrolling_frame.vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED

    def destroy(self) -> None:
        """Destroys widget resources by calling the parent destroy method, resetting the detail view selection callback if present, and destroying the associated model and delegate."""
        super().destroy()
        if self._detail_view:
            self._detail_view.set_selection_changed_fn(None)
        self._model.destroy()
        self._delegate.destroy()
