# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["FolderBrowserModel"]

import asyncio
import json
import os
import tempfile
import time
import traceback
from itertools import chain
from typing import Callable, Dict, List, Optional, Set, Union

import carb
import carb.tokens
import omni.kit.app
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem

from .folder_browser_data import (
    AbstractBrowserFolder,
    BrowserFile,
    FileSystemFolder,
    TraverseResult,
    TraverseStatus,
    classify_result,
)
from .folder_browser_item import FileDetailItem, FolderCategoryItem, FolderCollectionItem
from .folder_identity import local_url_key, normalize_url, shutdown_link_checker
from .traverse_context import TraverseContext, TraverseState

REMOTE_FOLDER_PREFIX = "omniverse://"
PERSISTENT_SETTING_PREFIX = "/persistent"


class FolderBrowserModel(AbstractBrowserModel):
    """
    Represents the browser model for folders.

    Keyword Args:
        filter_file_suffixes (Optional[List[str]]): List of file suffixes. Files with suffix not in this list will be ignored. Default is None, means all file suffixes will appear.
        ignore_folder_names (Optional[List[str]]): List of folder names. Folder with name in this list will be ignored. Default is None, means all folders will appear.
        show_empty_folders (bool): If true, show empty folders (no files in the folder). Otherwise, hide empty folders. Default is False.
        show_summary_folder (bool): If true, show a summary folder (named "ALL") with all files in all folders. Otherwise, donot show such a folder. Default is True.
        setting_folders (Optional[str]): Setting path to save/load root folders
        create_file_object_fn (callable): Function called when creating a file object. Default is creating a BrowserFile. Function signature: Optional[BrowserFile] create_file_object_fn(url: str)
        timeout (Optional[float]): Number of seconds to wait for to list/reading from folder. If timeout is None, block until the future completes. Default is 5.
        category_tree_mode (bool): Show collections/categories in treeview mode
        local_cache_file(str):  Define the local cache file name for the model to be cached locally. If it is None, no local file cache will be stored.
        run_warmup (bool): If run in warmup. Default False.

    Overridden functions:
        bool filter_file(url: str): Determines a file will appear or not. Return true if appear, otherwise ingored. Default check file suffix with keyword args filter_file_suffixes.
            Args:
                url (str): Url of file.
        void execute(self, item: FileDetailItem): Execute a file.
            Args:
                item: File detail item to be executed.
        void sort_items(items: List[Union[FolderCollectionItem, FolderCollectionItem, DetailItem]]): Sort kinds of browser items. Default sort by name.
            Args:
                items (List[Union[FolderCollectionItem, FolderCollectionItem, DetailItem]]): List of browser items to be sorted.
        FolderCollectionItem create_collection_item(folder: AbstractBrowserFolder):  Create a collection item from a folder.
            Args:
                folder (AbstractBrowserFolder): Folder object to create collection item
        FolderCategoryItem create_category_item(folder: AbstractBrowserFolder): Create a category item from a folder.
            Args:
                folder (AbstractBrowserFolder): Folder object to create category item
        Union[FileDetailItem, List[FileDetailItem] create_detail_item(file: BrowserFile): Create detail item(s) from a file
            Args:
                file (BrowserFile): File object to create detail item
        AbstractBrowserFolder create_folder_object(*args, **kwargs): Create folder object when a root folder appended.
            Args and keyword args: please refer to FileSystemFolder

    """

    SUMMARY_FOLDER_NAME = "All"
    COUNT_LOADING = "..."
    COUNT_TIMEOUT = "Timeout"

    def __init__(
        self,
        filter_file_suffixes: Optional[List[str]] = None,
        ignore_folder_names: Optional[List[str]] = None,
        show_empty_folders: bool = False,
        show_summary_folder: bool = True,
        setting_folders: Optional[str] = None,
        create_file_object_fn: callable = None,
        hide_file_without_thumbnails: bool = False,
        show_category_subfolders: bool = False,
        timeout: Optional[float] = 5.0,
        category_tree_mode: bool = False,
        local_cache_file: str = None,
        run_warmup: bool = False,
        ignore_sub_folder_with_files: bool = False,
        custom_folders_setting: Optional[str] = None,
    ):
        super().__init__()

        # First, because destroy() may run against a model whose __init__ raised part way through.
        # It used to read this through its mangled name with a getattr default, which spelled the
        # class name in a string: renaming the class would have left that silently answering None,
        # and a heartbeat that is never found is never cancelled either.
        self.__heartbeat_task = None

        if category_tree_mode:  # pragma: no cover
            carb.log_warn("'category_tree_mode' deprecated in FolderBrowserModel. Use TreeFolderBrowserModel instead")
        self._root_collection_item: Optional[FolderCollectionItem] = None
        self._root_folders: List[AbstractBrowserFolder] = []
        self._filter_file_suffixes = filter_file_suffixes
        self._ignore_folder_names = ignore_folder_names
        self._show_empty_folders = show_empty_folders
        self._show_summary_folder = show_summary_folder
        self._create_file_object_fn = create_file_object_fn
        self._hide_file_without_thumbnails = hide_file_without_thumbnails
        self._show_category_subfolders = show_category_subfolders
        self._ignore_sub_folder_with_files = ignore_sub_folder_with_files
        self._timeout = timeout
        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()
        self._traverse_in_queue: List[str] = []

        # Folders that are queued or scanning, in queue order: the head is the one the worker is
        # processing. Order and membership only - every value the UI needs is read off the folder
        # item and its traverse_ctx. A folder leaves the moment its traverse ends.
        self.active_folders: List[AbstractBrowserFolder] = []
        self._active_folders_changed_fns: List[Callable[[], None]] = []
        self._traverse_progress_fns: List[Callable[[object], None]] = []
        self._custom_folder_path: Optional[str] = custom_folders_setting
        self._custom_folder_sub: Optional[int] = None
        self._custom_folders: Set[str] = set()

        # Read alias from omniverse config to replace folder url if defined
        try:
            import toml

            global_config_path = carb.tokens.get_tokens_interface().resolve("${omni_global_config}")
            omniverse_config_path = os.path.join(global_config_path, "omniverse.toml").replace("\\", "/")
            omni_config = toml.load(omniverse_config_path)
            self.__alias_configs = omni_config.get("aliases", {})
        except:  # pragma: no cover
            self.__alias_configs = {}

        # If folder loading not completed, show category count with COUNT_LOADING instead of number
        self._loading_completed = True

        self._json_file = None
        if local_cache_file and local_cache_file.endswith(".json"):
            self._json_file = carb.tokens.get_tokens_interface().resolve(local_cache_file)

        # Cache of browser items
        self._folder_cache: Dict[
            Union[AbstractBrowserFolder, BrowserFile, str],
            Union[FolderCollectionItem, FolderCategoryItem, CategoryItem, FileDetailItem],
        ] = {}

        self._settings = carb.settings.get_settings()

        # Load root folders from settings
        if setting_folders is not None:
            if setting_folders.startswith(PERSISTENT_SETTING_PREFIX):
                self._setting_folders = setting_folders  # pragma: no cover
            else:
                self._setting_folders = PERSISTENT_SETTING_PREFIX + setting_folders

            # load root folders from setting
            root_folders = self._settings.get(self._setting_folders)
            if not root_folders:
                if self._setting_folders != setting_folders:
                    root_folders = self._settings.get(setting_folders)
            if root_folders:
                for root_folder in root_folders:
                    if root_folder:
                        self.process_root_folder(root_folder, sync=False)
        else:
            self._setting_folders = None

        # load root folders from additional folder settings. Add watcher on property to refresh on change
        if self._custom_folder_path:
            additional_root_folders = list(self._settings.get(self._custom_folder_path))
            for root_folder in additional_root_folders:
                self.process_root_folder(root_folder, sync=False)
                self._custom_folders.add(root_folder)
            self._custom_folder_sub = omni.kit.app.SettingChangeSubscription(
                self._custom_folder_path, self._on_custom_folders_changed
            )

        self.__traverse_future = asyncio.ensure_future(self._run())
        # Backstop: a BaseException escaping the coroutine would otherwise be swallowed by asyncio
        # and only surface as a browser that quietly never scans again.
        self.__traverse_future.add_done_callback(self.__on_worker_done)

        self.on_refresh_categories: Callable[[None], None] = None

        if run_warmup:
            self.__warmup()

    def process_root_folder(self, root_folder: str, sync: bool = True) -> Optional[FileSystemFolder]:
        """
        Process a root folder name and url and add it to the list of root folders.

        Args:
            root_folder: Name of root folder with optional prepended collection name.
        """
        fields = root_folder.split("::")
        if len(fields) == 1:
            return self.append_root_folder(root_folder, save=False, sync=sync)
        elif len(fields) == 2:
            return self.append_root_folder(fields[1], name=fields[0], save=False, sync=sync)
        else:
            carb.log_error(f"Unknown folder format: {root_folder}")
            return None

    def destroy(self):
        self._stop_event.set()
        if self.__heartbeat_task is not None:
            self.__heartbeat_task.cancel()
            self.__heartbeat_task = None
        self._work_queue.put_nowait(None)
        self.__traverse_future.cancel()
        self.on_refresh_categories = None

        for root_folder in self._root_folders:
            for sub_folder in root_folder.sub_folders:
                sub_folder.destroy()
            root_folder.destroy()

        self._custom_folder_sub = None
        # The link checker's thread is shared and lazily rebuilt, so dropping it here costs a
        # thread creation if another model is still working, and leaves none behind if not.
        shutdown_link_checker()

    def register_folder(self, url: str, name: Optional[str] = None) -> None:  # pragma: no cover - never called
        """
        Register a folder path with the model.
        Args:
            url (str): Url of folder
            name (Optional[str]): Name of folder. Default is None.
        """
        if name:
            url = f"{name}::{url}"
        carb.log_info(f"Registering root folder: {url}")
        self.process_root_folder(url)

    def unregister_folder(self, url: str) -> None:  # pragma: no cover - never called
        """
        Unregister a folder path with the model when finished with it.
        Args:
            url (str): Url of folder
        """
        self.remove_root_folder(url)

    def append_root_folder(
        self, url: str, name: Optional[str] = None, save: bool = True, sync: bool = True
    ) -> Optional[FileSystemFolder]:
        """
        Append a root folder.
        Return FileSystemFolder object is appended, otherwise None means url already exists.
        Args:
            url (str): Url of folder
            name (Optional[str]): Name of folder. Default is None, means use last directory name as collection name.
            save (bool): True to save current root folder to settings if setting path defined. False means nothing saved.
        """
        url = carb.tokens.get_tokens_interface().resolve(url)
        url = normalize_url(url.replace("\\", "/"))
        if url.endswith("/"):
            url = url[:-1]

        if self.get_root_folder(url):
            return None  # pragma: no cover

        if name is None:
            name = url.split("/")[-1]
            # Root folders persist as "{name}::{url}", so a drive root would be saved as "C:::C:"
            # and read back as name "C" with url ":C:" - a collection that can never be found or
            # removed again. A trailing colon is illegal in a name anyway: "C:" -> "C".
            name = name.rstrip(":")

        def __is_name_valid(name) -> bool:
            if self._root_folders:
                for root_folder in self._root_folders:
                    if root_folder.name == name:
                        return False
            return True

        def __get_next_valid_name(name) -> str:
            if __is_name_valid(name):
                return name

            for index in range(1, 100):
                next = f"{name}_{index}"
                if __is_name_valid(next):
                    return next
            else:
                return name

        name = __get_next_valid_name(name)
        folder = self._create_folder_object_by_url(
            name,
            url,
            on_traversed_fn=self._on_folder_traversed,
            root=True,
            on_traverse_status_fn=self._on_folder_traverse_status,
        )
        self._root_folders.append(folder)

        if save:
            self._save_root_folders()

        if sync:
            self.folder_changed(folder)
        return folder

    def remove_root_folder(self, url: str) -> bool:
        """
        Remove a root folder
        Return True if succeeded, otherwise False.
        Args:
            url (str): Url of root folder to be removed.
        """
        url = carb.tokens.get_tokens_interface().resolve(url)
        url = url.replace("\\", "/")
        root_folder = self.get_root_folder(url)
        if root_folder:
            # Terminalize BEFORE mutating _root_folders. This is public and synchronous, so it
            # cannot await the unwind - but cancelling first means every write path the dying
            # traverse could still reach short-circuits on the terminal state. Ordering is the
            # guarantee; waiting is not.
            ctx = root_folder.traverse_ctx
            if ctx is not None and not ctx.is_terminal:
                self._finish_traverse(root_folder, ctx, None, cancelled=True, reason="collection removed")
            if root_folder in self._folder_cache:
                # Some root_folders can be lower in the hierarchy
                item = self._folder_cache[root_folder]
                if hasattr(item, "parent"):
                    if item.parent:
                        item.parent.children.remove(item)
                        parent = item.parent
                        # Decrement item counts for ancestors of the removed folder
                        while parent is not None:
                            parent.count -= item.count
                            self._item_changed(parent)
                            parent = parent.parent
                self._folder_cache.pop(root_folder)
            self._root_folders.remove(root_folder)
            if root_folder.url in self._traverse_in_queue:
                self._traverse_in_queue.remove(root_folder.url)

            # Usually already gone - the cancellation above unregisters it - but a collection
            # removed while idle was never registered in the first place, and this is harmless
            # either way.
            self._unregister_active_folder(root_folder)

            self._save_root_folders()
            self.folder_changed(root_folder)
            return True
        else:  # pragma: no cover
            carb.log_error(f"Folder {url} does not exist!")
            return False

    def get_root_folder(self, url: str) -> Optional[AbstractBrowserFolder]:
        """
        Find a root folder
        Return folder object if succeeded, otherwise False.
        Args:
            url (str): Url of root folder to find.
        """
        url = normalize_url(url.replace("\\", "/"))
        if url.endswith("/"):
            url = url[:-1]
        # Matched on identity rather than spelling: a collection added as C:/Users/me has to be
        # found by c:/users/me, or it is added a second time and cannot be removed by the url the
        # caller has.
        key = local_url_key(url)
        for root_folder in self._root_folders:
            if root_folder.url == url or local_url_key(root_folder.url) == key:
                return root_folder
        return None

    def folder_changed(self, item: Union[AbstractBrowserFolder, BrowserFile, None]) -> None:
        """
        Notify folder or file changed.
        Args:
            item (Union[AbstractBrowserFolder, BrowserFile]): Changed folder or file object.
        """
        if item is None:
            self._item_changed(None)
        else:
            # Remove cached browser item related to the item
            self.__clear_folder_cache(item)
            browser_item = self._folder_cache.get(item, None)
            if browser_item:
                self._item_changed(browser_item)
            else:
                # New folder
                self._item_changed(None)

    def _on_custom_folders_changed(self, item, event):
        """
        Remove and Add folders that change between updates
        """
        if event == carb.settings.ChangeEventType.CHANGED:
            custom_folder_raw = self._settings.get(self._custom_folder_path) or []  # In the case the property is None
            new_folders, old_folders = set(custom_folder_raw), set(self._custom_folders)
            added, deleted = new_folders - old_folders, old_folders - new_folders

            for folder in deleted:
                self.remove_root_folder(folder)

            for folder in added:
                self.process_root_folder(folder, sync=True)

            self._custom_folders = new_folders

    def start_traverse(self, folder: FileSystemFolder, force: bool = False):
        if folder.url not in self._traverse_in_queue or force:
            carb.log_info(f"Add folder to queue: {folder.url}")
            self._traverse_in_queue.append(folder.url)
            self._register_active_folder(folder)
            self._work_queue.put_nowait(folder)

    def _cancel_traverse(self, url: str) -> bool:
        """
        Stop the scan of one collection, whether it is running or still queued.

        Delegates to the shared terminal path and does nothing else: setting the state or cancelling
        the task here would consume :meth:`_finish_traverse`'s first-wins test-and-set, leaving the
        collection registered with its loading flag still on.

        Synchronous and non-blocking - the traverse unwinds on its own, and every write path it
        could still reach short-circuits on the terminal state. A queued collection needs no special
        case, since the worker skips a terminal folder when it reaches it.

        Args:
            url (str): Url of the root collection to cancel.
        Return True if this call is the one that stopped it; False if it was already over.
        """
        url = carb.tokens.get_tokens_interface().resolve(url)
        url = url.replace("\\", "/")
        folder = self.get_root_folder(url)
        if folder is None:
            return False
        ctx = folder.traverse_ctx
        if ctx is None or ctx.is_terminal:
            return False
        won = self._finish_traverse(folder, ctx, None, cancelled=True, reason="user cancelled", mark_prepared=True)
        if won:
            # Publish here. _finish_traverse clears the loading flag but leaves the notification to
            # its caller, and a button has none of its own. Without this the row keeps its spinner:
            # the delegate builds it in build_widget and stops it only when the row is rebuilt.
            category_item = self._folder_cache.get(folder, None)
            if category_item is not None:
                self._item_changed(category_item)
        return won

    # ---------------------------------------------------------------- progress registry ------

    def _add_active_folders_changed_fn(self, fn: Callable[[], None]) -> None:
        """Subscribe to folders being added to or removed from :attr:`active_folders`."""
        self._active_folders_changed_fns.append(fn)

    def _remove_active_folders_changed_fn(self, fn: Callable[[], None]) -> None:
        if fn in self._active_folders_changed_fns:
            self._active_folders_changed_fns.remove(fn)

    def _add_traverse_progress_fn(self, fn: Callable[[object], None]) -> None:
        """Subscribe to counter/state changes on any active traverse."""
        self._traverse_progress_fns.append(fn)

    def _remove_traverse_progress_fn(self, fn: Callable[[object], None]) -> None:
        if fn in self._traverse_progress_fns:
            self._traverse_progress_fns.remove(fn)

    _HEARTBEAT_SECONDS = 0.05

    async def __heartbeat(self) -> None:
        """
        Keep a timer pending for as long as anything is scanning.

        Folders wait on the app's next frame, which is the only wait that lets the app run - but if
        every one of them is waiting and nothing else is ready, asyncio has no timer to compute a
        timeout from and blocks in select, so the frame they are waiting for cannot happen. A
        sleeping task is enough to prevent it: the loop always has something to wake for.
        """
        try:
            while self.active_folders:
                await asyncio.sleep(self._HEARTBEAT_SECONDS)
        finally:
            # Only if this is still the current one, as ThumbnailView.__build_pending_async does:
            # a cancelled heartbeat runs its finally when it is next scheduled, which can be after
            # a replacement has started, and clearing the handle then loses the live task.
            if self.__heartbeat_task is asyncio.current_task():
                self.__heartbeat_task = None

    def __ensure_heartbeat(self) -> None:
        if self.__heartbeat_task is None and self.active_folders:
            self.__heartbeat_task = asyncio.ensure_future(self.__heartbeat())

    def _register_active_folder(self, folder: AbstractBrowserFolder) -> None:
        """Give the folder a fresh context and append it to the ordered active list."""
        # The reconnect path re-queues a folder that is already listed. Move it to the back rather
        # than listing it twice: it genuinely is queued again.
        if folder in self.active_folders:
            self.active_folders.remove(folder)
        folder.traverse_ctx = TraverseContext(folder, on_progress_fn=self._on_traverse_progress)
        # Queuing it supersedes the last interruption. Cleared here rather than when the traverse
        # actually begins, so a Refresh drops the Cancelled label straight away instead of leaving
        # it up until the worker gets round to the collection.
        folder.traverse_cancelled = False
        self.active_folders.append(folder)
        carb.log_info(f"collection queued: {folder.url}")
        self.__ensure_heartbeat()
        self._notify_active_folders_changed()

    def _unregister_active_folder(self, folder: AbstractBrowserFolder) -> None:
        if folder in self.active_folders:
            self.active_folders.remove(folder)
            self._notify_active_folders_changed()

    def _notify_active_folders_changed(self) -> None:
        for fn in list(self._active_folders_changed_fns):
            fn()

    def _on_traverse_progress(self, ctx) -> None:
        for fn in list(self._traverse_progress_fns):
            fn(ctx)

    def _finish_traverse(
        self,
        folder: AbstractBrowserFolder,
        ctx,
        result: TraverseResult,
        cancelled: bool = False,
        reason: str = None,
        mark_prepared: bool = False,
    ) -> bool:
        """
        End one root traverse. The single place a traverse is declared over.

        Runs in order and without yielding, so the row and spinner update in the same tick:

        1. identity check - a superseded context touches nothing;
        2. atomic test-and-set - first outcome wins, later ones no-op;
        3. outcome branch - the only outcome-dependent step;
        4. common cleanup - unconditional.

        Return True if this call was the one that ended the traverse.
        """
        # 1. Identity: a newer traverse may already own this folder.
        if folder.traverse_ctx is not ctx:
            return False

        # 2. First-wins. A timeout racing a completion must not clean up twice.
        if ctx.is_terminal:
            return False

        if cancelled:
            # No result: the traverse did not reach one. Recording OK or a failure here would be a
            # claim about the tree that nothing measured.
            done = False
            ctx.result = None
            ctx.reason = reason or "cancelled"
            ctx.set_state(TraverseState.CANCELLED)
            folder.traverse_cancelled = True
            if mark_prepared:
                # Dealt with, though not finished. `prepared` is what the browser reads to decide
                # whether a collection still needs scanning, and a cancelled traverse never reaches
                # _on_traverse_async_done - so without this the next category rebuild re-queues it
                # and the cancel becomes a fresh scan. Refresh Current Collection is the retry.
                #
                # Not set while the collection is being removed: folder_changed reads the same flag,
                # and a removed root that looks scanned leaves its row on screen.
                folder.prepared = True
        else:
            done = result is TraverseResult.OK
            ctx.result = result
            ctx.set_state(TraverseState.DONE if done else TraverseState.FAILED)

        # 3. Outcome branch. The cache is written synchronously here, which is the one step
        # that can raise: guard it so a failed write cannot strand a context that is already
        # terminal, then fall through to cleanup either way.
        if cancelled:
            # Neither branch applies. Caching a cancelled scan would persist a half-walked tree as
            # if it were the whole collection, and the next session would trust it; and a failure
            # notification would report a problem the user caused deliberately.
            carb.log_info(f"Traverse cancelled: {folder.url} ({ctx.reason})")
        elif done:
            try:
                self._save_data_to_json(folder)
            except Exception as exc:  # noqa: BLE001 - the scan succeeded; only persistence failed
                carb.log_error(f"Failed to save cache for {folder.url}: {exc}")
                self._notify_scan_failure(folder, retryable=False, cache_only=True)
        else:
            self._classify_failure(folder, result)

        # 4. Common cleanup, unconditional.
        self._unregister_active_folder(folder)
        # The context deliberately outlives the list entry: it carries the final counts and the
        # outcome, which the progress window still shows after a collection finishes. "Is this
        # folder working?" is answered by membership in active_folders, never by traverse_ctx.

        # Clear the loading flag but do not notify here: the caller publishes the folder straight
        # afterwards, and that notification covers the category item. Firing our own would double
        # the item-changed events every observer sees.
        category_item = self._folder_cache.get(folder, None)
        if category_item:
            category_item.loading = False

        if cancelled:
            # Children part way through never get their COMPLETED, so their rows keep spinning
            # after the collection has stopped. The whole sub tree shares the root's context, which
            # is the test for "was this row part of the cancelled scan" - no tree walk, and no
            # chance of clearing a row belonging to another collection.
            for other, other_item in self._folder_cache.items():
                if other is folder or not getattr(other_item, "loading", False):
                    continue
                if getattr(other, "traverse_ctx", None) is ctx:
                    # It was still spinning, so it had started and had not finished: this one was
                    # interrupted. Children that already finished keep their count, and children the
                    # traverse never reached stay as they were.
                    other.traverse_cancelled = True
                    other_item.loading = False
                    self._item_changed(other_item)

        # Release the url only if no live folder still claims it. Checking the list rather than
        # the url guards the remove-then-re-add flow: an old folder unwinding must not delete the
        # dedupe guard belonging to its replacement.
        if not any(other.url == folder.url for other in self.active_folders):
            if folder.url in self._traverse_in_queue:
                self._traverse_in_queue.remove(folder.url)

        # Cancel the task last: everything above is synchronous, so by the time the traverse is
        # interrupted the model already looks finished to anything the unwinding coroutine might
        # still touch. Nothing awaits the unwind - see _cancel_traverse.
        if cancelled and ctx.task is not None and not ctx.task.done():
            ctx.task.cancel()

        outcome = ctx.state.value if cancelled else result.value
        carb.log_info(f"collection ended: {folder.url} -> {outcome} (found {ctx.files_found:,})")
        return True

    def _classify_failure(self, folder: AbstractBrowserFolder, result: TraverseResult) -> None:
        """Route a failed traverse to the surface that matches whether retrying could help."""
        retryable = result is TraverseResult.RETRYABLE_FAILURE
        if retryable:
            # The tree already shows TIMEOUT plus "Refresh Current Collection" off this flag. No
            # notification here either - the caller's folder_changed covers it.
            folder.has_timeout = True
        self._notify_scan_failure(folder, retryable=retryable)

    def _notify_scan_failure(self, folder, retryable: bool, cache_only: bool = False) -> None:
        """
        Surface a failure the user would otherwise never see.

        Retryable failures stay silent here: they already have the TIMEOUT count and a Refresh
        affordance, and a toast on every network blip would be noise.
        """
        if retryable:
            return
        if cache_only:
            message = f'Loaded "{folder.name}" but could not save its cache'
        else:
            message = f'Could not load "{folder.name}"'
        carb.log_error(message)
        try:
            import omni.kit.notification_manager as nm

            nm.post_notification(message, status=nm.NotificationStatus.WARNING)
        except Exception:  # noqa: BLE001 - notifications are a surface, never a dependency of the scan
            pass

    def get_collection_items(self) -> List[FolderCollectionItem]:
        """Override to get list of collection items"""
        collection_items = []

        for root_folder in self._root_folders:
            if root_folder not in self._folder_cache:
                self._folder_cache[root_folder] = self.create_collection_item(root_folder)
            collection_items.append(self._folder_cache[root_folder])

        # fill self._root_folders with local cache
        self._load_data_from_json()

        # For collections, keep the order of settings
        # self.sort_items(collection_items)

        return collection_items

    def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]:
        """Override to get list of category items"""

        root_folder = item.folder
        if root_folder is None:
            return []

        if not root_folder.prepared:
            # Traverse folder to update all sub folders and files now
            self.start_traverse(root_folder)

        category_items = []
        summary_count = 0
        has_timeout = root_folder.has_timeout
        for sub_folder in root_folder.sub_folders:
            if sub_folder not in self._folder_cache:
                self._folder_cache[sub_folder] = self.create_category_item(sub_folder)
            category_item = self._folder_cache[sub_folder]
            if sub_folder.has_timeout:
                category_items.append(category_item)
            elif category_item.count > 0:
                category_items.append(category_item)
                summary_count += category_item.count
            elif self._show_empty_folders:  # pragma: no cover
                category_items.append(category_item)

            # If loading not completed, do not show category number
            if not self._loading_completed:
                category_item.count = self.COUNT_LOADING

        self.sort_items(category_items)
        if self._show_summary_folder:
            if has_timeout:
                summary_count = self.COUNT_TIMEOUT
            elif not self._loading_completed:
                summary_count = self.COUNT_LOADING
            category_items.insert(0, FolderCategoryItem(self.SUMMARY_FOLDER_NAME, summary_count, item.folder))

        return category_items

    def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]:
        """Override to get list of detail items"""
        detail_items = []

        if item.name == self.SUMMARY_FOLDER_NAME:
            # List all files in sub folders
            for sub_folder in item.folder.sub_folders:
                detail_items += self._get_folder_detail_items(sub_folder)
        elif isinstance(item, FolderCategoryItem):
            # List files in item folder
            detail_items = self._get_folder_detail_items(item.folder)
        else:  # CategoryItem
            return list(chain.from_iterable([self.get_detail_items(c) for c in item.children]))

        self.sort_items(detail_items)
        return detail_items

    def remove_collection(self, item: FolderCollectionItem) -> bool:
        url = item.folder.url
        return self.remove_root_folder(url)

    def get_folder_item(self, folder: FileSystemFolder) -> FolderCategoryItem:
        return self._folder_cache.get(folder, None)

    def _get_folder_detail_items(self, folder: AbstractBrowserFolder) -> List[FileDetailItem]:
        """Get list of detail items from a folder"""
        detail_items = []
        for file in folder.files:
            # with that option files that don't have thumbnails are hidden
            if self._hide_file_without_thumbnails and not file.thumbnail:
                continue

            if file not in self._folder_cache:
                self._folder_cache[file] = self.create_detail_item(file)

            if isinstance(self._folder_cache[file], list):
                detail_items.extend(self._folder_cache[file])
            else:
                detail_items.append(self._folder_cache[file])

        # we will have some means to make it configured by the user right now it is fixed at the
        # browser level
        if self._show_category_subfolders:
            for sub_folder in folder.sub_folders:
                # extend, not detail_items + ...: the latter builds a new list per sub folder, so
                # assembling k sub folders holding n items between them copied O(n * k) entries.
                detail_items.extend(self._get_folder_detail_items(sub_folder))

        return detail_items

    def _on_folder_traversed(self, folder: AbstractBrowserFolder, loading_completed=True, updated: bool = True) -> None:
        """Callback when folder traverse done"""
        carb.log_info(f"Traverse completed: {folder.url}, {loading_completed}")
        self._loading_completed = loading_completed

        if folder in self._root_folders:
            # Publishing the contents to the UI stays here; persisting them moved to the terminal
            # path, which is the only place that knows the whole sub tree succeeded. Saving here
            # too would write the cache twice, and would write it for a failed traverse.
            self.folder_changed(folder)

    def filter_file(self, url: str) -> bool:
        """
        Check a file if valid or not.
        Return true if valid, otherwise false.
        If filter_file_suffixes not defined, always valid. Otherwise only valid if in valid_file_suffixed.
        Args:
            url (str): Url of file.
        """
        if self._filter_file_suffixes is not None:
            for ext in self._filter_file_suffixes:
                if url.lower().endswith(ext.lower()):
                    return True
            else:
                return False
        else:
            return True

    def sort_items(self, items: List[Union[FolderCollectionItem, FolderCollectionItem, FileDetailItem]]) -> None:
        """
        Sort kinds of browser items by name.
        Args:
            items (List[Union[FolderCollectionItem, FolderCollectionItem, FileDetailItem]]): List of browser items to be sorted.
        """
        items.sort(key=lambda item: item.name)

    def create_collection_item(self, folder: AbstractBrowserFolder) -> FolderCollectionItem:
        """
        Create a collection item from a folder.
        Args:
            folder (AbstractBrowserFolder): Folder object to create collection item
        """
        return FolderCollectionItem(folder.name, folder.url, folder)

    def create_category_item(
        self, folder: AbstractBrowserFolder, parent: Optional[CategoryItem] = None
    ) -> FolderCategoryItem:
        """
        Create a category item from a folder.
        Args:
            folder (AbstractBrowserFolder): Folder object to create category item
        """
        if folder.has_timeout:
            count = self.COUNT_TIMEOUT
        else:
            count = self.__get_folder_count(folder)

            if self._show_category_subfolders:

                def recursive_count(current_count, folder: AbstractBrowserFolder) -> int:
                    for sub_folder in folder.sub_folders:
                        if self._hide_file_without_thumbnails:
                            for file in sub_folder.files:
                                if file.thumbnail:
                                    current_count += 1
                        else:
                            current_count += len(sub_folder.files)
                        current_count = recursive_count(current_count, sub_folder)

                    return current_count

                count = recursive_count(count, folder)

        return FolderCategoryItem(folder.name, count, folder, parent)

    def create_detail_item(self, file: BrowserFile) -> Union[FileDetailItem, List[FileDetailItem]]:
        """
        Create detail item(s) from a file.
        A file may includs multi detail items.
        Args:
            file (BrowserFile): File object to create detail item(s)
        """
        dirs = file.url.split("/")
        name = dirs[-1]

        return FileDetailItem(name, file.url, file, file.thumbnail)

    def create_folder_object(self, *args, **kwargs) -> AbstractBrowserFolder:
        """
        Create a folder object when a root folder appended. Default using FileSystemFolder.
        User could overridden to create own folder object for special usage.
        Args and keyword args please reference to FileSystemFolder.
        """
        return FileSystemFolder(*args, **kwargs)

    def _save_root_folders(self):
        # save to settings
        if not self._setting_folders:
            return
        folder_settings = []
        for root_folder in self._root_folders:
            folder_settings.append(f"{root_folder.name}::{root_folder.url}")
        self._settings.set(self._setting_folders, folder_settings)

    def _save_folder_to_json(
        self, folder: AbstractBrowserFolder, parent: Optional[AbstractBrowserFolder] = None
    ) -> Dict:
        # collection
        folder_url = folder.url
        output = {"url": folder_url, "sub_folders": {}}
        # category
        for sub_folder in folder.sub_folders:
            sub_folder_url = sub_folder.url
            category_item = {"url": os.path.relpath(sub_folder_url, folder_url), "files": {}}
            output["sub_folders"][sub_folder.name] = category_item
            # detail
            for file in sub_folder.files:
                thumbnail = file.thumbnail
                if thumbnail:
                    thumbnail = os.path.relpath(thumbnail, sub_folder_url)
                detail_item = {"url": os.path.relpath(file.url, sub_folder_url), "thumbnail": thumbnail}

                name = file.url.split("/")[-1]
                output["sub_folders"][sub_folder.name]["files"][name] = detail_item
        return output

    def _load_folder_from_json(self, data: Dict, folder: AbstractBrowserFolder):
        # category
        sub_folders = data["sub_folders"]
        for category_item in sub_folders:
            category_data = sub_folders[category_item]
            folder_url = folder.url + "/" + category_data["url"]
            category_folder = self._create_folder_object_by_url(category_item, folder_url)
            # files
            files = category_data["files"]
            for file_item in files:
                file_data = files[file_item]
                thumbnail = file_data["thumbnail"]
                if thumbnail:
                    thumbnail = folder_url + "/" + thumbnail
                file = BrowserFile(folder_url + "/" + file_data["url"], thumbnail)
                category_folder.files.append(file)
            folder.sub_folders.append(category_folder)

    def _save_data_to_json(self, folder: AbstractBrowserFolder):
        if not self._json_file:
            return

        start = time.time()
        try:
            with open(self._json_file) as json_file:
                json_decoded = json.load(json_file)
        except FileNotFoundError:
            json_decoded = {}
        except PermissionError:
            carb.log_error(f"Cannot write to {self._json_file}: permission denied!")
            return
        except Exception as exc:  # noqa: BLE001 - an unreadable cache is replaced, not fatal
            # Start again rather than refuse. This used to return, so one unparsable file - a write
            # interrupted by a crash or a full disk before the atomic replace landed - meant nothing
            # could ever be cached again, for any collection, until someone deleted it by hand.
            carb.log_warn(f"Replacing unreadable cache {self._json_file}: {exc}")
            json_decoded = {}

        json_decoded[folder.name] = self._save_folder_to_json(folder, None)

        # Write beside the target and rename into place. This file holds every collection's cache,
        # so truncating it with open(..., "w") leaves a half-written file that takes all of them
        # with it if anything interrupts. os.replace is atomic on one volume, which is why the temp
        # file has to sit in the same directory.
        directory = os.path.dirname(self._json_file) or "."
        handle, temp_path = tempfile.mkstemp(dir=directory, prefix=".cache-", suffix=".tmp")
        try:
            with os.fdopen(handle, "w") as json_file:
                # Compact: nothing reads this by eye, and indenting it costs more than the walk
                # that produced it - 4.9 ms against 0.2 ms over 10,000 files - for twice the bytes.
                json.dump(json_decoded, json_file, separators=(",", ":"))
            os.replace(temp_path, self._json_file)
        except Exception as exc:  # noqa: BLE001 - the scan succeeded; only persistence failed
            carb.log_error(f"Failed to write {self._json_file}: {exc}")
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return

        carb.log_info(f"Save folder {folder.url} to cache: {time.time() - start:.2f} seconds")

    def _load_data_from_json(self, check_only: bool = False):
        if not self._json_file:
            return

        start = time.time()
        asset_json = None
        try:
            with open(self._json_file, "r") as json_file:
                asset_json = json.load(json_file)
        except FileNotFoundError:
            carb.log_info(f"Failed to open {self._json_file}!")
            return
        except PermissionError:
            carb.log_error(f"Cannot read {self._json_file}: permission denied!")
            return
        except Exception as exc:  # noqa: BLE001 - a cache that cannot be read is one to rebuild
            # Not an error: the collections are scanned instead, and the next save replaces it.
            carb.log_warn(f"Ignoring unreadable cache {self._json_file}: {exc}")
            return

        if asset_json is None:
            return
        # collection
        for root_folder in self._root_folders:
            if not root_folder.prepared and root_folder.name in asset_json:
                saved_url = asset_json[root_folder.name]["url"]
                # OM-75630: If folder url redirected, do not load from cache
                saved_url = saved_url.replace("\\", "/")
                if saved_url == root_folder.url:
                    if not check_only:
                        self._load_folder_from_json(asset_json[root_folder.name], root_folder)
                    root_folder.has_cache = True
                else:
                    carb.log_warn(f"Do not load cache for {root_folder.name} because url changed:")
                    carb.log_warn(f" - from {saved_url}")
                    carb.log_warn(f" -   to {root_folder.url}")
                    root_folder.has_cache = False

        carb.log_info(f"Load folders from cache: {time.time() - start:.5f} seconds")

    def __get_folder_count(self, folder: AbstractBrowserFolder) -> int:
        if self._hide_file_without_thumbnails:
            return len([file for file in folder.files if file.thumbnail])
        else:
            return len(folder.files)

    def _shutting_down(self) -> bool:
        """
        Is this cancellation just the app going away?

        destroy() sets the stop event, which is the answer whenever a browser owns its model and
        tears it down. Plenty of apps do not: they load this extension through something else, the
        loop cancels the worker on the way out, and the flag is never set. The app itself is the
        only witness left, so ask it.
        """
        if self._stop_event.is_set():
            return True
        try:
            return not omni.kit.app.get_app().is_running()
        except Exception:  # noqa: BLE001 - no app to ask, in a bare unit test
            return False

    def __on_worker_done(self, task) -> None:
        """
        The worker task ended.

        Only shutdown should get here quietly. This exists for the exceptions that never reach the
        loop's own handlers - a BaseException escaping the coroutine is otherwise swallowed by
        asyncio and surfaces only as a browser that silently stops scanning.
        """
        if task.cancelled():
            if not self._shutting_down():
                # Warned, not errored. A cancel is indistinguishable from a teardown this model was
                # not told about, and Kit's test harness fails a job on any [Error] in stdout - so
                # an error here failed other extensions' ETM runs at shutdown, for nothing.
                carb.log_warn("Traverse worker was cancelled without a shutdown; nothing will scan.")
            return
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            carb.log_error(f"Traverse worker ended on {type(exc).__name__}: {exc}")

    async def _run(self):
        """
        The serial worker: one collection at a time, for the life of the model.

        Every exit from this loop is announced. If it ends for any reason other than shutdown,
        nothing will ever scan again - queued collections sit in the queue, and whatever was in
        flight keeps its spinner because no terminal transition runs for it. That failure is silent
        by nature, so it is worth a log line at the point it happens rather than a forensic
        exercise afterwards.
        """
        stopped_for = "shutdown"
        try:
            await self.__run_queue()
        except asyncio.CancelledError:
            # destroy() sets the stop event before it cancels, so a cancel with the flag set is the
            # ordinary way this ends. Without the flag, something cancelled the worker from outside
            # and the browser is now inert.
            stopped_for = "shutdown" if self._shutting_down() else "cancelled from outside"
            raise
        except BaseException as exc:  # noqa: BLE001 - re-raised; this only adds the log line
            stopped_for = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            if stopped_for == "shutdown":
                carb.log_info("Traverse worker stopped.")
            else:
                # An exception is this model's fault and stays an error. A cancel is not: see
                # _shutting_down, and the harness rule described in __on_worker_done.
                log = carb.log_warn if stopped_for == "cancelled from outside" else carb.log_error
                log(
                    f"Traverse worker stopped unexpectedly ({stopped_for}). No collection will be "
                    "scanned until this browser is reloaded."
                )

    async def __run_queue(self):
        while not self._stop_event.is_set():
            folder: AbstractBrowserFolder = await self._work_queue.get()
            if folder is None:
                break
            else:
                ctx = folder.traverse_ctx
                # A cancelled or removed collection leaves its entry in the queue - asyncio.Queue
                # cannot withdraw one - so the entry is a tombstone, collected here. Keyed on the
                # folder object, never the url: a url-keyed skip would let the ghost of a removed
                # collection swallow a legitimate re-add of the same path. The terminal context is
                # the whole test - sub folders are queued too, so anything narrower swallows them.
                if ctx is not None and ctx.is_terminal:
                    carb.log_info(f"Skipping {folder.url}: traverse already {ctx.state.value}")
                    self._unregister_active_folder(folder)
                    continue
                try:
                    start_time = time.time()
                    carb.log_info(f"Start traverse from queue: {folder.url}")
                    category_item = self._folder_cache.get(folder, None)
                    if category_item:
                        category_item.loading = True
                        # only need to update loading status
                        self._item_changed(category_item)
                    if ctx is not None:
                        ctx.set_state(TraverseState.REFRESHING if folder.prepared else TraverseState.SCANNING)
                    # Await a task rather than the coroutine, so _cancel_traverse has something to
                    # cancel. The context owns the handle; the children fan out beneath it and are
                    # cancelled with it by the gather they are awaited on.
                    task = asyncio.ensure_future(folder.start_traverse(on_connected_fn=self._on_server_connected))
                    if ctx is not None:
                        ctx.task = task
                    done = await task
                    if not done:
                        # A connector was launched. Nothing is decided yet: stay in the list,
                        # keep the url, keep the spinner, and wait for _on_server_connected.
                        if ctx is not None:
                            ctx.set_state(TraverseState.CONNECTING)
                        continue

                    carb.log_info(f"[{time.time() - start_time:.2f} s] End traverse {folder.url}")
                    result = folder.last_traverse_result
                    if result is None:
                        # Every path that returns True must publish an outcome. Treat a missing
                        # one as a bug rather than silently caching an unknown traversal.
                        carb.log_error(f"No traverse result published for {folder.url}")
                        result = TraverseResult.NON_RETRYABLE_FAILURE
                    # Terminalize first - it clears the loading flag - then publish, exactly as
                    # this loop did before: observers must see the final flag, not a stale one.
                    if ctx is not None:
                        self._finish_traverse(folder, ctx, result)
                    elif category_item:
                        category_item.loading = False
                    self.folder_changed(folder)

                except asyncio.CancelledError:
                    # The collection was cancelled, not the worker. CancelledError derives from
                    # BaseException, so it would sail past the handler below and kill this loop -
                    # one cancel and nothing would ever scan again. Re-raise only when the worker
                    # itself is going away, which is when the context is not the terminalized one.
                    if ctx is None or not ctx.is_terminal:
                        # Not our cancel. Expected during shutdown, when destroy() cancels the
                        # worker with whatever was in flight. Otherwise this names the collection
                        # left with its spinner turning, because nothing else will report it.
                        if self._shutting_down():
                            carb.log_info(f"Traverse worker stopped during {folder.url}")
                        else:
                            carb.log_warn(f"Traverse worker cancelled while scanning {folder.url}")
                        raise
                    carb.log_info(f"Traverse of {folder.url} unwound after cancel")
                    self.folder_changed(folder)

                except Exception as e:
                    carb.log_error(f"Exception when traverse: {folder.url}, {e}")
                    exc = traceback.format_exc()
                    carb.log_error(f"[omni.ui.tests.compare] Traceback:\n{exc}")
                    if ctx is not None:
                        self._finish_traverse(folder, ctx, TraverseResult.NON_RETRYABLE_FAILURE)
                    # Publish, as the paths above do. _finish_traverse clears the loading flag but
                    # notifies nothing, so without this the row keeps its spinner after a failure.
                    self.folder_changed(folder)

    def __warmup(self):

        async def __cache_all_folders_async():
            self._load_data_from_json(check_only=True)
            for folder in self._root_folders:
                try:
                    if hasattr(folder, "has_cache") and folder.has_cache:
                        carb.log_info(f"Already has cache for {folder.url}, ignore.")
                    else:
                        carb.log_info(f"Caching {folder.url}")
                        # Do not try connecting to nucleus server during warmup
                        await folder.start_traverse(try_connect_nucleus=False)
                        # Only cache a traversal that succeeded. Warmup has no TraverseContext - it
                        # drives its own event loop - so it reads the result off the folder. Saving
                        # unconditionally caches an empty tree whenever the url was unreachable.
                        if folder.last_traverse_result is TraverseResult.OK:
                            self._save_data_to_json(folder)
                            carb.log_info(f"Cached {folder.url}")
                        else:
                            carb.log_info(f"Not caching {folder.url}: {folder.last_traverse_result}")
                except Exception as e:
                    carb.log_info(f"Exception when caching: {folder.url}, {e}")

        loop = asyncio.events.new_event_loop()
        loop.run_until_complete(__cache_all_folders_async())
        loop.close()

    def _create_folder_object_by_url(self, name: str, url: str, **kwargs) -> FileSystemFolder:
        # OM-75623: Replace url if alias defined in omniverse.toml
        url = url.replace("\\", "/")
        for alias, value in self.__alias_configs.items():
            alias = alias.replace("\\", "/")
            value = value.replace("\\", "/")
            if alias.endswith("/"):
                alias = alias[:-1]
            if url.startswith(alias):
                carb.log_info(f"Replace url with alias:")
                carb.log_info(f"  from: {url}")
                url = url.replace(alias, value)
                carb.log_info(f"  to: {url}")
                break

        return self.create_folder_object(
            name,
            url,
            ignore_file_without_thumbnail=self._hide_file_without_thumbnails,
            ignore_empty_folder=not self._show_empty_folders,
            ignore_folder_names=self._ignore_folder_names,
            ignore_sub_folder_with_files=self._ignore_sub_folder_with_files,
            filter_file_fn=self.filter_file,
            timeout=self._timeout,
            **kwargs,
        )

    def __clear_folder_cache(self, folder: AbstractBrowserFolder) -> None:
        for sub_folder in folder.sub_folders:
            self._folder_cache.pop(sub_folder, None)
            for file in sub_folder.files:
                self._folder_cache.pop(file, None)
            self.__clear_folder_cache(sub_folder)

    def _on_server_connected(self, folder: AbstractBrowserFolder, result: bool) -> None:
        if result:
            # Server connected, traverse folder again
            carb.log_info(f"Connected to {folder.url}!")
            # Remove from traverse queue and add it back
            if folder.url in self._traverse_in_queue:
                self._traverse_in_queue.remove(folder.url)
            self.start_traverse(folder)
        else:
            # The connection failed, so nothing else will ever end this traverse. Terminalize here
            # or the collection keeps its spinner forever - the folder stays in active_folders,
            # its url is never released and the tree's loading flag is never cleared.
            carb.log_error(f"Invalid URL: {folder.url}!")
            ctx = folder.traverse_ctx
            if ctx is not None:
                result = folder.last_traverse_result
                if result is None or result is TraverseResult.OK:
                    stat_result = getattr(folder, "_last_stat_result", None)
                    result = (
                        classify_result(stat_result)
                        if stat_result is not None
                        else TraverseResult.NON_RETRYABLE_FAILURE
                    )
                # Publish, as the worker does after its own terminal transitions. _finish_traverse
                # clears the loading flag and notifies nothing, so without this the row is never
                # rebuilt: the spinner of a collection whose server never answered keeps turning,
                # and keeps waking the app, for the life of the session.
                if self._finish_traverse(folder, ctx, result):
                    self.folder_changed(folder)

    def _on_folder_traverse_status(self, folder: AbstractBrowserFolder, status: TraverseStatus) -> None:
        pass
