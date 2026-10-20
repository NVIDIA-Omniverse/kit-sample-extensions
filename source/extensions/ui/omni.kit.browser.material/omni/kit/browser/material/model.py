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
from typing import Dict, List, Optional, Union

import carb.settings
import omni.kit.commands
import omni.kit.undo
import omni.usd
from omni.kit.browser.folder.core import FileDetailItem, FolderCategoryItem, TreeFolderBrowserModel
from pxr import Sdf, Tf, Usd

from .data import MaterialFile, MaterialFolder, MaterialType, SubMaterial, UsdSubMaterial

SETTING_ROOT = "/exts/omni.kit.browser.material/"
SETTING_COLLECTION_ROOTS = SETTING_ROOT + "folders"
SETTING_FOLDERS_HIED_ROOT = SETTING_ROOT + "folders_hide_in_category"
SETTING_DONOT_CAST_SHADOWS_ROOT = SETTING_ROOT + "doNotCastShadows/"
SETTING_DONOT_CAST_SHADOWS_FOLDERS = SETTING_DONOT_CAST_SHADOWS_ROOT + "folders"
SETTING_DONOT_CAST_SHADOWS_EXCEPT_FILES = SETTING_DONOT_CAST_SHADOWS_ROOT + "exception_files"


class MaterialDetailItem(FileDetailItem):
    """
    Represent material detail item
    Args:
        file (MaterialFile): MaterialFile object to create detail item
        donot_cast_shadows (Optional[bool]): True to donot cast shadows if this material applied. False cast shadows. None means do not change this setting
    """

    def __init__(self, file: MaterialFile, donot_cast_shadows: Optional[bool], sub_material: UsdSubMaterial = None):
        dirs = file.url.split("/")
        name = dirs[-1]
        self.sub_material = sub_material
        if sub_material:
            name = sub_material.name
            thumbnail = sub_material.thumbnail
        else:
            thumbnail = file.thumbnail

        super().__init__(name, file.url, file, thumbnail)

        self.donot_cast_shadows = donot_cast_shadows

    def get_default_thumbmail_url(self):
        """
        Get default thumbnail url.
        """
        if self.sub_material:
            return self.sub_material.get_default_thumbnail_url(self.url)
        else:
            return self.file.get_default_thumbnail_url()


