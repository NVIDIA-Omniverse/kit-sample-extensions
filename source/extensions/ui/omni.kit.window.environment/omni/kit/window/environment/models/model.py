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
import json
import os
from typing import Dict, List, Optional, Tuple

import carb
import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from omni.kit.browser.core import CategoryItem, CollectionItem
from omni.kit.browser.folder.core import BrowserFile, FileDetailItem, TreeFolderBrowserModel
from omni.kit.environment.core import SceneTemplateHelper, SkyType
from omni.kit.stage_templates import unregister_template

from .data import EnvFile, EnvFolder, EnvType, get_env_type
from .stage_template import get_template_cache_file, register_env_template, unregister_cached_env_templates

SETTING_ROOT = "/exts/omni.kit.window.environment/"
SETTING_DATA_TIMEOUT = SETTING_ROOT + "data/timeout"
SETTING_COLLECTION_ROOTS = SETTING_ROOT + "folders"
SETTING_CUSTOM_COLLECTION_ROOTS = SETTING_ROOT + "custom_folders"


class EnvDetailItem(FileDetailItem):
    """
    Represent env detail item
    Args:
        file (BrowserFile): BrowserFile object to create detail item.
    """

    def __init__(self, file: EnvFile):
        dirs = file.url.split("/")
        name = dirs[-1]
        super().__init__(name, file.url, file, file.thumbnail)

        if not hasattr(file, "type"):
            file.type = get_env_type(file.url)
        self.type = file.type


