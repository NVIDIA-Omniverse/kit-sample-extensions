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
from itertools import chain
from typing import Dict, List, Optional, Union

import carb
import carb.settings
import omni.kit.app
from omni.kit.browser.core import CategoryItem

from .folder_browser_data import AbstractBrowserFolder, BrowserFile, FileSystemFolder, TraverseStatus
from .folder_browser_item import FileDetailItem, FolderCategoryItem, FolderCollectionItem
from .folder_browser_model import FolderBrowserModel

# Longest the summary view may lag the scan behind it. Coalescing to a frame still means a full
# rebuild every frame, each proportional to every material found so far; four a second reads as
# live and costs an order of magnitude less.
SUMMARY_REFRESH_INTERVAL = 0.25
# While a scan runs the view is changing wholesale anyway, and each refresh walks every retained
# folder in every collection - expensive enough to dominate the frame budget even while finding
# nothing. A second is still live enough to watch and cuts that traffic fourfold.
SUMMARY_REFRESH_INTERVAL_SCANNING = 1.0

# The same for the collection item, which is the heavier notification: it evicts the cached children
# of the whole tree, so the next query rebuilds every detail item and sorts them on a key that reads
# a pybind property per item. A traverse reports one per folder that ends with changes, and stack
# captures of a frozen scan put the main thread in that chain more than anywhere else.
COLLECTION_REFRESH_INTERVAL = 0.25
COLLECTION_REFRESH_INTERVAL_SCANNING = 1.0


