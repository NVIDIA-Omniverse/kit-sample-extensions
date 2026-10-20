# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import json
from itertools import chain
from typing import Dict, List, Optional

import carb.settings
from omni.kit.browser.core import CategoryItem, DetailItem
from omni.kit.browser.folder.core import (
    FileDetailItem,
    FileSystemFolder,
    FolderCategoryItem,
    FolderCollectionItem,
    TreeFolderBrowserModel,
)

from .actions import add_asset_from_drag
from .asset import SimreadyAsset
from .browser_folder import AssetFolder
from .combobox_model import ComboBoxModel
from .style import SIMREADY_DRAG_PREFIX

SETTINGS_DEFAULT_PHYSICS = "/exts/omni.simready.explorer/default_physics"


class AssetDetailItem(DetailItem):
    """
    Represents a single asset detail item.
    Args:
        name (str): asset name.
        url (str): asset url.
        asset (SimreadyAsset): asset object linked to this item.
        thumbnail (Optional[str]): thumbnail url of file. Default is None.
    """

    def __init__(self, asset: SimreadyAsset):
        super().__init__(asset.name, asset.url, asset.thumbnail)
        self.asset = asset

        # Physics model
        physics_values: List[str] = []
        if self.asset.physics_variant:
            physics_values = self.asset.physics_variant.get("Values", [])
            default_value = AssetDetailItem.get_default_physics_value()
            if physics_values:
                # "None" is not in the physics variantset of the asset, so we need to add it "manually"
                physics_values.insert(0, "None")
                if AssetDetailItem.get_default_physics_value() not in physics_values:
                    default_value = physics_values[0]
            self.physics_model = ComboBoxModel(physics_values, current_value=default_value)
        else:
            self.physics_model = None

    @classmethod
    def get_default_physics_value(cls) -> str:
        """Default physics variant value for all assets.
        This is used to initialize the physics model."""
        return str(carb.settings.get_settings().get_as_string(SETTINGS_DEFAULT_PHYSICS) or "RigidBody")

    @property
    def physics(self) -> str:
        return self.physics_model.current_value if self.physics_model else "None"

    @physics.setter
    def physics(self, value: str) -> None:
        if self.physics_model:
            self.physics_model.current_value = value

    def filter(self, filter_words: Optional[List[str]]) -> bool:  # noqa: A003
        # Filter asset by not only name but also tag
        if filter_words is None:
            return True
        else:
            for word in filter_words:
                # Each search word should be in name or tag
                if word.lower() not in self.name.lower():
                    # No partial match in asset name, check tags
                    for tag in self.asset.tags:
                        if word.lower() in tag.lower():
                            break  # Found a partial match in asset tag
                    else:
                        return False  # No partial match in any of the tags, reject asset
            else:
                return True


