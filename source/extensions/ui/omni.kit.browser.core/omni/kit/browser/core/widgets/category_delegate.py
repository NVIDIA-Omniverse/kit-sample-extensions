# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui

from ..models import CategoryItem


class CategoryDelegate(ui.AbstractItemDelegate):
    """
    Delegate to represent category item.
    Args:
        teee_mode: Show categories in tree mode. Default flat mode (no branches)
    """

    def __init__(self, tree_mode: bool = False):
        self._tree_mode = tree_mode
        super().__init__()

    def build_widget(
        self, model: ui.AbstractItemModel, item: CategoryItem, index: int = 0, level: int = 0, expanded: bool = False
    ):
        """Creates a widget for a category item in either tree or list view. In tree mode, if the item has children, a branch label is displayed; otherwise, a widget with spacer, label, and count is constructed.

        Args:
            model (ui.AbstractItemModel): Category data model.
            item (CategoryItem): Category item.
            index (int): Ignored parameter.
            level (int): Ignored parameter for tree indentation spacing.
            expanded (bool): Ignored parameter for expansion state.
        """
        if self._tree_mode and len(item.children) > 0:
            # In tree mode, if have children, show as branch
            ui.Label(
                self.get_label(item), alignment=ui.Alignment.LEFT_CENTER, style_type_name_override="TreeView.Item.Name"
            )
            return

        count = self.get_count(item)

        with ui.HStack(height=20):
            if self._tree_mode:
                ui.Label("  " * level, width=0)
            ui.Spacer(width=6)
            if not self._tree_mode:
                with ui.VStack(width=6):
                    ui.Spacer()
                    ui.Line(height=10, alignment=ui.Alignment.LEFT, style_type_name_override="TreeView.Mark")
                    ui.Spacer()
            ui.Label(
                self.get_label(item), alignment=ui.Alignment.LEFT_CENTER, style_type_name_override="TreeView.Item.Name"
            )

            if not self._tree_mode:
                ui.Label(
                    str(count),
                    width=10,
                    alignment=ui.Alignment.RIGHT_CENTER,
                    style_type_name_override="TreeView.Item.Count",
                )

    def build_branch(
        self,
        model: ui.AbstractItemModel,
        item: CategoryItem,
        column_id: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """Creates a branch widget that toggles subtree display. In tree mode, if the item has children, displays an indented +/- sign based on expansion state. If not in tree mode or no children, no branch is created.

        Args:
            model (ui.AbstractItemModel): Category data model.
            item (CategoryItem): Category item.
            column_id (int): Ignored parameter.
            level (int): Ignored parameter for tree indentation spacing.
            expanded (bool): Determines branch sign; True shows '-' and False shows '+'.
        """
        if not self._tree_mode or len(item.children) == 0:
            # In tree mode, if have children, show as branch
            return

        with ui.HStack(height=20, spacing=5):
            ui.Label("  " * level, width=0)
            if expanded:
                ui.Label("- ", width=5)
            else:
                ui.Label("+ ", width=5)

    def get_label(self, item: CategoryItem) -> str:
        """Returns the name label of a category item.

        Args:
            item (CategoryItem): Category item object.

        Returns:
            str: Name of the category item.
        """
        return item.name

    def get_count(self, item: CategoryItem) -> str:
        """Returns the count value of a category item.

        Args:
            item (CategoryItem): Category item object.

        Returns:
            str: Count of the category item.
        """
        return item.count
