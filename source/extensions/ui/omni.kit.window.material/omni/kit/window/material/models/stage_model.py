# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import omni.usd
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem
from omni.kit.browser.material import MaterialDetailItem
from pxr import Usd

from .material_helper import MaterialHelper, MaterialStatus

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")
CACHED_THUMBNAIL_PATHS_EXIST: Dict[str, bool] = {}
CACHED_THUMBNAIL_URLS: Dict[str, str] = {}


class MaterialPrimDetailItem(DetailItem):
    """
    Represent a detail item for a material prim in a stage.
    Args:
        path (Optional[str]): Path of material prim. None means item for "Create New
        status (MaterialStatus): Material status, including assigned, selected.
    """

    def __init__(self, path: Optional[str], status: MaterialStatus):
        self.__original_path = path
        self.__prim = None
        self.assigned = status.assigned
        self.selected = status.selected
        self.hovered = False

        if path is None:
            # "Create New"
            prim_path = "Create New"
            name = "Create New"
            thumbnail = f"{ICON_PATH}/Create_New_Material.png"
        else:
            prim_path = path
            name = prim_path.split("/")[-1]

            # Set thumbnail to None by default and set real url later
            # Because for stage with huge materials it is slow
            thumbnail = None

        super().__init__(name, prim_path, thumbnail)

    @property
    def prim(self) -> Optional[Usd.Prim]:
        if self.__prim is not None:
            return self.__prim
        self.__prim = (
            None
            if self.__original_path is None
            else omni.usd.get_context().get_stage().GetPrimAtPath(self.__original_path)
        )
        return self.__prim

    async def check_thumbnail(self) -> bool:
        material_file = self._get_material_filename()
        if not material_file:
            return False

        # To speed up, avoid call omni.client.stat_async if unnecessary
        # First check if thumbnail already cached for same material
        if material_file in CACHED_THUMBNAIL_URLS:
            self.thumbnail = CACHED_THUMBNAIL_URLS[material_file]
            return True

        # Next check if thumbnail directory exists
        thumbnail_path = os.path.dirname(material_file).replace("\\", "/") + "/.thumbs/256x256"
        if thumbnail_path not in CACHED_THUMBNAIL_PATHS_EXIST:
            result, _ = await omni.client.stat_async(thumbnail_path)
            CACHED_THUMBNAIL_PATHS_EXIST[thumbnail_path] = result == omni.client.Result.OK

        if not CACHED_THUMBNAIL_PATHS_EXIST[thumbnail_path]:
            return False

        # Last check if thumbnail exists
        thumbnail = thumbnail_path + "/" + os.path.basename(material_file) + ".png"
        result, _ = await omni.client.stat_async(thumbnail)
        if result == omni.client.Result.OK:
            self.thumbnail = thumbnail
            CACHED_THUMBNAIL_URLS[material_file] = thumbnail
            return True
        return False

    def filter(self, filter_words: Optional[List[str]]) -> bool:
        if self.__original_path is None:
            # Always show "Create New"
            return True
        else:
            return super().filter(filter_words)

    def _get_material_filename(self) -> str:
        shader = omni.usd.get_shader_from_material(self.prim)
        if shader:
            asset = shader.GetSourceAsset("mdl")
            if asset:
                filename = asset.resolvedPath
                return filename.replace("\\", "/")
        return ""