class SimReadyBrowserModel(TreeFolderBrowserModel):
    """
    Represent browser model for SimReady assets.
    It show files(assets) by tags instead of folders.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            show_summary_folder=True,
            *args,
            **kwargs,
        )

        # Folder for labels, used to show as category item
        self._label_folders: Dict[str, FileSystemFolder] = {}

    @property
    def current_asset_folder(self) -> Optional[AssetFolder]:
        """Current active asset folder"""
        # Now always use first root folder
        return self._root_folders[0] if self._root_folders else None

    def _traverse_folders(self) -> None:
        """Traverse root folders"""
        # Traverse active root folder if necessary
        if self.current_asset_folder:
            # Not in cache
            if not self.current_asset_folder.prepared:
                # No traversed
                self.start_traverse(self.current_asset_folder)

    def refresh_current_asset_folder(self) -> None:
        """Refresh current asset folder"""
        if self.current_asset_folder is None:
            return

        # Force to traverse folder and view will refresh after traverse done
        self.start_traverse(self.current_asset_folder, force=True)

    def start_traverse(self, folder: FileSystemFolder, force: bool = False):
        # For SRE, categories comes from __Label_folders, need to clean for a new traverse
        if folder.url not in self._traverse_in_queue or force:
            # TODO: Need to ONLY clean items related to this asset folder
            self._label_folders = {}

            super().start_traverse(folder, force=force)

    def create_folder_object(self, *args, **kwargs):
        return AssetFolder(*args, **kwargs)

    def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]:
        # Traverse active root folder if necessary
        self._traverse_folders()

        # Create category item from labels
        category_items: List[FolderCategoryItem] = []
        root_folders = [folder for folder in self._label_folders.values() if folder.name.find("/") < 0]
        summary_count = 0
        for folder in root_folders:
            if folder not in self._folder_cache:
                self._folder_cache[folder] = self._create_folder_category_item(folder)
            category_items.append(self._folder_cache[folder])
            summary_count += self._folder_cache[folder].count

        self.sort_items(category_items)

        if self._show_summary_folder:
            category_items.insert(0, CategoryItem(self.SUMMARY_FOLDER_NAME, summary_count))

        return category_items

    def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]:
        """Override to get list of detail items"""
        if item.name == self.SUMMARY_FOLDER_NAME:
            return self._get_summary_detail_items()
        else:
            # List files in item folder
            detail_items = self._get_folder_detail_items(item.folder)
            for child in item.children:
                detail_items += self.get_detail_items(child)

        self.sort_items(detail_items)
        return detail_items

    def get_drag_mime_data(self, item: AssetDetailItem = None) -> str:
        if item:
            drag_data = {"url": item.url, "variants": {}}
            if item.physics:
                drag_data["variants"]["PhysicsVariant"] = item.physics if item.physics != "None" else ""
            return SIMREADY_DRAG_PREFIX + json.dumps(drag_data)
        return super().get_drag_mime_data(item)

    def execute(self, item: DetailItem) -> None:
        drag_mime_data = self.get_drag_mime_data(item)
        add_asset_from_drag(drag_mime_data)

    def _on_folder_traversed(self, folder: AssetFolder, loading_completed=True, updated: bool = True) -> None:
        """
        Folder traversed,
        - Update tags and view
        - Save data to cache
        """
        carb.log_info(f"Traverse completed: {folder.url}, {loading_completed}")

        if updated and folder == self.current_asset_folder:
            # Update tags
            self._update_labels(folder)
            # Refresh view
            self.folder_changed(None)

    def _update_labels(self, folder: AssetFolder) -> None:
        for label, assets in folder.asset_by_labels.items():
            if not label:
                continue

            new_folder = False
            if label not in self._label_folders:
                self._label_folders[label] = AssetFolder(label, label)
                new_folder = True
            self._label_folders[label].files.extend(assets)

            # Clean cache to re-generate category items
            self._folder_cache[self._label_folders[label]] = None

            if new_folder:
                # Create parent label folders
                while True:
                    pos = label.rfind("/")
                    if pos > 0:
                        parent_label = label[:pos]
                        if parent_label not in self._label_folders:
                            self._label_folders[parent_label] = AssetFolder(parent_label, parent_label)
                        folder = self._label_folders[label]
                        if folder not in self._label_folders[parent_label].sub_folders:
                            self._label_folders[parent_label].sub_folders.append(folder)
                            self.sort_items(self._label_folders[parent_label].sub_folders)
                        label = parent_label
                    else:
                        break

    def _get_summary_detail_items(self) -> List[FileDetailItem]:
        # List all assets from label folder
        root_folders = [folder for folder in self._label_folders.values() if folder.name.find("/") < 0]
        return list(chain.from_iterable([self.get_detail_items(self._folder_cache[f]) for f in root_folders]))

    def create_detail_item(self, asset: SimreadyAsset) -> FileDetailItem:
        """
        Create detail item(s) from a file.
        A file may include multi detail items.
        Args:
            file (BrowserFile): File object to create detail item(s)
        """
        return AssetDetailItem(asset)
