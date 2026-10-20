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

import carb
import omni.kit.window.file
from omni.kit.browser.core import DetailItem
from omni.kit.browser.folder.core import TreeFolderBrowserModel

SETTINGS_ROOT = "exts/omni.kit.browser.sample/"
SETTINGS_FOLDERS = SETTINGS_ROOT + "folders"
SETTINGS_FOLDERS_HIDE_ROOT = SETTINGS_ROOT + "folders_hide_in_category"


class SampleBrowserModel(TreeFolderBrowserModel):
    """Sample browser model that can register multiple root folder paths."""

    def __init__(self, *args, **kwargs):
        """Sample browser model init."""
        super().__init__(
            *args,
            setting_folders="/exts/omni.kit.browser.sample/folders",
            filter_file_suffixes=[".usd", ".usda", ".usdc"],
            local_cache_file="${shared_documents}/omni.kit.browser.sample.cache.json",
            ignore_sub_folder_with_files=True,
            setting_folders_hide_in_category=SETTINGS_FOLDERS_HIDE_ROOT,
            **kwargs,
        )

    def execute(self, item: DetailItem) -> None:
        """Execute this method when a DetailItem is double-clicked."""
        # Create a Reference of the Props in the stage
        omni.kit.window.file.open_stage(item.url)

    def register_sample_folder(self, url: str, name: Optional[str] = None):
        """Register a sample folder path with the model."""
        if name:
            url = f"{name}::{url}"
        carb.log_info(f"Registering root folder: {url}")
        self.process_root_folder(url)

    def unregister_sample_folder(self, url: str):
        """Unregister a sample folder path with the model when finished with it."""
        self.remove_root_folder(url)
