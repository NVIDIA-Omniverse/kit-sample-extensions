# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Dict, Optional

import carb.settings
from omni import ui
from omni.kit.browser.core import DetailDelegate

from ..extension import SETTINGS_WAYPOINT_EDITING
from ..extension import get_instance as get_waypoint_instance
from ..model import WaypointItem, WaypointModel
from ..viewport_waypoint import ViewportWaypoint
from .edit import WaypointItemEditWidget
from .hover import WaypointItemHoverWidget


class WaypointDelegate(DetailDelegate):
    """
    Represent to show detail for a waypoint in stage.
    Args:
        stage_model (WaypointModel): waypoint model.
    """

    def __init__(self, model: WaypointModel):
        self._waypoint_instance = get_waypoint_instance()
        self._hover_widgets: Dict[WaypointItem, WaypointItemHoverWidget] = {}
        self._edit_widgets: Dict[WaypointItem, WaypointItemEditWidget] = {}
        self._selection_widgets: Dict[WaypointItem, ui.Widget] = {}

        self._settings = carb.settings.get_settings()
        self._editing_waypoint_name = self._settings.get(SETTINGS_WAYPOINT_EDITING)
        self._editing_waypoint_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_WAYPOINT_EDITING, self._on_waypoint_editing_changed
        )
        super().__init__(model)

    def destroy(self) -> None:
        """Destroys the WaypointDelegate object by cleaning up hover, edit, and selection widgets, and resetting internal state.

        Calls destroy on child widgets and clears internal collections.
        """
        self._waypoint_instance = None
        for widget in self._hover_widgets.values():
            widget.destroy()
        self._hover_widgets.clear()
        for widget in self._edit_widgets.values():
            widget.destroy()
        self._edit_widgets.clear()
        self._selection_widgets.clear()
        super().destroy()

    def get_label(self, item: WaypointItem) -> str:
        """Returns the label for a given waypoint item.

        Args:
            item (WaypointItem): Waypoint item to retrieve the label from.

        Returns:
            str: The name of the waypoint item.
        """
        return item.name

    def on_right_click(self, item: WaypointItem) -> None:
        """Handles a right click event on a waypoint item.

        Args:
            item (WaypointItem): Waypoint item that received the right click event.

        Do nothing if in edit state. Otherwise, disables hover widget and displays context menu.
        """
        if self._edit_widgets[item].visible:
            return

        self._hover_widgets[item].visible = False

        self.show_context_menu(item)

    def on_click(self, item: WaypointItem) -> None:
        """Processes a click event on a waypoint item by delegating to the parent implementation.

        Args:
            item (WaypointItem): Waypoint item that was clicked.
        """
        super().on_click(item)

    def on_hover(self, item: WaypointItem, hovered: bool) -> None:
        """Handles a hover event on a waypoint item.

        Args:
            item (WaypointItem): Waypoint item that is being hovered.
            hovered (bool): Hover state; True if pointer is over the item.

        Toggles the hover widget's visibility if not in edit state.
        """
        if not self._edit_widgets[item].visible:
            self._hover_widgets[item].visible = hovered

    def build_thumbnail(self, item: WaypointItem) -> Optional[ui.Image]:
        """Builds a thumbnail image for a waypoint item along with associated hover, edit, and selection widgets.

        Args:
            item (WaypointItem): Waypoint item to build the thumbnail for.

        Constructs a stack of UI elements for the thumbnail and sets up hover and edit widgets. Updates edit widget visibility based on the current editing state.

        Returns:
            Optional[ui.Image]: The generated thumbnail image widget.
        """
        with ui.ZStack():
            with ui.HStack():
                image = ui.ImageWithProvider(
                    item.thumbnail_provider,
                    alignment=ui.Alignment.CENTER,
                    fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                    style_type_name_override="GridView.Image",
                )

            self._build_hover_widget(item)
            self._build_edit_widget(item)
            self._selection_widgets[item] = ui.Rectangle(style_type_name_override="GridView.Item.Selection")

        if len(self._editing_waypoint_name) > 0 and item.waypoint.name == self._editing_waypoint_name:
            self._show_editing(item, True)
        return image

    def show_context_menu(self, item: WaypointItem) -> None:
        """Displays the context menu for a given waypoint item.

        Args:
            item (WaypointItem): Waypoint item for which the context menu should be shown.
        """
        pass

    def _on_edit_begin(self, item: WaypointItem) -> None:
        # Widgets status controller by _on_waypoint_editing_changed
        pass

    def _on_edit_end(self, item: WaypointItem) -> None:
        # Widgets status controller by _on_waypoint_editing_changed
        pass

    def _build_hover_widget(self, item: WaypointItem):
        # Toolbar when item hovered
        self._hover_widgets[item] = WaypointItemHoverWidget(item, on_edit_begin_fn=self._on_edit_begin)
        self._hover_widgets[item].visible = False

    def _build_edit_widget(self, item: WaypointItem):
        # Widget when item in editing
        self._edit_widgets[item] = WaypointItemEditWidget(item, on_edit_end_fn=self._on_edit_end)
        self._edit_widgets[item].visible = False

    def _on_waypoint_editing_changed(self, item, event_type) -> None:
        self._editing_waypoint_name = self._settings.get(SETTINGS_WAYPOINT_EDITING)
        if self._editing_waypoint_name:
            # In editing
            for waypoint_item in self._edit_widgets:
                if waypoint_item.waypoint.name == self._editing_waypoint_name:
                    self._show_editing(waypoint_item, True)
        else:
            # Edit done
            for waypoint_item in self._edit_widgets:
                if self._edit_widgets[waypoint_item].visible:
                    self._show_editing(waypoint_item, False)

    def _show_editing(self, item: WaypointItem, visible: bool):
        self._edit_widgets[item].visible = visible
        self._selection_widgets[item].checked = visible