class TreeFolderBrowserModel(FolderBrowserModel):
    def __init__(self, *args, **kwargs):
        self.__summary_item = None
        # Pending coalesced refresh of the summary item, or None. See __request_summary_refresh.
        self.__summary_refresh_task = None
        self.__summary_refreshed_at = 0.0
        # Pending coalesced refresh of the collection item. See _request_collection_refresh.
        self.__collection_refresh_task = None
        self.__collection_refreshed_at = 0.0
        setting_folders_hide_in_category = kwargs.pop("setting_folders_hide_in_category", None)
        self.__folders_hide_in_category = (
            carb.settings.get_settings().get(setting_folders_hide_in_category)
            if setting_folders_hide_in_category
            else []
        )

        super().__init__(*args, **kwargs)

    def process_root_folder(self, root_folder: str, sync: bool = True) -> Optional[FileSystemFolder]:
        folder = super().process_root_folder(root_folder, sync=sync)

        # Hide root folder in category view only for default folders
        if folder and folder.name in self.__folders_hide_in_category:
            folder.hide_root_in_category = True
        return folder

    def remove_collection(self, item: FolderCollectionItem) -> bool:  # pragma: no cover
        # Only one default collection item and could not be removed
        pass

    def get_collection_items(self) -> List[FolderCollectionItem]:
        """Override to get list of collection items"""
        # Treeview mode, create a default collection item
        if self._root_collection_item is None:
            self._root_collection_item = FolderCollectionItem("TreeRoot", "", None)

        # Load folders from local cache
        self._load_data_from_json()

        return [self._root_collection_item]

    def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]:
        """
        Create category item for every root folder.
        Also create category items for sub folders as children of parent category item.
        Summary category item will be created if required.
        """
        category_items: List[FolderCategoryItem] = []

        for root_folder in self._root_folders:
            category_item = self._folder_cache.get(root_folder)

            if category_item is None:
                category_item = self._create_folder_category_item(root_folder)
                # Name contains sub categories, create full category item chain
                if len(root_folder.name.split("/")) > 1:
                    category_item = self._create_category_item_chain(root_folder, category_items)
                    if category_item:
                        self.sort_items(category_item.children)
            else:
                # Get root category item
                parent = category_item.parent
                while parent:
                    category_item = parent
                    parent = parent.parent

            if category_item and category_item not in category_items:
                if root_folder.hide_root_in_category and len(category_item.children) > 0:
                    # When hide root in category view, only hide root item when prepared or laded from cache
                    category_items.extend(category_item.children)
                else:
                    category_items.append(category_item)
            if category_item:
                if not self._json_file or not hasattr(root_folder, "has_cache") or not root_folder.has_cache:
                    # Not in cache
                    if not root_folder.prepared:
                        # No traversed
                        self.start_traverse(root_folder)

        self.sort_items(category_items)

        if self._show_summary_folder:
            summary_count = sum([c.count for c in category_items])
            self.__summary_item = CategoryItem(self.SUMMARY_FOLDER_NAME, summary_count)
            category_items.insert(0, self.__summary_item)

        return category_items

    def __request_summary_refresh(self) -> None:
        """
        Ask for one summary refresh soon, however many times this is called.

        The summary item's children are every detail item in every root folder, rebuilt from
        scratch and sorted on each notification - see :meth:`_get_summary_detail_items`. A traverse
        reports a status for every folder it discovers, and this runs on the event loop inside that
        traverse, so notifying per folder costs folders x items and holds the loop for the whole
        rebuild: the app stops ticking, and the scan appears to hang. Collapsing them
        to a few a second shows the user exactly the same thing.

        The count itself is updated eagerly by the caller. Only the notification waits.
        """
        if self.__summary_refresh_task is not None:
            return
        self.__summary_refresh_task = asyncio.ensure_future(self.__refresh_summary_async())

    async def __refresh_summary_async(self) -> None:
        try:
            interval = SUMMARY_REFRESH_INTERVAL_SCANNING if self.active_folders else SUMMARY_REFRESH_INTERVAL
            waited = time.time() - self.__summary_refreshed_at
            if waited < interval:
                await asyncio.sleep(interval - waited)
            await omni.kit.app.get_app().next_update_async()
            # Re-read the item rather than capturing it: get_category_items builds a new
            # CategoryItem every time it runs, so one held across a frame can already have been
            # replaced. Notifying the stale one is how an earlier attempt at this failed.
            item = self.__summary_item
            if item is not None:
                self._item_changed(item)
            self.__summary_refreshed_at = time.time()
        finally:
            # No except: a cancel - destroy, or a model going away mid-sleep - ends this task, and
            # swallowing it would tell the loop the task ran to completion. The slot is cleared
            # either way, so the next request starts a new one.
            self.__summary_refresh_task = None

    def destroy(self):
        if self.__summary_refresh_task is not None:
            self.__summary_refresh_task.cancel()
            self.__summary_refresh_task = None
        if self.__collection_refresh_task is not None:
            self.__collection_refresh_task.cancel()
            self.__collection_refresh_task = None
        super().destroy()

    def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]:
        """Override to get list of detail items"""
        if item.name == self.SUMMARY_FOLDER_NAME:
            return self._get_summary_detail_items()
        elif isinstance(item, FolderCategoryItem):
            # List files in item folder
            if item.folder.hide_root_in_category:
                # For root folder that hidden in category view, get detail items from sub folders
                detail_items = []
                for sub_folder in item.folder.sub_folders:
                    detail_items += self._get_folder_detail_items(sub_folder)
                    if not self._show_category_subfolders:
                        for child in sub_folder.sub_folders:
                            detail_items += self._get_folder_detail_items(child)
            else:
                detail_items = self._get_folder_detail_items(item.folder)

                # In tree mode, for root folders, show items in sub folders
                if not detail_items:
                    if item.folder in self._root_folders:
                        for sub_folder in item.folder.sub_folders:
                            detail_items += self._get_folder_detail_items(sub_folder)
                    else:
                        pos = item.folder.url.rfind("/")
                        parent_url = item.folder.url[:pos]

                        for root_folder in self._root_folders:
                            if root_folder.hide_root_in_category:
                                if parent_url == root_folder.url:
                                    for sub_folder in item.folder.sub_folders:
                                        detail_items += self._get_folder_detail_items(sub_folder)
        else:
            detail_items = super().get_detail_items(item)

        self.sort_items(detail_items)
        return detail_items

    def folder_changed(self, item: Union[AbstractBrowserFolder, BrowserFile, None]) -> None:
        """
        Notify folder or file changed.
        Args:
            item (Union[AbstractBrowserFolder, BrowserFile]): Changed folder or file object.
        """

        def refresh_category_status():
            browser_item = self._folder_cache.get(item, None)
            if browser_item:
                self._item_changed(browser_item)

        if item is None:
            # Clean all folder cache and refresh the collection item
            self._folder_cache = {}
            self._item_changed(self._root_collection_item)
        elif item.hide_root_in_category:
            if item.prepared:
                if hasattr(item, "has_update") and not item.has_update and item.prepared:
                    # Folder traverse done without changes, only refresh category items for loading status
                    refresh_category_status()
                else:
                    # Folder traverse done: drop the browser items and refresh the collection item,
                    # keeping the rows of collections that are still scanning. Dropping the cache is
                    # a dict rebuild; the notification that follows is coalesced.
                    self._folder_cache = self.__keep_rows_still_scanning()
                    self._request_collection_refresh()

                    # Cache writes moved to the terminal path in FolderBrowserModel, which is the
                    # only place that knows the whole traverse succeeded. Saving here as well
                    # wrote the cache twice per traverse, and wrote it for failed ones too.
            else:
                # Folder in traversing, refresh category item to show loading
                refresh_category_status()
        else:
            if item not in self._root_folders:
                # Removed. Asked first because it outranks anything the traverse left behind: the
                # row is already out of the cache, so there is nothing to refresh in place. A
                # cancelled collection used to fall into the branch below - cancelling marks it
                # prepared, and it has no updates - which left the removed row on screen.
                self._item_changed(self._root_collection_item)
            elif hasattr(item, "has_update") and not item.has_update and item.prepared:
                refresh_category_status()
            elif self._folder_cache.get(item, None) is None:
                # Root folder removed, refresh collection item
                self._item_changed(self._root_collection_item)

    def __keep_rows_still_scanning(self) -> dict:
        """
        What survives emptying the browser item cache: the rows of collections still working.

        One collection finishing used to throw away every row, including those of collections still
        scanning - and a row that no longer exists draws nothing, so their spinner vanished.

        active_folders is the model's own answer to which collections are still working, and it is
        what sets a row's loading flag in the first place, so matching on it keeps the two in step.
        Matched by url prefix, because the cache is keyed by sub folder while active_folders holds
        roots. Not by traverse context: a context turns terminal before the model drops the
        collection, so rows would still be discarded in the window between.
        """
        if not self.active_folders:
            return {}
        roots = [f.url.rstrip("/") for f in self.active_folders if getattr(f, "url", None)]
        keep = {}
        for key, item in self._folder_cache.items():
            url = getattr(key, "url", None)
            if not url:
                # A file, keyed by file rather than folder: the content the finishing traverse just
                # changed, so it is dropped.
                continue
            url = url.rstrip("/")
            if any(url == root or url.startswith(root + "/") for root in roots):
                keep[key] = item
        return keep

    def _request_collection_refresh(self) -> None:
        """
        Ask for one collection refresh soon, however many times this is called.

        Notifying the collection item is the most expensive notification the model makes: it evicts
        the cached children of the whole tree, so the next query rebuilds every detail item and
        sorts them on a pybind property read per item. A traverse raises one per folder that ended
        with changes, on the event loop inside that traverse, so a drive scan spends its time
        rebuilding a view nobody has seen yet.

        Only while a scan is running: otherwise there is no flood to collapse and the notification
        is a change the user just made. The caller still drops the cache eagerly, so anything that
        asks in the meantime gets fresh data - only the notification waits.
        """
        if not self.active_folders:
            # Nothing is scanning, so this is a change the user made - adding or removing a
            # collection - and there is no flood to collapse. Delaying it only makes the browser
            # feel slow, and it showed up as a stale screenshot in test_2_add_remove_root.
            item = self._root_collection_item
            if item is not None:
                self._item_changed(item)
            self.__collection_refreshed_at = time.time()
            return
        if self.__collection_refresh_task is not None:
            return
        self.__collection_refresh_task = asyncio.ensure_future(self.__refresh_collection_async())

    async def __refresh_collection_async(self) -> None:
        try:
            interval = COLLECTION_REFRESH_INTERVAL_SCANNING if self.active_folders else COLLECTION_REFRESH_INTERVAL
            waited = time.time() - self.__collection_refreshed_at
            if waited < interval:
                await asyncio.sleep(interval - waited)
            await omni.kit.app.get_app().next_update_async()
            # Re-read rather than capture, for the reason __refresh_summary_async gives: an item
            # held across a frame can already have been replaced.
            item = self._root_collection_item
            if item is not None:
                self._item_changed(item)
            self.__collection_refreshed_at = time.time()
        finally:
            self.__collection_refresh_task = None

    def __refresh_category_item(self, item: FolderCategoryItem, recurse: bool = True) -> bool:
        # Refresh category item
        # - For category itself, refresh count, reset browser cache
        # - For sub folders
        #     * if browser item already exists, refresh count
        #     * otherwise create a new browser item

        # Refresh children
        category_count = 0
        sub_category_items = []
        for sub in item.folder.sub_folders:
            sub_item = self._folder_cache.get(sub, None)
            if sub_item:
                if sub.has_update and recurse:
                    self.__refresh_category_item(sub_item)
            else:
                sub_item = self._create_folder_category_item(sub)
            if sub_item:
                sub_category_items.append(sub_item)
                sub_item.parent = item
                category_count += sub_item.count
        category_count += item.folder.file_item_count

        # Reset count
        count_changed = item.count != category_count
        item.count = category_count

        # Reset children
        remove_children = [child for child in item.children if child not in sub_category_items]
        for child in remove_children:
            if child.folder:
                self._folder_cache.pop(child.folder, None)
        children = sorted(sub_category_items, key=lambda x: x.name)
        children_changed = children != item.children
        item.children = children

        # Tell the view only when there is something to see. This runs once per folder discovered,
        # and on a drive most hold nothing this browser shows: 380 of 678 refreshes left the row
        # identical and rebuilt it anyway, spinner included.
        if count_changed or children_changed:
            self._item_changed(item)
            return True
        return False

    def __refresh_category_train(
        self, folder: AbstractBrowserFolder, status: TraverseStatus, recurse: bool = True
    ) -> None:
        # A folder changed, need to refresh category view for category item and parent items
        browser_item = self._folder_cache.get(folder, None)
        if status == TraverseStatus.START:
            # Only refresh loading status
            if browser_item:
                browser_item.loading = True
                self._item_changed(browser_item)
                return
        loading_changed = False
        if status == TraverseStatus.COMPLETED:
            # First refresh loading status here, update category item later
            if browser_item and browser_item.loading:
                browser_item.loading = False
                loading_changed = True

        if folder in self._root_folders and folder.hide_root_in_category:
            # To hide root item in category view, use sub folders instead
            self._folder_cache.pop(folder, None)
            self._item_changed(self._root_collection_item)
            return

        if browser_item:
            # Treeview mode, need to refresh category view to show sub folders

            # Notification for prepare refresh categories
            if self.on_refresh_categories:
                self.on_refresh_categories()

            old_count = browser_item.count

            # Refresh category item and its children (sub folders)
            notified = self.__refresh_category_item(browser_item, recurse=recurse)
            if loading_changed and not notified:
                # The counts and children may be identical - a collection that finished having
                # found nothing new - but its spinner still has to stop, and only a rebuild stops
                # it, so the flag changing is itself a reason to publish.
                self._item_changed(browser_item)

            if old_count != browser_item.count:
                # Update count in parent items
                parent = browser_item.parent
                while parent:
                    parent.count += browser_item.count - old_count
                    self._item_changed(parent)
                    parent = parent.parent

                # Finally, need to update summary item
                if self.__summary_item:
                    self.__summary_item.count += browser_item.count - old_count
                    self.__request_summary_refresh()
        else:
            # Either new root folder or root folder removed, just refresh the collection item
            self._item_changed(self._root_collection_item)

    def _on_folder_traversed(self, folder: AbstractBrowserFolder, loading_completed=True, updated: bool = True) -> None:
        """
        Folder traversed,
        - Update category and detail widgets
        - Save data to cache
        """
        carb.log_info(f"Traverse completed: {folder.url}, {loading_completed}")

        # The cache write that used to live here moved to the terminal path, so that exactly one
        # save happens per successful root traverse and none happens for a failed one.

        if updated and not folder.hide_root_in_category:
            # Visible roots only. A hidden root has no row of its own to hold a stale count - its
            # sub folders are the categories - and __refresh_category_train would take the branch
            # that drops the whole folder cache and publishes the collection item on the spot,
            # uncoalesced. The work that follows does that properly anyway: folder_changed keeps
            # the rows still scanning and asks _request_collection_refresh, from the same
            # post-cleanup state.
            #
            # Recount from what the folder ended up holding. The COMPLETED status that drove the
            # last refresh is raised before _is_folder_updated drops the files the listing no
            # longer returned, so the count published there still counts a file that is gone. A
            # sub folder is rescued by its parent, whose own COMPLETED arrives after that cleanup;
            # a root has no parent, and its row and the summary kept the stale number.
            #
            # Only roots get here - sub folders are not given this callback - so this is one
            # recount per root per traverse, and only when something actually changed. The summary
            # rebuild it can ask for is the coalesced one, capped at once a second while scanning.
            #
            # recurse=False keeps it that cheap. Every sub folder was cleaned up and recounted
            # before this, so only the root's own files are in question: this adds up the children
            # it already has, and does not walk the tree again. Measured over 900 folders, the
            # recursive form of this one call cost 10.8 ms in a single frame.
            #
            # And only when the number actually moved. Refreshing raises on_refresh_categories,
            # where the widget snapshots the selection to restore it afterwards - and it can only
            # snapshot a FolderCategoryItem, so with the summary row selected it keeps the folder
            # selected before that one and restores it over the top. A scan that dropped nothing
            # would have bounced the user off "All" for no change at all.
            item = self._folder_cache.get(folder, None)
            if item is not None and item.count != self.__root_count_now(item, folder):
                self.__refresh_category_train(folder, TraverseStatus.COMPLETED, recurse=False)

    def __root_count_now(self, item: FolderCategoryItem, folder: AbstractBrowserFolder) -> int:
        """What the row would count if it were rebuilt from the state the traverse left behind."""
        return sum(child.count for child in item.children) + folder.file_item_count

    def _save_file_to_json(self, folder: AbstractBrowserFolder, file: BrowserFile) -> Dict:
        file_cache = {
            "url": os.path.relpath(file.url, folder.url),
            "thumbnail": os.path.relpath(file.thumbnail, folder.url).replace("\\", "/") if file.thumbnail else "",
        }
        return file_cache

    def _save_folder_to_json(
        self, folder: AbstractBrowserFolder, parent: Optional[AbstractBrowserFolder] = None
    ) -> Dict:
        output = {
            "url": os.path.relpath(folder.url, parent.url) if parent else folder.url,
            "sub_folders": {},
            "files": {},
        }
        # sub folders
        for sub_folder in folder.sub_folders:
            output["sub_folders"][sub_folder.name] = self._save_folder_to_json(sub_folder, folder)

        # files
        for file in folder.files:
            dirs = file.url.split("/")
            name = dirs[-1]
            output["files"][name] = self._save_file_to_json(folder, file)

        return output

    def _load_file_from_json(self, data: Dict, folder: AbstractBrowserFolder) -> Optional[BrowserFile]:
        thumbnail = data["thumbnail"] if data["thumbnail"] else None
        if thumbnail:
            thumbnail = folder.url + "/" + thumbnail
        elif self._hide_file_without_thumbnails:
            return None
        return BrowserFile(folder.url + "/" + data["url"], thumbnail)

    def _load_folder_from_json(self, data: Dict, folder: AbstractBrowserFolder):
        files = data.get("files", {})
        if files:
            for file_data in files.values():
                file = self._load_file_from_json(file_data, folder)
                if file:
                    folder.files.append(file)

        if folder._ignore_sub_folder_with_files and folder.files:
            # This is already done when traverse folder now.
            # But in some test machiness, still cached with full data.
            # Could be removed later
            return

        sub_folders = data.get("sub_folders", {})
        if sub_folders:
            for name, sub in sub_folders.items():
                sub_folder_url = folder.url + "/" + sub["url"]
                sub_folder = self._create_folder_object_by_url(name, sub_folder_url)
                self._load_folder_from_json(sub_folders[name], sub_folder)
                folder.sub_folders.append(sub_folder)

        if folder.hide_root_in_category:
            # Refresh root folder to sync with new/deleted folder
            async def __refresh_root_folder():
                for _ in range(4):
                    await omni.kit.app.get_app().next_update_async()
                self.start_traverse(folder)

            asyncio.ensure_future(__refresh_root_folder())

    def _create_folder_category_item(self, folder: AbstractBrowserFolder) -> Optional[FolderCategoryItem]:
        """
        Create category item for a folder.
        Return None if no sub folder and files in folder.
        Otherwise return created category item.
        """
        # Count all sub folders and files
        category_count = 0
        sub_category_items = []
        for sub in folder.sub_folders:
            sub_category_item = self._create_folder_category_item(sub)
            if sub_category_item:
                sub_category_items.append(sub_category_item)
                category_count += sub_category_item.count
        category_count += folder.file_item_count

        # Create category item
        names = folder.name.split("/")
        if category_count > 0 or folder.has_timeout:
            category_item = FolderCategoryItem(names[-1], category_count, folder)
        elif folder in self._root_folders:
            # Empty, but since it is root folder, still show it with count = 0
            category_item = FolderCategoryItem(names[-1], 0, folder)
        elif not folder.prepared:
            # Folder in loading, still show for loading progress
            category_item = FolderCategoryItem(names[-1], 0, folder)
        else:
            return None
        # A collection that is queued or scanning is born showing it. The flag is normally carried
        # on the item, but the item does not always survive the scan: folder_changed clears the
        # folder cache when a hidden-root collection finishes, so another collection still scanning
        # has its row rebuilt and would come back with its spinner off.
        category_item.loading = folder in self.active_folders

        category_item.children = sub_category_items
        for sub_item in sub_category_items:
            sub_item.parent = category_item
        self._folder_cache[folder] = category_item

        return category_item

    def __find_category_item_by_name(
        self, name: str, root_category_items: List[FolderCategoryItem]
    ) -> Optional[FolderCategoryItem]:
        names = name.split("/")
        found = None
        for name in names:
            for item in root_category_items:
                if item.name.lower() == name.lower():
                    root_category_items = item.children
                    found = item
                    break
            else:
                return None

        return found

    def _create_category_item_chain(
        self, folder: AbstractBrowserFolder, root_category_items: List[FolderCategoryItem]
    ) -> Optional[FolderCategoryItem]:
        # Folder name includs sub categories, create item one by one adding count of current folder
        exist_category_item = self.__find_category_item_by_name(folder.name, root_category_items)
        if exist_category_item:
            return None
        names = folder.name.split("/")
        folder_category_item = self._folder_cache[folder]
        last_name = ""
        parent_item: Optional[CategoryItem] = None
        for name in names:
            if name == names[-1]:
                item = folder_category_item
            else:
                fullname = f"{last_name}/{name}" if last_name else name
                item = self.__find_category_item_by_name(name, root_category_items)
                if item is None:
                    item = CategoryItem(fullname, 0)
                    self._folder_cache[fullname] = item
                item.count += folder_category_item.count
            if parent_item:
                if item not in parent_item.children:
                    parent_item.children.append(item)
                item.parent = parent_item
            parent_item = item
            last_name = name

        return self._folder_cache.get(names[0])

    def _get_summary_detail_items(self) -> List[FileDetailItem]:
        # Here not sort by all detail items but sort as:
        # - First sort by root folder order
        # - Then sort detail items in every root folder
        return list(chain.from_iterable([self.get_detail_items(self._folder_cache[f]) for f in self._root_folders]))

    def _on_folder_traverse_status(self, folder: AbstractBrowserFolder, status: TraverseStatus) -> None:
        self.__refresh_category_train(folder, status)
