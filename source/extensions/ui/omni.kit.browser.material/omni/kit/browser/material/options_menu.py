# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.client
from omni.kit.browser.core import OptionMenuDescription
from omni.kit.browser.folder.core import FolderBrowserModel, FolderOptionsMenu

from .delegate import MaterialDetailDelegate


class MaterialOptionsMenu(FolderOptionsMenu):
    """
    Represent options menu used in material browser.
    Args:
        delegate (MaterialDetailDelegate): Detail delegate used in the window.
    """

    def __init__(self, delegate: MaterialDetailDelegate):
        self._delegate = delegate
        super().__init__(None)

        if self._delegate.can_generate_thumbnail():
            self.append_menu_item(OptionMenuDescription("", None))
            self.append_menu_item(
                OptionMenuDescription(
                    "Generate Thumbnail For Selected",
                    clicked_fn=self._on_generate_item_thumbnail,
                    enabled_fn=self._is_item_thumbnail_enabled,
                )
            )
            self.append_menu_item(
                OptionMenuDescription(
                    "Generate Thumbnail For Current Category",
                    clicked_fn=self._on_generate_category_thumbnails,
                    enabled_fn=self._is_category_thumbnail_enabled,
                )
            )
            # In tree mode, collection is also a category.
            # Select the category with collection url to generate for collection
            """
            self.append_menu_item(
                OptionMenuDescription(
                    "Generate Thumbnail For Current Collection",
                    clicked_fn=self._on_generate_collection_thumbnails,
                    enabled_fn=self._is_collection_thumbnail_enabled,
                )
            )
            """

    def _on_generate_item_thumbnail(self) -> None:
        for detail_item in self._browser_widget.detail_selection:
            self._delegate.generate_thumbnail(detail_item)

    def _on_generate_category_thumbnails(self) -> None:
        selection = self._browser_widget.category_selection
        if selection:
            category_item = selection[0]
            if hasattr(category_item, "folder") and category_item.folder:
                for detail_item in self._browser_widget.model.get_detail_items(selection[0]):
                    self._delegate.generate_thumbnail(detail_item)

    def _on_generate_collection_thumbnails(self) -> None:  # pragma: no cover - never called
        collection_item = self._browser_widget.collection_selection
        if collection_item:
            category_items = self._browser_widget.model.get_item_children(collection_item)
            for category_item in category_items:
                if category_item.name == FolderBrowserModel.SUMMARY_FOLDER_NAME:
                    continue
                detail_items = self._browser_widget.model.get_item_children(category_item)
                for detail_item in detail_items:
                    self._delegate.generate_thumbnail(detail_item)

    def _is_item_thumbnail_enabled(self) -> bool:
        if self._browser_widget is None:
            return False
        detail_selection = self._browser_widget.detail_selection
        if detail_selection:
            list_entry = detail_selection[0].file.list_entry
            if list_entry and not list_entry.access & omni.client.AccessFlags.WRITE:
                return False
            else:
                return True
        else:
            return False

    def _is_collection_thumbnail_enabled(self) -> bool:  # pragma: no cover
        if self._browser_widget is None:
            return False
        category_items = self._browser_widget.category_selection
        if category_items:
            category_item = category_items[0]
            if hasattr(category_item, "folder"):
                list_entry = category_item.folder.list_entry
                if list_entry is None:
                    result, list_entry = omni.client.stat(category_item.url)
                    if result == omni.client.Result.OK:
                        category_item.folder.list_entry = list_entry
                if list_entry and not list_entry.access & omni.client.AccessFlags.WRITE:
                    return False
                else:
                    return True
            else:
                return False
        else:
            return False

    def _is_category_thumbnail_enabled(self) -> bool:
        if self._browser_widget is None:
            return False
        category_selection = self._browser_widget.category_selection
        if category_selection:
            category_item = category_selection[0]
            if category_item.name == FolderBrowserModel.SUMMARY_FOLDER_NAME:
                return self._is_collection_thumbnail_enabled()
            else:
                list_entry = category_selection[0].folder.list_entry
                if list_entry and not list_entry.access & omni.client.AccessFlags.WRITE:
                    return False
                return True
        else:
            return False
