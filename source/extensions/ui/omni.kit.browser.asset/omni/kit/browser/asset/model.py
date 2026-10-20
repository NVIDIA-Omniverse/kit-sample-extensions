# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os

import carb.settings
import omni.kit.commands
import omni.usd
from omni.kit.browser.core import DetailItem
from omni.kit.browser.folder.core import FileSystemFolder, TreeFolderBrowserModel
from pxr import Sdf, Tf, Usd

SETTING_FOLDER = "/exts/omni.kit.browser.asset/folders"


class AssetBrowserModel(TreeFolderBrowserModel):
    """
    Represent asset browser model
    """

    def __init__(self, *args, **kwargs):
        settings = carb.settings.get_settings()
        self.__default_folders = settings.get(SETTING_FOLDER)
        super().__init__(
            *args,
            setting_folders=SETTING_FOLDER,
            show_category_subfolders=True,
            hide_file_without_thumbnails=False,
            local_cache_file="${shared_documents}/omni.kit.browser.asset.cache.json",
            filter_file_suffixes=[".usd", ".usda", ".usdc"],
            show_summary_folder=True,
            timeout=settings.get("/exts/omni.kit.browser.asset/data/timeout"),
            **kwargs,
        )

    def create_folder_object(self, name: str, url: str, **kwargs) -> FileSystemFolder:
        """
        Create a folder object when a root folder appended. Default using FileSystemFolder.
        User could overridden to create own folder object for special usage.
        Args and keyword args please reference to FileSystemFolder.
        """
        if self.__default_folders and any(url.startswith(folder) for folder in self.__default_folders):
            # OM-75191: For folders in default settings, hide file without thumbnail
            # Otherwise show all files
            kwargs["ignore_file_without_thumbnail"] = True
        return FileSystemFolder(name, url, **kwargs)

    def execute(self, item: DetailItem) -> None:
        # Create a Reference or payload of the Props in the stage
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        new_prim_path = self._make_prim_path(stage, item.url)
        as_instanceable = carb.settings.get_settings().get("/persistent/app/stage/instanceableOnCreatingReference")

        # Determine if we should create a payload or reference
        create_as_payload = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport") == "payload"

        # Add asset to stage
        cmd_name = "CreatePayloadCommand" if create_as_payload else "CreateReferenceCommand"
        omni.kit.commands.execute(
            cmd_name,
            usd_context=omni.usd.get_context(),
            path_to=new_prim_path,
            asset_path=item.url,
            instanceable=as_instanceable,
        )

    def _make_prim_path(self, stage: Usd.Stage, url: str, prim_path: Sdf.Path = None, prim_name: str = None):
        """Make a new/unique prim path for the given url"""
        if prim_path is None or prim_path.isEmpty:
            if stage.HasDefaultPrim():
                prim_path = stage.GetDefaultPrim().GetPath()
            else:
                prim_path = Sdf.Path.absoluteRootPath

        if prim_name is None:
            prim_name = Tf.MakeValidIdentifier(os.path.basename(os.path.splitext(url)[0]))

        return Sdf.Path(omni.usd.get_stage_next_free_path(stage, prim_path.AppendChild(prim_name).pathString, False))