class EnvBrowserModel(TreeFolderBrowserModel):
    """
    Represent environment browser model.
    Args:
        env_type (EnvType): Type of env file
    Please reference FolderBrowserModel for args and keyword args.
    """

    def __init__(self, **kwargs):
        self._settings = carb.settings.get_settings()
        self._scene_template_helper = SceneTemplateHelper()

        timeout = kwargs.pop("timeout", self._settings.get(SETTING_DATA_TIMEOUT))
        super().__init__(
            setting_folders=SETTING_COLLECTION_ROOTS,
            timeout=timeout,
            local_cache_file="${shared_documents}/omni.kit.window.environment.cache.json",
            ignore_sub_folder_with_files=True,
            setting_folders_hide_in_category="/exts/omni.kit.window.environment/folders_hide_in_category",
            filter_file_suffixes=[".usd", ".usda", ".hdr"],
            ignore_folder_names=["Sky_Elements", "SubUSDs", "*props*"],
            custom_folders_setting=SETTING_CUSTOM_COLLECTION_ROOTS,
            **kwargs,
        )

        self._cached_scene_menu_items: Dict[Optional[CollectionItem], List[Tuple[str, str]]] = {}
        self.__templates_cache_file = carb.tokens.get_tokens_interface().resolve(
            "${omni_global_data}/omni.kit.window.environment.templates"
        )
        self.__sub_change = self.subscribe_item_changed_fn(lambda m, i: self.refresh_stage_templates(i))

    def destroy(self):
        self.__sub_change = None
        super().destroy()

    def filter_file(self, url: str) -> bool:
        valid = super().filter_file(url)
        if valid:
            dirs = url.split("/")
            name = dirs[-1].split(".")[0].lower()
            if name.endswith("_rt") or name.endswith("_pt"):
                # Ignore render settings
                return False
            else:
                return True
        return False

    def create_folder_object(self, *args, **kwargs):
        return EnvFolder(*args, **kwargs)

    def create_detail_item(self, file: BrowserFile) -> EnvDetailItem:
        return EnvDetailItem(file)

    def execute(self, item: EnvDetailItem) -> str:
        # Apply the sky to current stage
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return ""

        return self.__import_environment(item.type, item.url)

    def __import_environment(self, type: EnvType, url: str) -> str:
        sky_type = None
        if type == EnvType.USD:
            sky_type = SkyType.DYNAMIC
        elif type == EnvType.HDR:
            sky_type = SkyType.HDRI
        elif type == EnvType.TEMPLATE:
            sky_type = SkyType.SCENE
        else:
            return ""

        try:
            from omni.kit.actions.core import get_action_registry

            action = get_action_registry().get_action("omni.kit.environment.core", "import")
            if action:
                return action.execute(sky_type, url)
            else:
                return ""
        except ImportError:
            from omni.kit.environment.core import import_environment

            return import_environment(sky_type, url)

    def refresh_stage_templates(self, item: Optional[CollectionItem]) -> None:
        carb.log_info(f"Refresh templates")

        async def __delay_update_template_async():
            await omni.kit.app.get_app().next_update_async()
            try:
                from omni.kit.stage_templates import rebuild_stage_template_menu

                has_rebuild = True
            except ImportError:
                has_rebuild = False

            # unregister templates
            if item is None:
                for collection_item in self._cached_scene_menu_items:
                    await self._unregister_scene_category_templates(collection_item, has_rebuild=has_rebuild)
            elif item in self._cached_scene_menu_items:
                await self._unregister_scene_category_templates(item, has_rebuild=has_rebuild)

            # register template
            if item is None:
                collection_items = self.get_item_children(item)
                for collection_item in collection_items:
                    categories = self.get_item_children(collection_item)
                    for category_item in categories:
                        await self._register_scene_category_templates(category_item, has_rebuild=has_rebuild)
            elif isinstance(item, CollectionItem):
                categories = self.get_item_children(item)
                for category_item in categories:
                    await self._register_scene_category_templates(category_item, has_rebuild=has_rebuild)
            elif isinstance(item, CategoryItem):
                await self._register_scene_category_templates(item, has_rebuild=has_rebuild)

            unregister_cached_env_templates(has_rebuild=has_rebuild)

            if has_rebuild:
                rebuild_stage_template_menu()

            self.__save_templates()

        asyncio.ensure_future(__delay_update_template_async())

    async def _unregister_scene_category_templates(self, item: CollectionItem, has_rebuild: bool):
        extra_kwargs = {"rebuild": False} if has_rebuild else {}
        for name, _ in self._cached_scene_menu_items[item]:
            unregister_template(name, **extra_kwargs)
            if not has_rebuild:
                await omni.kit.app.get_app().next_update_async()

        self._cached_scene_menu_items[item] = []

    async def _register_scene_category_templates(self, category_item: CategoryItem, has_rebuild: bool) -> None:
        if category_item.name == "All":
            return

        if category_item not in self._cached_scene_menu_items:
            self._cached_scene_menu_items[category_item] = []
        detail_items: List[EnvDetailItem] = self.get_item_children(category_item)
        for detail_item in detail_items:
            if detail_item.type == EnvType.TEMPLATE:
                menuitem_name = os.path.splitext(detail_item.name)[0]
                register_env_template(menuitem_name, detail_item.url, has_rebuild)
                self._cached_scene_menu_items[category_item].append((menuitem_name, detail_item.url))
                if not has_rebuild:
                    await omni.kit.app.get_app().next_update_async()

    def __save_templates(self):
        templates_by_name = {}
        for _, templates in self._cached_scene_menu_items.items():
            for name, url in templates:
                templates_by_name[name] = url

        templates_cache_file = get_template_cache_file()
        try:
            with open(templates_cache_file, "w") as json_file:
                json.dump(templates_by_name, json_file, indent=4)
                if json_file:
                    json_file.close()
        except PermissionError:
            carb.log_error(f"Cannot write to {templates_cache_file}: permission denied!")
            return
        except Exception as exc:
            carb.log_error(f"Unknown failure to save to {templates_cache_file}: {exc}")
            return

        carb.log_info(f"Save {len(templates_by_name)} templates to cache")

    def _save_file_to_json(self, folder: EnvFolder, file: EnvFile) -> Dict:
        file_cache = super()._save_file_to_json(folder, file)
        file_cache["type"] = file.type
        return file_cache

    def _load_file_from_json(self, data: Dict, folder: EnvFolder) -> Optional[EnvFile]:
        thumbnail = data["thumbnail"] if data["thumbnail"] else None
        if thumbnail:
            thumbnail = folder.url + "/" + thumbnail
        elif self._hide_file_without_thumbnails:
            return None
        type = data["type"] if data["type"] else None
        return EnvFile(folder.url + "/" + data["url"], thumbnail, type=type)
