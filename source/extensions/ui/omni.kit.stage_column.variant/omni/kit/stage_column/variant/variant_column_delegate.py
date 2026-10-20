# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import re

import carb.settings
import omni.ui as ui
import omni.usd
from omni.kit.widget.stage import AbstractStageColumnDelegate, StageColumnItem
from pxr import Sdf, UsdGeom

from .variant_delegate import VariantSetsDelegate
from .variant_models import VariantSetTreeModel

SCROLLABLE_COUNT = 3
ITEM_HEIGHT = 22


class VariantColumnDelegate(AbstractStageColumnDelegate):
    """The column delegate that represents the visibility column"""

    def __init__(self):
        super().__init__()
        self._variant_sets_delegate = VariantSetsDelegate()

        self._settings = carb.settings.get_settings()
        self.style_data = {
            "TreeView": {
                "background_color": 0x0,
                "background_selected_color": 0x0,
                "secondary_color": 0x0,
            },
        }
        self.__variant_model = {}
        self.__handling_selection = False

        self.__stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(self._on_stage_event, name="VariantColumnDelegate stage update")
        )

        self.__last_selected_paths = None
        self.__refresh_item_selection()

    def __refresh_item_selection(self):
        selection = omni.usd.get_context().get_selection()
        selected_paths = selection.get_selected_prim_paths()
        if self.__last_selected_paths == selected_paths:
            return

        if self.__last_selected_paths:
            for path in self.__last_selected_paths:
                model = self.__variant_model.get(Sdf.Path(path), None)
                if model:
                    model.on_selection_changed()

        self.__last_selected_paths = selected_paths

        if selected_paths:
            for path in selected_paths:
                model = self.__variant_model.get(Sdf.Path(path), None)
                if model:
                    model.on_selection_changed()

    def _on_stage_event(self, event):
        """Called with subscription to pop"""
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self.__refresh_item_selection()

    def destroy(self):
        for model in self.__variant_model.values():
            model.destroy()
        self.__variant_model = {}
        self._variant_sets_delegate.destroy()
        self.__stage_event_sub = None

    @property
    def initial_width(self):
        """The width of the column"""
        return ui.Pixel(200)

    def build_header(self):
        """Build the header"""
        with ui.HStack():
            ui.Spacer(width=10)
            ui.Label("Variant", name="variant_header", style_type_name_override="TreeView.Header")

    async def build_widget(self, item: StageColumnItem):
        """Build the eye widget"""
        if not item or not item.stage:
            return

        prim = item.stage.GetPrimAtPath(item.path)
        if not prim or not prim.IsValid():
            return

        variant_sets = prim.GetVariantSets().GetNames()
        if not variant_sets:
            return

        self.__variant_model[Sdf.Path(item.path)] = VariantSetTreeModel(item.stage, item.path)

        def get_column_height(variant_sets):
            if len(variant_sets) >= SCROLLABLE_COUNT:
                return ITEM_HEIGHT * SCROLLABLE_COUNT
            return ITEM_HEIGHT * len(variant_sets)

        column_height = get_column_height(variant_sets)
        stack = ui.ZStack(height=column_height, style=self.style_data)
        stack.identifier = f"variant_zstack_{re.sub('[^0-9a-zA-Z]+', '_', item.path.pathString).lower()}"
        with stack:
            if len(variant_sets) >= SCROLLABLE_COUNT:
                frame = ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF)
            else:
                frame = ui.Frame()

            with frame:
                widths = [ui.Fraction(10), ui.Fraction(10)]
                tree_view = ui.TreeView(
                    self.__variant_model[item.path],
                    delegate=self._variant_sets_delegate,
                    root_visible=False,
                    header_visible=False,
                    column_widths=widths,
                )
                tree_view.set_selection_changed_fn(lambda s, t=tree_view: self._variant_set_selected(item.path, t))
            # Min size
            ui.Spacer(width=200)

    def _variant_set_selected(self, item_path, tree_view):
        """We should not be able to select variant set(s)"""
        if self.__handling_selection:
            return

        self.__handling_selection = True
        tree_view.clear_selection()

        # Select current item
        omni.usd.get_context().get_selection().set_selected_prim_paths([str(item_path)], True)
        self.__handling_selection = False