class MaterialBrowserModel(TreeFolderBrowserModel):
    """
    Represent material browser model.
    Please reference FolderBrowserModel for args and keyword args.
    """

    def __init__(self, **kwargs):
        timeout = kwargs.pop(
            "timeout", carb.settings.get_settings().get("/exts/omni.kit.browser.material/data/timeout")
        )
        super().__init__(
            setting_folders=SETTING_COLLECTION_ROOTS,
            show_category_subfolders=True,
            local_cache_file="${shared_documents}/omni.kit.browser.material.cache.json",
            filter_file_suffixes=[".mdl", ".usd", ".usda", ".usdc"],
            ignore_folder_names=["Templates"],
            timeout=timeout,
            setting_folders_hide_in_category=SETTING_FOLDERS_HIED_ROOT,
            **kwargs,
        )

        self._donot_cast_shadows_folders = self._settings.get(SETTING_DONOT_CAST_SHADOWS_FOLDERS)
        self._donot_cast_shadows_except_files = self._settings.get(SETTING_DONOT_CAST_SHADOWS_EXCEPT_FILES)

    def create_folder_object(self, *args, **kwargs):
        """Create a folder object for material browser using provided arguments and keyword arguments.

        Returns:
            MaterialFolder: Created folder object.
        """
        return MaterialFolder(*args, **kwargs)

    def create_category_item(self, folder: MaterialFolder) -> FolderCategoryItem:
        """Create a category item from a folder.

        Args:
            folder (MaterialFolder): Folder used to create the category item.

        Returns:
            FolderCategoryItem: Category item with folder name and total file count.
        """
        count = 0

        def __recursive_count(folder: MaterialFolder, inlcude_sub_folder=True) -> int:
            count = 0
            for file in folder.files:
                if file.sub_materials:
                    # For multi materials, count all sub materials
                    count += len(file.sub_materials)
                else:
                    count += 1

            if self._show_category_subfolders:
                for sub_folder in folder.sub_folders:
                    count += __recursive_count(sub_folder)

            return count

        count += __recursive_count(folder)
        return FolderCategoryItem(folder.name, count, folder)

    def create_detail_item(self, file: MaterialFile) -> Union[MaterialDetailItem, List[MaterialDetailItem]]:
        """Create detail item or list of detail items from a file.

        Args:
            file (MaterialFile): File used to create detail item(s).

        Returns:
            Union[MaterialDetailItem, List[MaterialDetailItem]]: Created detail item instance(s) for the material file.
        """
        # Only set donot_cast_shadows for materials in defined folders
        # Otherwise keep no change
        donot_cast_shadows = None
        if self._donot_cast_shadows_folders:
            dirs = file.url.split("/")
            name = dirs[-1]
            folder = dirs[-2]
            if folder in self._donot_cast_shadows_folders:
                if not self._donot_cast_shadows_except_files or name not in self._donot_cast_shadows_except_files:
                    donot_cast_shadows = True

        if file.sub_materials:
            return [MaterialDetailItem(file, donot_cast_shadows, sub_material=sub) for sub in file.sub_materials]
        else:
            return MaterialDetailItem(file, donot_cast_shadows)

    def execute(self, item: MaterialDetailItem) -> None:
        """
        Apply material to selected prims, add doNotCastShadows proprty to prims if it does not already exist.
        Args:
            item (MaterialDetailItem): Material item to assign.
        """

        usd_context = omni.usd.get_context()
        selected_paths = usd_context.get_selection().get_selected_prim_paths()

        omni.kit.undo.begin_group()

        material_prim_path = self.create_material(item)

        for prim_path in selected_paths:
            self.bind_material(material_prim_path, [prim_path])

            if item.donot_cast_shadows is not None:
                # Change primvar "doNotCastShadows" to selected prim
                omni.kit.commands.execute(
                    "ChangePrimVarCommand",
                    prim_path=prim_path,
                    primvar_name="doNotCastShadows",
                    value=item.donot_cast_shadows,
                    type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
                )

        omni.kit.undo.end_group()

    @staticmethod
    def create_material_by_url(material_url: str, sub_material_id: Optional[str], context_name: str = ""):
        """
        Create material.
        Args:
            material_url (str): Url of material.
            sub_material_id (str): Id of sub material. Default None means no sub material.
            context_name (str): Name of usd context to create material in.
        Returns:
            Path of created material prim
        """
        file = MaterialFile(material_url)
        if sub_material_id:
            sub_material = SubMaterial(sub_material_id.split("/")[-1], url=sub_material_id)
        else:
            sub_material = None
        item = MaterialDetailItem(file, False, sub_material)
        return MaterialBrowserModel.create_material_by_item(item, context_name)

    @staticmethod
    def create_material_by_item(item: MaterialDetailItem, context_name: str = "") -> str:
        """Create material from a material detail item.

        Args:
            item (MaterialDetailItem): Material detail item for material creation.
            context_name (str): USD context name for material creation.

        Returns:
            str: Path of the created material prim.
        """
        usd_context = omni.usd.get_context(context_name)
        stage: Usd.Stage = usd_context.get_stage()

        default_prim = stage.GetDefaultPrim()
        default_root = default_prim.GetPath().pathString if default_prim else "/World"
        materials_root = f"{default_root}/Looks"
        materials_root_prim = stage.GetPrimAtPath(materials_root)
        if not materials_root_prim:
            stage.DefinePrim(materials_root, "Scope")

        material_prim_name = item.sub_material.name if item.sub_material else item.name[:-4]
        material_prim_path = omni.usd.get_stage_next_free_path(
            stage, f"{materials_root}/{Tf.MakeValidIdentifier(material_prim_name)}", False
        )

        if item.file.type == MaterialType.MDL:
            omni.kit.commands.execute(
                "CreateMdlMaterialPrimCommand",
                mtl_url=item.url,
                mtl_name=material_prim_name,
                mtl_path=material_prim_path,
            )
        else:
            omni.kit.commands.execute(
                "CreateReferenceCommand",
                path_to=material_prim_path,
                asset_path=item.url,
                prim_path=item.sub_material.url if item.sub_material else None,
                usd_context=usd_context,
            )
        return material_prim_path

    def create_material(self, item: MaterialDetailItem, context_name: str = "") -> str:
        """Create material by invoking create_material_by_item.

        Args:
            item (MaterialDetailItem): Material detail item for creating material.
            context_name (str): USD context name for material creation.

        Returns:
            str: Path of the created material prim.
        """
        return MaterialBrowserModel.create_material_by_item(item, context_name)

    def bind_material(self, material_prim_path: str, target_paths: List[str]) -> None:
        """
        Bind material to target prims.
        Args:
            material_prim_path (str): Url of material prim.
            target_paths (List[str]): List of target paths.
        """
        for path in target_paths:
            omni.kit.commands.execute(
                "BindMaterialCommand",
                prim_path=path,
                material_path=material_prim_path,
            )

    def _save_file_to_json(self, folder: MaterialFolder, file: MaterialFile) -> Dict:
        file_cache = super()._save_file_to_json(folder, file)
        file_cache["type"] = file.type
        if file.sub_materials:
            file_cache["subs"] = {}
            for sub in file.sub_materials:
                file_cache["subs"][sub.name] = {
                    "url": sub.url,
                    "thumbnail": os.path.relpath(sub.thumbnail, folder.url).replace("\\", "/") if sub.thumbnail else "",
                    "default": sub.default if isinstance(sub, UsdSubMaterial) else "",
                }
        return file_cache

    def _load_file_from_json(self, data: Dict, folder: MaterialFolder) -> Optional[MaterialFile]:
        thumbnail = data["thumbnail"] if data["thumbnail"] else None
        if thumbnail:
            thumbnail = folder.url + "/" + thumbnail

        sub_materials = None
        subs_datas = data.get("subs", None)
        if subs_datas:
            sub_materials = []
            for name, sub_data in subs_datas.items():
                sub_thumbnail = (folder.url + "/" + sub_data["thumbnail"]) if sub_data["thumbnail"] else None
                if sub_data["default"] != "":
                    sub = UsdSubMaterial(sub_data["url"], default=sub_data["default"], thumbnail=sub_thumbnail)
                else:
                    sub = SubMaterial(name, thumbnail=sub_thumbnail, url=sub_data["url"])
                sub_materials.append(sub)

        file = MaterialFile(folder.url + "/" + data["url"], sub_materials=sub_materials)
        file.thumbnail = thumbnail
        return file
