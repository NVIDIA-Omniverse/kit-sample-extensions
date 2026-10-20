# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
import functools
import json
import threading
import traceback
from itertools import chain
from typing import Callable, Dict, List, Optional

import carb
import omni.client as omni_client
import omni.ui as ui
import omni.usd
from omni.kit.async_engine import run_coroutine
from omni.kit.browser.core import CategoryItem, DetailItem
from omni.kit.browser.folder.core import (
    FileDetailItem,
    FileSystemFolder,
    FolderCategoryItem,
    FolderCollectionItem,
    TreeFolderBrowserModel,
)

from .asset import WrappAsset
from .browser_folder import WrappAssetFolder, WrappAssetLabelFolder
from .combobox_model import ComboBoxModel
from .consistents import WRAPP_EXPLORER_DRAG_PREFIX
from .utils import (
    add_asset_from_drag,
    get_stage_dir_and_name,
    get_wrapp_repo_config_url_for_stage,
    get_wrapp_url_for_stage,
    log_warning_with_notification,
    wrapp_install,
    wrapp_uninstall,
)


class WrappAssetDetailItem(DetailItem):
    """Represents a single WRAPP asset detail item in the browser.

    Manages the display and interaction state for a WRAPP asset including:
    - Version selection
    - Thumbnail display
    - Asset metadata presentation

    Args:
        asset (WrappAsset): The WRAPP asset to represent
    """

    def __init__(self, asset: WrappAsset):
        super().__init__(asset.name, asset.url, asset.thumbnail)
        self.asset = asset
        self._on_updated_fn: Callable[[], None] = None
        self._on_wrapp_progress_updated_fn: Callable[[float], None] = None
        self._progress_type: str | None = None
        self._wrapp_progress: float = 0.0

        # Version model
        if self.asset.versions:
            self.versions_model = ComboBoxModel(self.asset.versions, current_value=self.asset.version)
        else:
            self.versions_model = None

    @property
    def url(self) -> str:
        return self.asset.url

    @property
    def url_to_update(self) -> str:
        return self.asset.get_interface_usd_url(version=self.version_to_update)

    @property
    def thumbnail(self) -> str:
        return self.asset.thumbnail

    @property
    def thumbnail_to_update(self) -> str:
        """Get the thumbnail URLs for the url_to_update."""
        return self.asset.get_thumbnail_url(self.url_to_update)

    @property
    def version_to_update(self) -> str:
        return self.versions_model.current_value if self.versions_model else self.version

    @version_to_update.setter
    def version_to_update(self, value: str) -> None:
        if self.versions_model:
            self.versions_model.current_value = value

    @property
    def version(self) -> str:
        return self.asset.version

    @version.setter
    def version(self, value: str) -> None:
        if value not in self.asset.versions:
            carb.log_error(
                f"Failed setting asset '{self.asset.name}' to version {value}. It is not in available versions: {self.asset.versions}"
            )
            return
        self.asset.version = value

    @property
    def installed(self) -> bool:
        return self.asset.installed

    @property
    def wrapp_progress(self) -> float:
        return self._wrapp_progress

    @wrapp_progress.setter
    def wrapp_progress(self, value: float) -> None:
        self._wrapp_progress = value

    @property
    def progress_type(self) -> str:
        return self._progress_type

    @progress_type.setter
    def progress_type(self, value: str) -> None:
        self._progress_type = value

    def progress_updated(self, progress: float) -> None:
        self.wrapp_progress = progress
        if self._on_wrapp_progress_updated_fn:
            self._on_wrapp_progress_updated_fn(progress)

    def set_on_wrapp_progress_updated_fn(self, fn: Callable[[float], None]) -> None:
        """Set a callbable that will be called when the WRAPP progress is updated."""
        self._on_wrapp_progress_updated_fn = fn

    def remove_on_wrapp_progress_updated_fn(self) -> None:
        """Remove the callbable that will be called when the WRAPP progress is updated."""
        self._on_wrapp_progress_updated_fn = None

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

    async def update(self, version: str = None, run_on_updated: bool = False) -> None:
        if version:
            if version not in self.asset.versions:
                log_warning_with_notification(
                    f"Failed setting asset '{self.asset.name}' to version {version}. It is not in available versions: {self.asset.versions}"
                )
                return
            self.version_to_update = version

        # Get the current stage
        usd_context = omni.usd.get_context()
        if not usd_context:
            log_warning_with_notification("No USD context available. Cannot update asset.")
            return
        stage = usd_context.get_stage()
        if not stage:
            log_warning_with_notification("No stage available. Cannot update asset.")
            return

        try:
            self.progress_type = "Install"

            package_name = self.asset.name
            package_version = self.version_to_update
            install_root = get_stage_dir_and_name(stage)[0]
            relative_destination = self.asset.relative_destination
            install_dir = f"{install_root}/{relative_destination}"
            wrapp_repo_url = self.asset.wrapp_repo_url

            if not install_root:
                log_warning_with_notification(
                    f"No install path found for asset {package_name} version {package_version}. "
                    "Is current stage associated with a valid uri?"
                )
                return

            await wrapp_install(
                package_name=package_name,
                package_version=package_version,
                install_dir=install_dir,
                wrapp_repo_url=wrapp_repo_url,
                tags=False,
                progress_callback=self.progress_updated,
            )

            self.version = self.version_to_update
            # Currently this will trigger a refresh on the "Installed" folder if it is a version upgrade.
            if run_on_updated:
                self.on_updated()

        except Exception as e:
            msg = f"Failed to install asset {self.asset.name} version {self.version} ({self.url}) "
            log_warning_with_notification(msg)
            carb.log_error(traceback.format_exc())
        finally:
            self.progress_type = None

    async def uninstall(self) -> None:
        try:
            # Get the current stage
            usd_context = omni.usd.get_context()
            if not usd_context:
                log_warning_with_notification("No USD context available. Cannot uninstall asset.")
                return
            stage = usd_context.get_stage()
            if not stage:
                log_warning_with_notification("No stage available. Cannot uninstall asset.")
                return

            self.progress_type = "Uninstall"
            stage = omni.usd.get_context().get_stage()
            install_root = get_stage_dir_and_name(stage)[0]
            relative_destination = self.asset.relative_destination
            install_dir = f"{install_root}/{relative_destination}"

            await wrapp_uninstall(
                self.asset.name,
                package=self.asset.destination_wrapp,
                install_dir=install_dir,
                force=False,
                progress_callback=self.progress_updated,
            )
        finally:
            self.progress_type = None

    def set_thumbnail_not_found_fn(self, fn: Callable[[], None]) -> None:
        """Set a callbable that will be called when the Item thumbnail not found. Good for setting a default thumbnail."""
        self.asset.set_thumbnail_not_found_fn(fn)

    def set_interface_usd_url_found_fn(self, fn: Callable[[], None]) -> None:
        """Set a callbable that will be called when the default interface USD URL is not found
        and use the first USD in the package as the default USD URL. Good for logging and triggering an update.
        """
        self.asset.set_interface_usd_url_found_fn(fn)

    def set_on_updated_fn(self, fn: Callable[[], None]) -> None:
        """Set a callbable that will be called when the Item is updated,
        For example, when the asset is installed, call this to update Installed and out of date list.
        """
        self._on_updated_fn = fn

    def on_updated(self) -> None:
        if self._on_updated_fn:
            try:
                self._on_updated_fn()
            except Exception as e:
                carb.log_error(f"Error calling on_updated function: {e}")


