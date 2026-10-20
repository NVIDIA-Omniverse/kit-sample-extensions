# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["FolderCollectionItem", "FolderCategoryItem", "FileDetailItem"]

from typing import Optional

from omni.kit.browser.core import CategoryItem, CollectionItem, DetailItem

from .folder_browser_data import AbstractBrowserFolder, BrowserFile


class FolderCollectionItem(CollectionItem):
    """
    Represents a single folder collection item.
    Args:
        name (str): collection name.
        url (str): folder url.
        folder (AbstractBrowserFolder): folder object linked to this item.
    """

    def __init__(self, name: str, url: str, folder: AbstractBrowserFolder):
        super().__init__(name, url)
        self.folder = folder


class FolderCategoryItem(CategoryItem):
    """
    Represents a single folder category item.
    Args:
        name (str): folder name.
        count (int): count of files in this folder.
        folder (AbstractBrowserFolder): folder object linked to this item.
        parent (CategoryItem): parent category item, to get sibling info.
        is_last_child (bool): Is last child of siblings, for drawing purposes.
    """

    def __init__(
        self,
        name: str,
        count: int,
        folder: AbstractBrowserFolder,
        parent: Optional[CategoryItem] = None,
        is_last_child: Optional[bool] = False,
    ):
        name = name.replace("%20", " ")
        super().__init__(name, count, parent, is_last_child)
        self.folder = folder


class FileDetailItem(DetailItem):
    """
    Represents a single file detail item.
    Args:
        name (str): file name.
        url (str): file url.
        file (BrowserFile): file object linked to this item.
        thumbnail (Optional[str]): thumbnail url of file. Default is None.
    """

    def __init__(self, name: str, url: str, file: BrowserFile, thumbnail: Optional[str] = None):
        name = name.replace("%20", " ")
        super().__init__(name, url, thumbnail)
        self.file = file
