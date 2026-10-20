# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from functools import partial
from typing import List, Optional

import omni.ui as ui
from omni.kit.browser.core import TreeCategoryDelegate

from ..models.folder_browser_item import FolderCategoryItem
from ..models.tree_folder_browser_model import TreeFolderBrowserModel
from .context_menu import ContextMenu


class FolderCategoryDelegate(TreeCategoryDelegate):
    def __init__(self, **kwargs):
        super().__init__(hide_zero_count=True)
        self._widget_model = None
        self._context_menu = None
        # Wired by the widget when it opts into scan progress. While these are None the spinner is
        # the plain indicator it has always been.
        self._scan_tooltip_fn = None
        self._show_progress_fn = None
        self._cancel_fn = None
        self._loading_menu = None

    def _set_scan_callbacks(self, tooltip_fn=None, show_progress_fn=None, cancel_fn=None) -> None:
        """
        Make the per-collection spinner a control.

        Args:
            tooltip_fn: Called with the item, returns the tooltip text.
            show_progress_fn: Called with the item when the spinner is clicked.
            cancel_fn: Called with the item to stop that collection's scan.
        """
        self._scan_tooltip_fn = tooltip_fn
        self._show_progress_fn = show_progress_fn
        self._cancel_fn = cancel_fn

    def build_loading_overlay(self, item) -> None:
        """
        Make the spinner report what the scan is doing.

        An invisible button over it, so the spinner keeps its own look and gains a tooltip and a
        click. Only once a browser has opted in through :meth:`_set_scan_callbacks` - until then
        nothing is built, a click over the spinner selects the row, and the tree behaves as it
        always did.
        """
        if self._show_progress_fn is None and self._scan_tooltip_fn is None:
            return
        ui.InvisibleButton(tooltip=self.__scan_tooltip(item), clicked_fn=partial(self.__on_spinner_clicked, item))

    def __scan_tooltip(self, item) -> str:
        if self._scan_tooltip_fn is None:
            return ""
        try:
            return self._scan_tooltip_fn(item) or ""
        except Exception:  # noqa: BLE001 - a tooltip must never break a row build
            return ""

    def __on_spinner_clicked(self, item) -> None:
        if self._show_progress_fn is not None:
            self._show_progress_fn(item)

    def get_count(self, item: FolderCategoryItem) -> str:
        """
        What the row shows on its right hand side.

        A number is a claim that the folder holds that many items. A folder whose own traverse was
        stopped part way does not - it holds however much had been found at that moment, which reads
        as if it had finished. `TIMEOUT` already takes this line for the same reason.

        Only folders that were actually interrupted say so. One that had already finished keeps its
        count, and one the traverse never reached keeps its zero, which `hide_zero_count` renders as
        blank. The flag is cleared by the next traverse.
        """
        if hasattr(item, "folder") and item.folder:
            if item.folder.has_timeout:
                return "TIMEOUT"
            if getattr(item.folder, "traverse_cancelled", False):
                return "Cancelled"
        return super().get_count(item)

    # To collect all items, we need to bind widget model to get all detail items
    def bind_model(self, model: TreeFolderBrowserModel):
        self._widget_model = model

    def _get_collect_urls(self, item: FolderCategoryItem) -> Optional[List[str]]:  # pragma: no cover - never called
        """
        Query folder category local collected urls.
        Args:
            item (FolderCategoryItem): category item to query
        Return:
            collected urls if found. Else None.
        """
        if not self._widget_model or not item:
            return None
        items = self._widget_model.get_detail_items(item)

        return [item.url for item in items]

    def _on_item_right_click(self, item: FolderCategoryItem):
        """Show category item's menu"""
        if getattr(item, "loading", False) and self._cancel_fn is not None:
            # A collection being scanned gets its own menu. The collect entries below act on the
            # files a collection contains, which is exactly what is not yet known while it scans.
            self._show_loading_menu(item)
            return
        if self._context_menu is None:
            self._context_menu = ContextMenu()
        if self._context_menu:
            self._context_menu.urls = self._get_collect_urls(item)
            self._context_menu.folder_name = item.name
            self._context_menu.show_menu()

    def _show_loading_menu(self, item: FolderCategoryItem) -> None:
        """Right-click menu for a collection that is being scanned: watch it, or stop it."""
        self._loading_menu = ui.Menu("Scan")
        with self._loading_menu:
            if self._show_progress_fn is not None:
                ui.MenuItem("Show Scan Progress", triggered_fn=lambda i=item: self._show_progress_fn(i))
            ui.MenuItem("Cancel Scan", triggered_fn=lambda i=item: self._cancel_fn(i))
        self._loading_menu.show()