class WrappBrowserModel(TreeFolderBrowserModel):
    """Model for managing WRAPP assets in the browser.

    Handles:
    - Asset folder traversal and caching
    - Asset version management
    - Drag and drop operations
    """

    def __init__(self, *args, **kwargs):
        super().__init__(show_summary_folder=True, *args, **kwargs)

        # Folder for labels, used to show as category item
        self._label_folders: Dict[str, FileSystemFolder] = {}

        self._subscription = []
        self._in_traverse_folders = []

        self._wrapp_dependencies_json = None
        self._wrapp_dependencies_folder = None
        self._wrapp_repo_config = None
        self._wrapp_repo_config_folder = None
        self._wrapp_project_config_folder = None
        self._background_loop = None
        self._start_refreshing_callback_fn = {}
        self._run_and_wait_coroutine(self.setup_wrapp_data_folders())
        self.subscribe_to_stage()  # Run refresh_asset_folders() when a stage is opened
        self._workspace_registered = False
        # Note: This is a MEGA Content Pipeline specific request
        self.register_to_workspace()

    @property
    def wrapp_dependencies_json(self) -> str:
        return self._wrapp_dependencies_json

    @wrapp_dependencies_json.setter
    def wrapp_dependencies_json(self, value: str) -> None:
        if value:
            value = omni_client.normalize_url(value)
        else:
            self._wrapp_dependencies_json = ""
            self._wrapp_dependencies_folder = None
            return

        if self._wrapp_dependencies_json == value:
            return
        self._wrapp_dependencies_json = value
        self._wrapp_dependencies_folder = self._create_folder_object_by_url(
            "wrapp_installed", self._wrapp_dependencies_json, on_traversed_fn=self._on_folder_traversed, root=True
        )

    @property
    def wrapp_repo_config(self) -> str:
        return self._wrapp_repo_config

    @wrapp_repo_config.setter
    def wrapp_repo_config(self, value: str) -> None:
        if value:
            value = omni_client.normalize_url(value)
        else:
            self._wrapp_repo_config = ""
            self._wrapp_repo_config_folder = None
            return

        if self._wrapp_repo_config == value:
            return
        self._wrapp_repo_config = value
        self._wrapp_repo_config_folder = self._create_folder_object_by_url(
            "wrapp_repo_config", self._wrapp_repo_config, on_traversed_fn=self._on_folder_traversed, root=True
        )

    @property
    def wrapp_dependencies_folder(self) -> FileSystemFolder:
        return self._wrapp_dependencies_folder

    @property
    def wrapp_repo_config_folder(self) -> FileSystemFolder:
        return self._wrapp_repo_config_folder

    @property
    def wrapp_project_config_uri(self) -> List[str]:
        try:
            from omni.cip.workspace import ProjectModel
        except ImportError:
            return

        return ProjectModel().project_uri

    @property
    def wrapp_project_config_folder(self) -> FileSystemFolder:
        if not self.wrapp_project_config_uri:
            return None

        if self._wrapp_project_config_folder:
            return self._wrapp_project_config_folder

        self._wrapp_project_config_folder = self._create_folder_object_by_url(
            "wrapp_project_config",
            self.wrapp_project_config_uri,
            on_traversed_fn=self._on_folder_traversed,
            root=True,
        )
        return self._wrapp_project_config_folder

    def _start_background_loop(self):
        self._background_loop = asyncio.new_event_loop()
        background_loop_thread = threading.Thread(target=self._background_loop.run_forever, daemon=True)
        background_loop_thread.start()
        return self._background_loop

    def _run_coroutine_in_background_loop(self, coro) -> asyncio.Future:
        if not self._background_loop:
            self._start_background_loop()
        return asyncio.run_coroutine_threadsafe(coro, self._background_loop)

    def _run_and_wait_coroutine(self, coro):
        return self._run_coroutine_in_background_loop(coro).result()

    def _run_start_refreshing_callback_fns(self):
        if self._start_refreshing_callback_fn.values():
            for fn in self._start_refreshing_callback_fn.values():
                fn()

    @property
    def folders_to_traverse(self) -> List[FileSystemFolder]:
        folders_to_traverse = []

        # OMPE-56740
        # The order of the folders is important. The front folder will take precedence over the back folder.
        # For example, if both wrapp_repo_config_folder and wrapp_project_config_folder are present,
        # and both define the same repo with different install paths,
        # then the install path from wrapp_repo_config_folder will be used.

        # Wrapp config from USD stage directory - usually the .wrapp_repo.config
        if self.wrapp_repo_config_folder and self.wrapp_repo_config_folder.url:
            folders_to_traverse.append(self.wrapp_repo_config_folder)

        # Installed packages
        if self.wrapp_dependencies_folder and self.wrapp_dependencies_folder.url:
            folders_to_traverse.append(self.wrapp_dependencies_folder)

        # project config repos - .wrapp_project.config
        if self.wrapp_project_config_folder and self.wrapp_project_config_folder.url:
            folders_to_traverse.append(self.wrapp_project_config_folder)

        return folders_to_traverse

    async def setup_wrapp_data_folders(self, wrapp_dependencies_json="", wrapp_repo_config=""):
        """Create the wrapp data folders for traversing.
        If wrapp_dependencies_json or wrapp_repo_config is provided, use it instead of fetching the wrapp data files from current stage.
        """
        # If the stage is an in-memory stage, we do not need to fetch the wrapp data
        self.wrapp_dependencies_json, self.wrapp_repo_config = wrapp_dependencies_json, wrapp_repo_config
        try:
            if omni.usd.get_context().get_stage().GetRootLayer().realPath:
                if not self.wrapp_dependencies_json:
                    self.wrapp_dependencies_json = await get_wrapp_url_for_stage()
                if not self.wrapp_repo_config:
                    self.wrapp_repo_config = await get_wrapp_repo_config_url_for_stage()
        except Exception:
            pass

    def _on_stage_opened(self, *args, **kwargs) -> None:
        """Handle stage events.

        Args:
            event (omni.usd.StageEventType): The stage event to handle
        """
        self.refresh_asset_folders()

    def subscribe_to_stage(self) -> None:
        """Subscribe to stage events"""
        subscription = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="Wrapp Browser Model Stage Open Event",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
        )
        self._subscription.append(subscription)

    def _traverse_folders(self) -> None:
        """Traverse root folders"""
        # Traverse active root folder if necessary
        folders_to_traverse = self.folders_to_traverse

        if not folders_to_traverse:
            return

        # Start refreshing animation
        self._run_start_refreshing_callback_fns()

        for folder in folders_to_traverse:
            if not self._folder_cache.get(folder) or not folder.prepared:
                self.start_traverse(folder)

    def register_to_workspace(self, force: bool = False) -> None:
        if self._workspace_registered and not force:
            return

        try:
            from omni.cip.workspace import ProjectModel
        except ImportError:
            carb.log_verbose("No omni.cip.workspace module available.")
            return

        try:
            project_model = ProjectModel()
            if hasattr(project_model, "register_workspace_changed_callback"):
                project_model.register_workspace_changed_callback(
                    lambda _: self.refresh_asset_folders(), "package_explorer"
                )
            else:
                project_model.register_repo_changed_callback(self.refresh_asset_folders)
            self._workspace_registered = True
        except Exception:
            carb.log_error("Failed to register to workspace.")

    def refresh_asset_folders(self, wrapp_dependencies_json="", wrapp_repo_config="", use_cache: bool = True) -> None:
        """Refresh all asset folders in the browser."""
        if not use_cache:
            WrappAssetFolder.clear_wrapp_url_caches()

        self._run_and_wait_coroutine(self.refresh_asset_folders_async(wrapp_dependencies_json, wrapp_repo_config))

    async def refresh_asset_folders_async(self, wrapp_dependencies_json="", wrapp_repo_config="") -> None:
        """Refresh all asset folders in the browser."""
        # Start refreshing animation
        self._run_start_refreshing_callback_fns()

        self._label_folders = {}
        # If the stage is an in-memory stage, we do not need to fetch the wrapp data
        await self.setup_wrapp_data_folders(wrapp_dependencies_json, wrapp_repo_config)
        for folder in self.folders_to_traverse:
            self.start_traverse(folder, force=True)

    def set_start_refreshing_callback_fn(self, fn: Callable[[], None], name: str) -> None:
        """Set a callable that will be called when the refreshing starts."""
        self._start_refreshing_callback_fn[name] = fn

    def start_traverse(self, folder: FileSystemFolder, force: bool = False) -> None:
        """Start traversing a folder.

        Args:
            folder (FileSystemFolder): The folder to traverse
            force (bool, optional): Whether to force traversal even if already in queue.
                Defaults to False.
        """
        # Categories comes from __Label_folders, need to clean for a new traverse
        if folder.url not in self._traverse_in_queue or force:
            for label in folder.asset_by_labels:
                if label in self._label_folders:
                    del self._label_folders[label]
            if folder.url not in self._traverse_in_queue:
                self._traverse_in_queue.append(folder.url)
            if folder not in self._in_traverse_folders:
                self._in_traverse_folders.append(folder)
            self._work_queue.put_nowait(folder)

    def is_in_traversing(self) -> bool:
        if self._work_queue and not self._work_queue.empty():
            return True
        else:
            return not all(folder.prepared for folder in self._in_traverse_folders)

    def get_drag_mime_data(self, item: WrappAssetDetailItem = None) -> str:
        if item:
            drag_data = {
                "name": item.asset.name,
                "version": item.version_to_update,
                "url": item.url_to_update,
                "wrapp_repo_url": item.asset.wrapp_repo_url,
                "relative_destination": item.asset.relative_destination,
                "target_package": item.asset.destination_wrapp,
            }
            return WRAPP_EXPLORER_DRAG_PREFIX + json.dumps(drag_data)
        return super().get_drag_mime_data(item)

    def execute(self, item: WrappAssetDetailItem) -> None:
        drag_mime_data = self.get_drag_mime_data(item)
        add_asset_from_drag(drag_mime_data)

    def create_folder_object(self, *args, **kwargs):
        return WrappAssetFolder(*args, **kwargs)

    def _on_folder_traversed(
        self, folder: WrappAssetFolder, loading_completed=True, updated: bool = True, force: bool = False
    ) -> None:
        """
        Folder traversed,
        - Update tags and view
        - Save data to cache
        """
        try:
            self._in_traverse_folders.remove(folder)
        except ValueError:
            pass

        if updated:
            # Update tags
            self._update_labels(folder)
            # Refresh view
            if force or not self._in_traverse_folders:
                self.folder_changed(None)
        carb.log_info(f"Traverse completed: {folder.url}")

    async def _reload_label_folder_async(self, folder: WrappAssetLabelFolder) -> None:
        # Clean cache label folders related to the label
        for key in list(self._label_folders.keys()):
            if folder.name in key:
                self._label_folders.pop(key, None)

        # Start refreshing animation
        self._run_start_refreshing_callback_fns()

        # Traverse the source folders of the label folder
        traverse_tasks = []
        for source_folder in folder.source_folders:
            traverse_tasks.append(source_folder.start_traverse())
        await asyncio.gather(*traverse_tasks)

    def _reload_label_folder(self, folder: WrappAssetLabelFolder) -> None:
        run_coroutine(self._reload_label_folder_async(folder))

    def _update_labels(self, folder: WrappAssetFolder) -> None:
        # If not force, and there are still folders are in traverse queue, do not update labels
        for label, assets in folder.asset_by_labels.items():
            if not label:
                continue

            if new_folder := label not in self._label_folders:
                label_folder = WrappAssetLabelFolder(label, folder)
                label_folder.set_reload_fn(functools.partial(self._reload_label_folder, label_folder))
                self._label_folders[label] = label_folder
            else:
                # Update the source folder of the existing label folder
                self._label_folders[label].add_source_folder(folder)

            self._label_folders[label].files.extend(assets)
            # Clean cache to re-generate category items
            self._folder_cache[self._label_folders[label]] = None

            # Create parent label folders
            while new_folder:
                pos = label.rfind("/")
                if pos <= 0:
                    break
                parent_label = label[:pos]
                if parent_label not in self._label_folders:
                    label_folder = WrappAssetLabelFolder(parent_label, folder)
                    label_folder.set_reload_fn(functools.partial(self._reload_label_folder, label_folder))
                    self._label_folders[parent_label] = label_folder
                else:
                    self._label_folders[parent_label].add_source_folder(folder)

                child_label_folder = self._label_folders[label]
                if child_label_folder not in self._label_folders[parent_label].sub_folders:
                    self._label_folders[parent_label].sub_folders.append(child_label_folder)
                    self.sort_items(self._label_folders[parent_label].sub_folders)
                label = parent_label

        # Sort and remove duplicates
        for label_folder in self._label_folders.values():
            label_folder.files = list(set(label_folder.files))
            label_folder.files.sort(key=lambda x: x.name)

    def create_detail_item(self, asset: WrappAsset) -> FileDetailItem:
        """
        Create detail item(s) from a file.
        A file may include multi detail items.
        Args:
            file (BrowserFile): File object to create detail item(s)
        """
        return WrappAssetDetailItem(asset)

    def destroy(self):
        while self._subscription:
            subscription = self._subscription.pop()
            subscription.reset()
        if self._background_loop:
            self._background_loop.call_soon_threadsafe(self._background_loop.stop)
            self._background_loop = None
        super().destroy()

    def sort_items(self, items: List[WrappAssetDetailItem]) -> None:
        # We want these special folders to be at the top
        items.sort(
            key=lambda item: (
                0 if item.name == "Installed" else 1 if item.name == "Installed/Out of Date" else 2,
                item.name,
            )
        )

    def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]:
        # Traverse active root folder if necessary
        if item.name == "TreeRoot":
            self._traverse_folders()

        # Create category item from labels
        category_items: List[FolderCategoryItem] = []
        root_folders = [folder for folder in self._label_folders.values() if folder.name.find("/") < 0]
        summary_count = 0
        for folder in root_folders:
            if folder not in self._folder_cache:
                category_item = self._create_folder_category_item(folder)
                self._folder_cache[folder] = category_item
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

    def _get_summary_detail_items(self) -> List[FileDetailItem]:
        # List all assets from label folder
        root_folders = [folder for folder in self._label_folders.values() if folder.name.find("/") < 0]
        return list(chain.from_iterable([self.get_detail_items(self._folder_cache[f]) for f in root_folders]))

    def reload_installed_folder(self) -> None:
        """Reload the installed folder."""
        installed_folder = self._label_folders.get("Installed")
        if installed_folder:
            installed_folder.reload()


class DetailListViewModel(ui.AbstractItemModel):
    """
    Model wrapper that adapts the detail model for use with TreeView.
    Provides a flat list of detail items.
    """

    def __init__(self):
        super().__init__()
        self._items = []
        self._source_model = None

    def set_items(self, items):
        """Set the items to display in the list view."""
        self._items = items or []
        self._item_changed(None)

    def get_item_children(self, parent_item):
        """Return all items for root (parent_item=None), empty for others."""
        if parent_item is None:
            return self._items
        return []

    def get_item_value_model_count(self, item):
        """Single column for the list view."""
        return 1

    def get_item_value_model(self, item, column_id):
        """Return a value model for the item."""
        if item is not None and column_id == 0:
            return item
        return None
