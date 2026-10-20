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
from typing import Dict, List, Optional

import omni.kit.app
from omni import ui

from ..models import CategoryItem, ChildrenModelWrapper, SingleLevelWrapper
from .thumbnail_view import ThumbnailView


class OverviewView:
    """
    Represent an overview to show categories.
    Args:
        model (ChildrenModelWrapper): Model to show categories.
    """

    def __init__(self, model: ChildrenModelWrapper, **kwargs):
        self.model = model
        self.model.add_item_changed_fn(self._on_model_updated)

        self._overview_kwargs = kwargs
        self._thumbnail_size = kwargs.pop("thumbnail_size", 128)

        self._container = ui.VStack(spacing=0)
        self._sub_models: Dict[CategoryItem, ChildrenModelWrapper] = {}
        self._thumbnail_views: Dict[CategoryItem, ThumbnailView] = {}
        self._thumbnail_containers: Dict[CategoryItem, ui.HStack] = {}
        self._thumbnail_left_spacers: Dict[CategoryItem, ui.Spacer] = {}
        self._thumbnail_right_spacers: Dict[CategoryItem, ui.Spacer] = {}
        self._on_selection_changed_fn = None

        self._build_ui()

    def destroy(self):
        self._on_selection_changed_fn = None
        for item in self._thumbnail_views:
            self._thumbnail_views[item].destroy()

    @property
    def thumbnail_size(self) -> int:
        """Thumbnail size of detail item"""
        return self._thumbnail_size

    @thumbnail_size.setter
    def thumbnail_size(self, value: int) -> None:
        """Thumbnail size of detail item"""
        self._thumbnail_size = value
        for item in self._thumbnail_views:
            self._thumbnail_views[item].thumbnail_size = self._thumbnail_size

    def set_selection_changed_fn(self, on_selection_changed_fn) -> None:
        """
        Set function called when selection changed.
        Args:
            on_selection_changed_fn (callable): Function called when selection changed. Function signure:
                void on_selection_changed_fn(root: [CategoryItem], selection: List[DetailItem])
        """
        self._on_selection_changed_fn = on_selection_changed_fn

    def filter(self, filter_words: Optional[List[str]]) -> None:
        """
        Filter detail items.
        Args:
            filter_words: A string list to filter detail items. None means filtering nothing.
        """
        for item in self._thumbnail_views:
            self._thumbnail_views[item].filter(filter_words)

    def center(self, enable: bool):

        async def __center_async():
            while self._container.computed_width <= 0:
                await omni.kit.app.get_app().next_update_async()

            for item in self._thumbnail_views:
                if enable:
                    # Make grid H center
                    max_columns = int(self._container.computed_width / self._thumbnail_views[item].column_width)
                    spacer_width = (
                        self._container.computed_width - self._thumbnail_views[item].column_width * max_columns
                    ) / 2
                    self._thumbnail_left_spacers[item].width = ui.Pixel(spacer_width)
                    self._thumbnail_right_spacers[item].width = ui.Pixel(spacer_width)
                else:
                    self._thumbnail_left_spacers[item].width = ui.Pixel(0)
                    self._thumbnail_right_spacers[item].width = ui.Pixel(0)

        asyncio.ensure_future(__center_async())

    def _build_ui(self):
        self._container.clear()
        self._thumbnail_views.clear()

        with self._container:
            children: List[CategoryItem] = self.model.get_item_children(None)
            for child in children:
                self._sub_models[child] = ChildrenModelWrapper(self.model._source_model, child)
                with ui.CollapsableFrame(
                    child.name,
                    style_type_name_override="Overview.Frame",  # TODO: Strange that type name override does not work
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    build_header_fn=self._build_custom_header,
                ):
                    self._thumbnail_containers[child] = ui.HStack()
                    with self._thumbnail_containers[child]:
                        self._thumbnail_left_spacers[child] = ui.Spacer(width=0)
                        thumbnail_view = ThumbnailView(
                            self._sub_models[child], thumbnail_size=self._thumbnail_size, **self._overview_kwargs
                        )
                        thumbnail_view.set_selection_changed_fn(
                            lambda selection, category_item=child: self._on_selection_changed(category_item, selection)
                        )
                        self._thumbnail_views[child] = thumbnail_view
                        self._thumbnail_right_spacers[child] = ui.Spacer(width=0)

    def _on_model_updated(self, model, item):
        # model changed, rebuild ui
        self._build_ui()

    def _build_custom_header(self, collapsed: bool, title: str):
        if not title:
            # Do not show header is no title
            return

        if not collapsed:
            arrow_alignment = ui.Alignment.CENTER_BOTTOM
            arrow_width = 7
            arrow_height = 5
        else:
            arrow_alignment = ui.Alignment.RIGHT_CENTER
            arrow_width = 4
            arrow_height = 6

        with ui.HStack(height=40):
            with ui.VStack(width=15):
                ui.Spacer()
                ui.Triangle(
                    alignment=arrow_alignment,
                    width=arrow_width,
                    height=arrow_height,
                    style_type_name_override="Overview.Header.Arrow",
                )
                ui.Spacer()

            ui.Label(title.upper(), width=100, style_type_name_override="Overview.Header.Label")
            ui.Line(style_type_name_override="Overview.Header.Line")

    def _on_selection_changed(self, root: CategoryItem, selections: List[CategoryItem]):
        if len(selections) > 0:
            # Clear selections in other thumbnail views
            for item in self._thumbnail_views:
                if item != root:
                    self._thumbnail_views[item].selection = []

        if self._on_selection_changed_fn is not None:
            self._on_selection_changed_fn(root, selections)
