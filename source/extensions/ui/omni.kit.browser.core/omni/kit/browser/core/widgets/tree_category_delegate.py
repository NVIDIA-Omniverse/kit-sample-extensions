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
from functools import partial
from itertools import chain
from typing import List

import omni.kit.app
from omni import ui
from omni.ui import scene as sc

from ..models import CategoryItem
from . import CategoryDelegate
from .style import FULL_LINE_HEIGHT


class VLine(ui.Line):
    def __init__(self, half: bool = False):
        return super().__init__(
            height=FULL_LINE_HEIGHT / 2 if half else FULL_LINE_HEIGHT,
            width=0,
            alignment=ui.Alignment.LEFT,
            style_type_name_override="TreeView.Branch.Line",
        )


class TreeCategoryDelegate(CategoryDelegate):
    """
    Delegate to represent category items in a hierarchical structure.

    Kwargs:
        hide_zero_count (bool): Hide category count if count is 0. Default False.
    """

    def __init__(self, hide_zero_count: bool = False, *args, **kwargs):
        self.__hide_zero_count = hide_zero_count
        self._transform = {}
        self._rotate_future = {}
        super().__init__(*args, **kwargs)

    def destroy(self) -> None:
        """
        Stop every spinner this delegate started.

        _rotate never returns, so a row that leaves the tree while loading keeps waking the app
        every frame for the life of the process: build_widget only cancels the rotation of the item
        it is rebuilding, which a removed row never is.
        """
        for future in self._rotate_future.values():
            if future is not None:
                future.cancel()
        self._rotate_future.clear()
        self._transform.clear()

    def _prune_rows(self, live_items) -> None:
        """
        Stop the spinner of any row that has left the tree. Called by the widget that owns the tree.

        destroy() covers the widget closing, and build_widget covers a row being rebuilt, but a
        loading row that simply disappears - its collection removed, or filtered out of the tree -
        is neither. Nothing would rebuild it, so its rotation would go on waking the app every
        frame until the browser closed.
        """
        live = set(live_items)
        for item in [item for item in self._rotate_future if item not in live]:
            future = self._rotate_future.pop(item, None)
            if future is not None:
                future.cancel()
            self._transform.pop(item, None)

    def build_widget(
        self, model: ui.AbstractItemModel, item: CategoryItem, index: int = 0, level: int = 0, expanded: bool = False
    ):
        """Create a widget per category item

        Args:
            model (ui.AbstractItemModel): Category data model.
            item (CategoryItem): Category item.
            index (int): ignore.
            level (int): ignore.
            expanded (bool): ignore.
        """
        with ui.HStack(mouse_pressed_fn=partial(self._on_category_item_click, item)):
            ui.Label(
                self.get_label(item), alignment=ui.Alignment.LEFT_CENTER, style_type_name_override="TreeView.Item.Name"
            )

            show_count = True
            if self.__hide_zero_count:
                try:
                    count = int(self.get_count(item))
                    show_count = count > 0
                except:
                    pass

            if item.loading:
                ui.Spacer()
                with ui.ZStack(width=FULL_LINE_HEIGHT, height=FULL_LINE_HEIGHT):
                    with sc.SceneView(width=FULL_LINE_HEIGHT, height=FULL_LINE_HEIGHT).scene:
                        self._transform[item] = sc.Transform()
                        with self._transform[item]:
                            sc.Image("${omni.kit.browser.core}/icons/omni_logo_24.png", width=2.0, height=2.0)
                    # On top of the spinner, and empty unless a subclass wants something there.
                    self.build_loading_overlay(item)

                async def _rotate():
                    angle = [0]
                    while True:
                        delta = await omni.kit.app.get_app().next_update_async()
                        angle[0] -= delta * 1.5
                        transform = sc.Matrix44.get_rotation_matrix(0, 0, angle[0])
                        self._transform[item].transform = transform

                # Stop the previous one first. _rotate never returns, so overwriting the handle
                # leaks a coroutine that wakes every frame for the life of the app - and a loading
                # row is rebuilt every time its collection reports progress: 3 became 98 in 41 s.
                previous = self._rotate_future.get(item)
                if previous is not None and not previous.done():
                    previous.cancel()
                self._rotate_future[item] = asyncio.ensure_future(_rotate())
            else:
                if item in self._rotate_future and self._rotate_future[item]:
                    self._rotate_future[item].cancel()
                    self._rotate_future[item] = None
                if show_count:
                    ui.Label(
                        f"{self.get_count(item)}",
                        alignment=ui.Alignment.RIGHT_CENTER,
                        style_type_name_override="TreeView.Item.Count",
                    )

        return

    def build_branch(
        self,
        model: ui.AbstractItemModel,
        item: CategoryItem,
        column_id: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """Create a branch widget that opens or closes subtree

        Args:
            model (ui.AbstractItemModel): Category data model.
            item (CategoryItem): Category item.
            column_id (int): ignore.
            level (int): Level of the hierarchy the current item is at, from 0 to n.
            expanded (bool): Indicates whether child categories are displayed expanded.
        """
        with ui.HStack(height=FULL_LINE_HEIGHT, spacing=0):
            ui.Spacer(width=5)  # Extra left margin for all

            if not item.children:
                ui.Spacer(width=2)
                if level == 0 and item.name.upper() == "ALL":  # No decoration for ALL root
                    return

                if level == 0:
                    # Just a simple dot
                    ui.Circle(
                        width=4, alignment=ui.Alignment.RIGHT_CENTER, style_type_name_override="TreeView.Branch.Line"
                    )
                    ui.Spacer(width=8)
                    return

                ui.Spacer(width=3)
                if level > 1:
                    for i in range(1, level):
                        # OM-83328: Always show line here
                        VLine()
                        ui.Spacer(width=15)

                with ui.ZStack():
                    # vertical line
                    with ui.HStack():
                        if not item.is_last_child:
                            # Full vertical line
                            VLine()
                        else:
                            # Half vertical line for L-shaped branch
                            with ui.VStack():
                                VLine(half=True)
                                ui.Spacer(height=6)
                        ui.Spacer()

                    # horiz line
                    ui.Line(width=16, style_type_name_override="TreeView.Branch.Line")

                    # dot
                    with ui.HStack():
                        ui.Spacer()
                        ui.Circle(
                            width=4,
                            alignment=ui.Alignment.RIGHT_CENTER,
                            style_type_name_override="TreeView.Branch.Line",
                        )

                ui.Spacer(width=10)  # more space after dot than +/-

            else:
                if level > 0:
                    item.children[-1].is_last_child = True

                    ui.Spacer(width=5)
                    for i in range(0, level):
                        # OM-83328: Always show line here
                        VLine()
                        if i != level - 1:
                            ui.Spacer(width=15)
                    ui.Spacer(width=10)

                self.draw_expanded_symbol(expanded)

    def draw_expanded_symbol(self, expanded: bool) -> None:
        """Draw the symbol indicating the expanded state for a category item.

        Args:
            expanded (bool): Flag indicating if the category item is expanded.
        """
        if expanded:
            # Minus sign
            with ui.VStack(width=8):
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer(width=2)
                    ui.Line(width=7, style_type_name_override="TreeView.Item")
                ui.Spacer()
        else:
            # Plus sign
            with ui.ZStack(width=8):
                # horiz line
                with ui.VStack(width=8):
                    ui.Spacer()
                    with ui.HStack():
                        ui.Spacer(width=2)
                        ui.Line(width=7, style_type_name_override="TreeView.Item")
                    ui.Spacer()
                # vertical line
                with ui.HStack():
                    ui.Spacer(width=1)
                    ui.Spacer()
                    with ui.VStack():
                        ui.Spacer(height=0.1)
                        ui.Spacer()
                        ui.Line(height=7, alignment=ui.Alignment.H_CENTER, style_type_name_override="TreeView.Item")
                        ui.Spacer()
                    ui.Spacer()
        ui.Spacer(width=5)

    def get_label(self, item: CategoryItem) -> str:
        """Return the label for a CategoryItem by splitting the item name and taking the last segment in uppercase.

        Args:
            item (CategoryItem): Category item.

        Returns:
            str: The processed label string.
        """
        return item.name.upper().split("/")[-1]

    def _on_category_item_click(self, item: CategoryItem, x, y, button, key_mod):
        if button == 1:
            self._on_item_right_click(item)

    def _on_item_right_click(self, item: CategoryItem):
        pass

    # ------------------------------------------------------------------ loading spinner hooks --
    # A delegate that has something to say about work in progress overrides these. They default to
    # inert so every existing browser keeps a spinner that is an indicator and nothing more.

    def build_loading_overlay(self, item: CategoryItem) -> None:
        """
        Build whatever belongs on top of a loading row's spinner. Nothing, by default.

        Called inside the spinner's own stack, so anything built here covers it and takes the input
        the row would otherwise get. A delegate that wants the spinner to do something - report what
        a scan is doing, open a window - builds it here; one that does not leaves the spinner the
        plain indicator it has always been, and a click over it selects the row.

        Called on every row build, and a loading row is rebuilt whenever its collection reports
        progress, so keep it cheap.
        """
        return
