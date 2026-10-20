# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["FolderOptionsMenu"]

from typing import Collection, Optional

from omni.kit.browser.core import OptionMenuDescription, OptionsMenu

from ..models.folder_browser_item import FolderCollectionItem
from ..models.tree_folder_browser_model import TreeFolderBrowserModel
from .predownload import PredownloadHelper


class FolderOptionsMenu(OptionsMenu):
    """
    Represent options menu used in material browser.
    Args:
        predownload_folder (Optional[str]): Folder to predownload files and sub folders. Predownload is used to download items from remote folder to local when startup. Default None means no predowndload.
    """

    def __init__(self, predownload_folder: Optional[str] = None):
        super().__init__()

        self._predownload_helper = PredownloadHelper(predownload_folder) if predownload_folder else None
        self._refresh_collection_menu_desc = OptionMenuDescription(
            "Refresh Current Collection",
            clicked_fn=self._on_refresh_collection,
            visible_fn=self._is_refresh_collection_visible,
        )
        self.append_menu_item(self._refresh_collection_menu_desc)

        self._download_menu_desc = OptionMenuDescription(
            "Download Current Collection",
            clicked_fn=self._on_download_collection,
            enabled_fn=self._is_download_collection_enable,
            visible_fn=lambda: self._predownload_helper is not None,
            get_text_fn=self._get_menu_item_text,
        )

        self.append_menu_item(OptionMenuDescription("", visible_fn=lambda: self._predownload_helper is not None))
        self.append_menu_item(self._download_menu_desc)

    def destroy(self) -> None:
        super().destroy()
        if self._predownload_helper:
            self._predownload_helper.destroy()

    def _on_remove_collection(self) -> None:
        if isinstance(self._browser_widget.model, TreeFolderBrowserModel):
            # Here collection means the root category item in category tree view
            if self._browser_widget.category_selection:
                category_selected = self._browser_widget.category_selection[0]
                collection_items = self._browser_widget.model.get_item_children(None)
                root_category_items = self._browser_widget.model.get_item_children(collection_items[0])
                if category_selected in root_category_items and hasattr(category_selected, "folder"):
                    self._browser_widget.model.remove_root_folder(category_selected.folder.url)
        else:
            super()._on_remove_collection()

    def _is_remove_collection_enabled(self) -> bool:
        if isinstance(self._browser_widget.model, TreeFolderBrowserModel):
            # Here collection means the root category item in category tree view
            if self._browser_widget.category_selection:
                category_selected = self._browser_widget.category_selection[0]
                collection_items = self._browser_widget.model.get_item_children(None)
                root_category_items = self._browser_widget.model.get_item_children(collection_items[0])
                if category_selected in root_category_items:
                    return True
            else:
                return False
        else:
            return super()._is_remove_collection_enabled()

    def _on_refresh_collection(self):
        collection_item: FolderCollectionItem = self._browser_widget.collection_selection
        if collection_item and hasattr(collection_item, "folder"):
            folder = collection_item.folder
            if folder and folder.has_timeout:
                folder._timeout = 10
                self._browser_widget.model.start_traverse(folder)

    def _is_refresh_collection_visible(self) -> bool:
        collection_item: FolderCollectionItem = self._browser_widget.collection_selection
        if collection_item:
            if hasattr(collection_item, "folder") and collection_item.folder and collection_item.folder.has_timeout:
                return True
        return False

    def _is_download_collection_enable(self):
        collection_item = self._browser_widget.collection_selection
        if collection_item:
            if self._is_remote_folder(collection_item.url):
                if self._predownload_helper:
                    state = self._predownload_helper.get_download_state(collection_item.url)
                    if state is None:
                        return True
                    else:
                        # Disable if already start downloading
                        return False
            else:
                return False
        return False

    def _get_menu_item_text(self) -> str:
        # Show download state if download starts
        collection_item = self._browser_widget.collection_selection
        if collection_item:
            if self._predownload_helper:
                state = self._predownload_helper.get_download_state(collection_item.url)
                if state is not None:
                    return "Download - " + state

        return "Download Current Collection"

    def _on_download_collection(self) -> None:
        collection_item = self._browser_widget.collection_selection
        if collection_item:
            self._predownload_helper.append_folder(collection_item.url)

    def _is_remote_folder(self, url):
        url = url.lower()
        return url.startswith("omniverse://") or url.startswith("http://") or url.startswith("https://")
