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

from omni.kit.browser.core import TreeBrowserWidget

from ..models import FileSystemFolder, FolderCategoryItem
from ..models.traverse_context import TraverseState
from .folder_browser_widget import FolderBrowserWidget
from .folder_category_delegate import FolderCategoryDelegate


class TreeFolderBrowserWidget(FolderBrowserWidget):
    def __init__(self, *args, category_delegate: Optional[FolderCategoryDelegate] = None, **kwargs):
        category_delegate = category_delegate or FolderCategoryDelegate()
        category_width = kwargs.pop("category_width", 190)
        splitter_extra_width = kwargs.pop("splitter_extra_width", 0)
        show_category_splitter = kwargs.pop("show_category_splitter", True)

        super().__init__(
            *args,
            category_delegate=category_delegate,
            category_width=category_width,
            show_category_splitter=show_category_splitter,
            splitter_extra_width=splitter_extra_width,
            **kwargs,
        )
        if isinstance(category_delegate, FolderCategoryDelegate):
            category_delegate.bind_model(self._browser_model)

    def _build_browser_widget_internal(self, *args, **kwargs) -> TreeBrowserWidget:
        browser_widget = TreeBrowserWidget(*args, **kwargs)
        browser_widget._on_category_selection_changed_fn = self._on_category_selection_changed
        return browser_widget

    def _on_category_selection_changed(self, category_item: FolderCategoryItem) -> None:
        # Traverse a category folder when selected and not synced
        if not category_item or not hasattr(category_item, "folder") or category_item.folder.prepared:
            return
        if self._is_cancelled(category_item.folder):
            # The collection was stopped on purpose, and everything under it shares that decision.
            # Selecting a folder inside it must not quietly start scanning again - that is what made
            # a cancel look like it had not worked. Refresh Current Collection is the way back.
            return
        self._browser_model.start_traverse(category_item.folder)

    @staticmethod
    def _is_cancelled(folder) -> bool:
        """True while this folder's collection is stopped. The whole sub tree shares its context."""
        ctx = getattr(folder, "traverse_ctx", None)
        return ctx is not None and ctx.state is TraverseState.CANCELLED

    def _on_new_collection_added(self, folder: FileSystemFolder) -> None:
        # Tree mode, collection is a root category item
        pass