class StageMaterialModel(AbstractBrowserModel):
    """
    Represent materials in opened stage.
    """

    def __init__(self):
        self._material_helper = MaterialHelper(
            self._on_materials_changed, on_material_status_changed_fn=self._on_material_status_changed
        )
        self._materials: List[Usd.Prim] = []
        self._cached_detail_items: Dict[Usd.Prim, MaterialPrimDetailItem] = {}
        self._collection_item = CollectionItem("Stage", "stage")
        self._actived: bool = False
        self._pending_change: bool = False
        self._thumbnail_future: Optional[asyncio.Future] = None
        super().__init__()

    @property
    def actived(self) -> bool:
        """
        Only when model actived, will update materials immediately.
        """
        return self._actived

    @actived.setter
    def actived(self, bind) -> None:
        self._actived = bind
        if self._actived and self._pending_change:
            # Update items since there are pending changes
            self._item_changed(self._collection_item)
            self._pending_change = False

    @property
    def selection_include_children(self) -> bool:
        return self._material_helper.selection_include_children

    @selection_include_children.setter
    def selection_include_children(self, enable: bool) -> None:
        self._material_helper.selection_include_children = enable

    def destroy(self) -> None:
        if self._material_helper:
            self._material_helper.destroy()
            self._material_helper = None

        if self._thumbnail_future is not None and not self._thumbnail_future.done():
            self._thumbnail_future.cancel()

    def add_on_selection_changed_fn(
        self, on_selection_changed_fn: callable, trigger_on_next_selection: bool = False
    ) -> None:
        """
        Add function called when material selection changed.
        Args:
            on_selection_changed_fn (callable): Function called when material selection changed. Function signature:
                void on_selection_changed_fn(materials: Dict[Usd.Prim, MaterialStatus])
            trigger_on_next_selection (bool): False to call callback immediately with current selection. Otherwise call when next selection changed.
        """
        self._material_helper.add_on_selection_changed_fn(
            on_selection_changed_fn, trigger_on_next_selection=trigger_on_next_selection
        )

    def remove_on_selection_changed_fn(self, on_selection_changed_fn: callable) -> bool:
        """
        Remove function called when material selection changed:
        Args:
            on_selection_changed_fn (callable): Function to be removed.
        """
        if self._material_helper:
            return self._material_helper.remove_on_selection_changed_fn(on_selection_changed_fn)

    def start_pick(self, on_materials_picked: callable):
        """
        Start picking materials from stage.
        Args:
            on_materials_picked: Function called when materials picked. Function signature:
                void on_materials_picked(materials: Dict[Usd.Prim, MaterialStatus])
        """
        self._material_helper.start_pick(on_materials_picked)

    def stop_pick(self):
        """
        Stop picking materials from stage.
        """
        if self._material_helper:
            self._material_helper.stop_pick()

    def execute(self, item: MaterialPrimDetailItem) -> None:
        """
        Bind material to selected prims
        """
        if item.prim:
            omni.kit.undo.begin_group()

            # TODO: In multiple context mode, we may get current context here
            usd_context = omni.usd.get_context()
            selected_paths = usd_context.get_selection().get_selected_prim_paths()
            stage = usd_context.get_stage()

            for path in selected_paths:
                prim = stage.GetPrimAtPath(path)
                if prim and omni.usd.is_prim_material_supported(prim):
                    omni.kit.commands.execute("BindMaterial", prim_path=path, material_path=item.prim.GetPath())

            omni.kit.undo.end_group()

    def get_collection_items(self) -> List[CollectionItem]:
        return [self._collection_item]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        self._materials = self._material_helper.get_materials_from_stage()
        count = len(self._materials) if self._materials else 0
        return [CategoryItem("Stage", count)]

    def get_detail_items(self, item: CategoryItem) -> List[MaterialDetailItem]:
        detail_items = []
        self._cached_detail_items = {}
        if self._materials:
            for material in self._materials:
                self._cached_detail_items[material] = MaterialPrimDetailItem(material, self._materials[material])
                detail_items.append(self._cached_detail_items[material])
            detail_items.sort(key=lambda item: item.name)

        if self._thumbnail_future is not None and not self._thumbnail_future.done():
            self._thumbnail_future.cancel()
        self._thumbnail_future = asyncio.ensure_future(self.__check_thumbnail())
        detail_items.insert(0, MaterialPrimDetailItem(None, MaterialStatus()))
        return detail_items

    def _on_materials_changed(self) -> None:
        # If model actived, update items immediately. Otherwise, pending until model actived.
        if self._actived:
            collection_changed = False
            materials_changed = []
            materials = self._material_helper.get_materials_from_stage()
            if materials is not None:
                if len(materials) == len(self._materials):
                    for material in materials:
                        if material not in self._materials:
                            collection_changed = True
                            break
                        else:
                            if materials[material] != self._materials[material]:
                                materials_changed.append(material)
                else:
                    collection_changed = True
                if collection_changed:
                    # Collection changed
                    self._item_changed(self._collection_item)
                else:
                    # Only some materials changed (maybe None because only care assigned/selected status here)
                    for material in materials_changed:
                        self._cached_detail_items[material].assigned = materials[material].assigned
                        self._cached_detail_items[material].selected = materials[material].selected
                        self._item_changed(self._cached_detail_items[material])
                    self._materials = materials
        else:
            self._pending_change = True

    def _on_material_status_changed(self, material: Usd.Prim, material_status: MaterialStatus):
        if material in self._cached_detail_items:
            if (
                self._cached_detail_items[material].assigned != material_status.assigned
                or self._cached_detail_items[material].selected != material_status.selected
            ):
                self._cached_detail_items[material].assigned = material_status.assigned
                self._cached_detail_items[material].selected = material_status.selected
                self._item_changed(self._cached_detail_items[material])

    async def __check_thumbnail(self):
        last_start = time.time()
        for _, item in self._cached_detail_items.items():
            if await item.check_thumbnail():
                self._item_changed(item)
            if time.time() - last_start > 0.1:
                await omni.kit.app.get_app().next_update_async()
                last_start = time.time()

        self._thumbnail_future = None
