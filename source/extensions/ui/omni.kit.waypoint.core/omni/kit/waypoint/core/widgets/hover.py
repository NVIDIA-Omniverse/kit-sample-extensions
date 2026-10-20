# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

import omni.kit.app
from omni import ui

from ..extension import get_instance
from ..model import WaypointItem


class WaypointItemHoverWidget:
    def __init__(self, item: WaypointItem, on_edit_begin_fn: callable = None):
        self._on_edit_begin_fn = on_edit_begin_fn
        self._waypoint_instance = get_instance()
        self._button_hovered = False
        self._build_ui(item)

    def destroy(self):
        self._waypoint_instance = None

    @property
    def visible(self) -> bool:
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._container.visible = value

    def _build_ui(self, item: WaypointItem) -> None:
        self._container = ui.HStack()
        with self._container:
            with ui.HStack():
                ui.Spacer()
                with ui.ZStack(width=24):
                    ui.Rectangle(
                        style_type_name_override="GridView.Hover.Frame", name=f"{item.waypoint.name} Hover Frame"
                    )
                    with ui.HStack(width=24):
                        ui.Spacer()
                        with ui.VStack(width=18):
                            ui.Spacer()
                            self._edit_button = ui.Button(
                                "",
                                width=18,
                                name="edit",
                                mouse_pressed_fn=lambda x, y, btn, a, item=item: self._on_edit(btn, item),
                                style_type_name_override="GridView.Hover.Button",
                                tooltip="Edit Waypoint",
                                mouse_hovered_fn=self._on_button_hovered,
                            )
                            ui.Spacer()
                            self._delete_button = ui.Button(
                                "",
                                width=18,
                                name="delete",
                                mouse_pressed_fn=lambda x, y, btn, a, item=item: self._on_remove(btn, item),
                                # mouse_hovered_fn=lambda hovered: self._on_apply_hover(hovered),
                                style_type_name_override="GridView.Hover.Button",
                                tooltip="Delete Waypoint",
                                mouse_hovered_fn=self._on_button_hovered,
                            )
                            ui.Spacer()
                        ui.Spacer()

    def _on_edit(self, btn: int, item: WaypointItem) -> None:
        if btn == 0:
            self._container.visible = False

            async def __begin_edit(item: WaypointItem):
                await omni.kit.app.get_app().next_update_async()
                if self._waypoint_instance.begin_edit_waypoint(item.waypoint):
                    if self._on_edit_begin_fn is not None:
                        self._on_edit_begin_fn(item)

            asyncio.ensure_future(__begin_edit(item))

    def _on_remove(self, btn: int, item: WaypointItem) -> None:
        if btn == 0:

            async def __delete(item: WaypointItem):
                await omni.kit.app.get_app().next_update_async()
                self._waypoint_instance.delete_waypoint(item.waypoint)

            asyncio.ensure_future(__delete(item))

    def _on_button_hovered(self, hovered: bool):
        self._button_hovered = hovered

    @property
    def button_hovered(self) -> bool:
        return self._button_hovered
