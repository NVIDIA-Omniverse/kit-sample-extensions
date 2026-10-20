# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import copy
from typing import Union

from ..models import CategoryItem, CollectionItem, DetailItem
from .browser_widget import BrowserWidget
from .style import TREE_UI_STYLES
from .tree_category_delegate import TreeCategoryDelegate


class TreeBrowserWidget(BrowserWidget):
    """A tree based browser widget that extends the base browser widget functionality using a tree view interface for categories and details.

    This class leverages a category delegate to manage how category items are displayed and refreshed, and supports additional UI styling to customize the tree appearance. When a category item is updated, it refreshes the corresponding category view and, if the item is selected, triggers a detail view update.

    Args:
        args (tuple): Variable positional arguments for initializing the widget.

    Keyword Args:
        category_delegate (TreeCategoryDelegate, optional): Delegate used for managing category display. Defaults to a new TreeCategoryDelegate instance.
        show_collection (bool, optional): Flag to control the visibility of the collection view. Defaults to False.
        style (dict, optional): Additional style parameters to update the default tree UI styles.
    """

    def __init__(self, *args, **kwargs):
        category_delegate = kwargs.pop("category_delegate", TreeCategoryDelegate())
        show_collection = kwargs.pop("show_collection", False)
        extra_ui_style = kwargs.pop("style", {})
        extra_tree_style = copy.copy(TREE_UI_STYLES)
        extra_tree_style.update(extra_ui_style)

        super().__init__(
            *args,
            category_delegate=category_delegate,
            style=extra_tree_style,
            show_collection=show_collection,
            **kwargs,
        )

    def _on_model_item_changed(self, item: Union[CollectionItem, CategoryItem, DetailItem]) -> None:
        if item and isinstance(item, CategoryItem):
            # Redraw item in category view
            self._category_view.model._item_changed(item)
            if item in self.category_selection:
                # Category selected, need to refresh details
                self._detail_view.model._item_changed(None)
        else:
            super()._on_model_item_changed(item)
