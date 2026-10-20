# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = [
    "BrowserFile",
    "AbstractBrowserFolder",
    "FileSystemFile",
    "FileSystemFolder",
    "TraverseStatus",
    "TraverseResult",
]

import abc
import asyncio
import enum
import os
import re
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

import carb
import omni.client
import omni.kit.app

from .folder_identity import derive_folder_key, find_links_async, local_url_key, resolve_folder_key

_legacy_nucleus_connector = False
try:
    from omni.kit.widget.nucleus_connector import connect
except ImportError:
    _legacy_nucleus_connector = True
    from omni.kit.widget.nucleus_connector import get_connector_instance

THUMBNAIL_PATH = ".thumbs"
THUMBNAIL_SIZE = 256
THUMBNAIL_FULL_PATH = f"/{THUMBNAIL_PATH}/{THUMBNAIL_SIZE}x{THUMBNAIL_SIZE}"
MAX_RETRY_COUNT = 3
# How many sub folders of one folder are traversed at once. Bounds in-flight work per level so a
# very deep or wide tree cannot starve the event loop.
MAX_CONCURRENT_SUB_FOLDERS = 8


class TraverseStatus:
    START = "start"
    SUB_FOLDERS_FOUND = "sub_folders_found"
    COMPLETED = "completed"


class TraverseResult(enum.Enum):
    """
    Outcome of traversing one folder and everything beneath it.

    ``URL_UNREACHABLE`` is special: it is returned only to the root wrapper
    (:meth:`FileSystemFolder.start_traverse`), which is the only caller with a connection
    decision to make. Recursive callers always receive a classified failure instead, so the
    sibling fold only ever orders the first three members.
    """

    OK = "ok"
    RETRYABLE_FAILURE = "retryable_failure"
    NON_RETRYABLE_FAILURE = "non_retryable_failure"
    URL_UNREACHABLE = "url_unreachable"


# Transient omni.client results: the url may work on a later attempt, so the collection keeps its
# "Refresh" affordance instead of a one-off error message. Looked up by name because the available
# members differ between omni.client versions.
_RETRYABLE_RESULT_NAMES = frozenset(
    ("ERROR_CONNECTION", "ERROR_CONNECTION_TIMEOUT", "ERROR_TIMEOUT", "ERROR_BUSY", "ERROR_UNAVAILABLE")
)


def classify_result(result) -> TraverseResult:
    """Map an ``omni.client.Result`` to a retryable/non-retryable traverse failure."""
    name = getattr(result, "name", str(result))
    if name in _RETRYABLE_RESULT_NAMES:
        return TraverseResult.RETRYABLE_FAILURE
    return TraverseResult.NON_RETRYABLE_FAILURE


# Worst-first. Folding a set of child outcomes takes the highest severity present, never the first
# one to arrive - completion order must not decide the result.
_RESULT_SEVERITY = {
    TraverseResult.OK: 0,
    TraverseResult.RETRYABLE_FAILURE: 1,
    TraverseResult.URL_UNREACHABLE: 2,
    TraverseResult.NON_RETRYABLE_FAILURE: 2,
}


def coerce_result(value) -> TraverseResult:
    """
    Accept a result from a possibly-overridden ``_traverse_folder_async``.

    That method is an extension point: ``omni.simready.explorer`` and
    ``omni.wrapp.package_explorer`` both override it and return ``None``, as every override did
    before traversal gained a return value. Such an override has no way to report failure, which is
    exactly how it behaved before - treat it as success rather than breaking it.
    """
    return value if isinstance(value, TraverseResult) else TraverseResult.OK


def fold_results(results) -> TraverseResult:
    """
    Fold gathered child outcomes into one result for the parent.

    Accepts anything ``asyncio.gather(..., return_exceptions=True)`` can produce: a
    :class:`TraverseResult`, or an exception instance from a child that raised.
    """
    worst = TraverseResult.OK
    for item in results:
        if isinstance(item, TraverseResult):
            candidate = item
        elif isinstance(item, asyncio.CancelledError):
            # Not a failure to fold. A cancelled child means the whole traverse is unwinding, and
            # folding it into NON_RETRYABLE_FAILURE would report the collection as broken and let
            # the parent carry on as if it had merely lost one sub tree.
            raise item
        elif isinstance(item, BaseException):
            carb.log_error(f"Exception while traversing sub folder: {item}")
            candidate = TraverseResult.NON_RETRYABLE_FAILURE
        else:
            continue
        if _RESULT_SEVERITY[candidate] > _RESULT_SEVERITY[worst]:
            worst = candidate
    return worst


class BrowserFile:
    """
    Represents a single file.
    Args:
        url (str): file url.
        thumbnail (Optional[str]): thumbnail url of file. Default is None.
    """

    def __init__(self, url: str, thumbnail: Optional[str] = None):
        self._url: str = url
        self._thumbnail: str = thumbnail
        # Identity, worked out once. It is asked for on both sides of every comparison and again
        # for the hash, and a scan compares every listed file against its cached copy.
        self._url_key: Optional[str] = None
        self._thumbnail_key: Optional[str] = None

        # Use prepared to check status of file in folder
        # False means this file in cache and not found in last traverse
        # True means this file was found in last traverse
        self.prepared = True

    @property
    def _item_count(self) -> int:
        """
        How many browsable items this file contributes.

        One by default - a file is an entry. Subclasses whose files can hold several entries
        override it; a material .usd, for instance, is worth one item per material prim inside.
        Progress reports this rather than the file count, because it is what the user is waiting
        to see appear in the browser.

        Protected: it exists for the traverse's accounting and for subclasses to answer, not for
        anyone holding a BrowserFile to ask.
        """
        return 1

    def __eq__(self, other: "BrowserFile") -> bool:
        return self.equals(other)

    def __hash__(self):
        # The same terms equals() uses. These objects are dictionary keys - the browser item cache
        # is keyed by them - so hashing the raw url while comparing the canonical one loses a file
        # that is looked up by another of its spellings.
        return hash((self._url_identity(), self._thumbnail_identity()))

    def _url_identity(self) -> str:
        """This file's identity: equal for two spellings of one local path. Computed once."""
        if self._url_key is None:
            self._url_key = local_url_key(self._url)
        return self._url_key

    def _thumbnail_identity(self) -> str:
        """The same for the thumbnail, which is a file url too."""
        if self._thumbnail_key is None:
            self._thumbnail_key = local_url_key(self._thumbnail or "")
        return self._thumbnail_key

    def _same_url(self, other: "BrowserFile") -> bool:
        """
        Do these two name one file?

        Protected rather than public: it is here for subclasses that override equals() and still
        have to decide identity the same way this class does - a listing and a cache that disagree
        show the same file twice. Nothing outside a BrowserFile needs to ask.
        """
        return self._url_identity() == other._url_identity()

    def equals(self, other: "BrowserFile") -> bool:
        """
        Check if two file objects are same.
        Returns True means same otherwise False.

        Urls are compared on identity rather than spelling: on Windows one file has many, and a
        cached copy spelled differently from the listing is still the same file.
        """
        return self._same_url(other) and self._thumbnail_identity() == other._thumbnail_identity()

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, value: str):
        self._url = value
        self._url_key = None

    @property
    def thumbnail(self) -> str:
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, value: str):
        self._thumbnail = value
        self._thumbnail_key = None

    def set_thumbnail(self, thumbnail_url: str) -> bool:
        """
        Check and set thumbnail.
        Args:
            thumbnail (str): Url of thumbnail.
        Return True if the thumbnail belongs to this file, otherwise False.
        """
        thumbnail_name = Path(thumbnail_url).stem
        file_name = self.url.split("/")[-1]

        if thumbnail_name == file_name or thumbnail_name == file_name + ".auto":
            # Through the setter, so the cached identity goes with it. Assigning the field directly
            # left thumbnail_key at the old value, and two files that had become equal would still
            # compare and hash as different.
            self.thumbnail = thumbnail_url
            return True
        else:
            return False

    def get_default_thumbnail_url(self) -> str:
        """
        Get default thumbnail url.
        """
        output_path = os.path.dirname(self.url) + THUMBNAIL_FULL_PATH
        output_file_name = self.url.split("/")[-1]
        return f"{output_path}/{output_file_name}.png"


class AbstractBrowserFolder:
    """
    Represents the abstract folder. Following functions need to be reimplemented:
        void start_traverse(): Start traverse folder to get sub folders and files

    Args:
        name (str): Folder name
        url (str): Folder url

    Keyword Args:
        ignore_folder_names (Optional[List[str]]): List of folder names. Sub folder with name in this list will be ignored.
            Default is None, means all folders will appear.
        filter_file_fn (callable): Determines a file will appear or not. Return true if appear, otherwise ingored. Default is None. Function signature:
            bool filter_file(url: str)
        on_traversed_fn (callable): Function to notify folder traverse done. Default is None. Function signature:
            void on_traversed_fn(folder: AbstractBrowserFolder)
        list_entry (Optional[omni.client.ListEntry]): folder list entry information. It is read while traversing, save for future usage. Default is None.
        timeout (Optional[float]): Number of seconds to wait for to list/reading from folder. If timeout is None, block until the future completes. Default is 5.
        on_traverse_status_fn (Callable[["AbstractBrowserFolder", TraverseStatus], None]): Function to notify traverse status. Default is None.
    Overridden functions:
        void start_traverse(): Start travserse to get all sub folders and filess in this folder.
            If traverse done, must set prepared = True and call on_traversed_fn to notify model.
    """

    def __init__(
        self,
        name: str,
        url: str,
        ignore_folder_names: Optional[List[str]] = None,
        filter_file_fn: callable = None,
        on_traversed_fn: callable = None,
        list_entry: Optional[omni.client.ListEntry] = None,
        timeout: Optional[float] = 5.0,
        on_traverse_status_fn: Callable[["AbstractBrowserFolder", TraverseStatus], None] = None,
    ):
        self.name = name
        self.url = url
        self.list_entry = list_entry
        self._timeout = timeout

        self._ignore_folder_names = ignore_folder_names
        self._filter_file_fn = filter_file_fn
        self._on_traverse_done_fn = on_traversed_fn
        self._on_traverse_status_fn = on_traverse_status_fn

        self.hide_root_in_category = False

        self._init_data()

    def destroy(self):
        pass

    @property
    def file_item_count(self) -> int:
        """Count of file items in this folder displayed in detail view"""
        return len(self.files)

    @abc.abstractmethod
    def start_traverse(self) -> None:
        """Start traverse folder to get sub folders and files"""
        self._init_data()

    def create_file_object(self, url: str) -> BrowserFile:
        """
        Create file object.
        Args:
            url: File Url.
        Return file object.
        """
        return BrowserFile(url)

    def _filter_folder(self, folder_name: str) -> bool:
        """
        Filter folder by name.
        Args:
            folder_name: Name of folder.
        Returns True if valid. Otherwise return False.
        """
        if self._ignore_folder_names is None:
            return True
        else:
            for ignore in self._ignore_folder_names:
                # Convert wild char "." and "*" to regex
                if "?" in ignore:
                    ignore = ignore.replace("?", ".")
                if "*" in ignore:
                    ignore = ignore.replace("*", ".+")
                if re.search(ignore, folder_name):
                    return False

            return True

    async def _on_file_found_async(self, url: str) -> Optional[BrowserFile]:
        """Function when a new file found during traversing."""
        if self._filter_file_fn and not self._filter_file_fn(url):
            return None

        return self.create_file_object(url)

    async def _on_sub_folder_found_async(self, url: str, entry) -> Optional["AbstractBrowserFolder"]:
        """Function when a new sub folder found during traversing."""
        sub_folder = self.create_folder_object(
            url.split("/")[-1],
            url,
            list_entry=entry,
            filter_file_fn=self._filter_file_fn,
            ignore_folder_names=self._ignore_folder_names,
            ignore_file_without_thumbnail=self._ignore_file_without_thumbnail,
            ignore_sub_folder_with_files=self._ignore_sub_folder_with_files,
            ignore_empty_folder=self._ignore_empty_folder,
            timeout=self._timeout,
            on_traverse_status_fn=self._on_traverse_status_fn,
        )
        self.sub_folders.append(sub_folder)
        return sub_folder

    def _init_data(self) -> None:
        self.prepared: bool = False
        self.has_timeout = False
        self.sub_folders: List[AbstractBrowserFolder] = []
        self.files: List[BrowserFile] = []

        # Outcome of the most recent traverse, published here rather than on a context object so
        # callers without one (__warmup builds none) can read it. Cleared when a traverse starts.
        self.last_traverse_result: Optional[TraverseResult] = None
        # Set by the model while this root, or an ancestor of it, is queued or scanning. The whole
        # sub tree shares the root's context so progress aggregates. None when idle.
        self.traverse_ctx = None
        # True when this folder's own traverse was stopped part way. Distinguishes a folder that was
        # interrupted from one that finished and one that was never reached - all three look alike
        # through `prepared`, which is False for the last two.
        self.traverse_cancelled = False
        # Directories already walked in the traverse this folder belongs to, shared by the whole
        # sub tree. Set by _traverse_async and kept afterwards, so a rescan starts from what
        # the last one saw.
        self._traverse_visited = None
        # This folder's identity for the traverse it is part of. Handed down from the parent, so
        # the whole sub tree is keyed without a filesystem call per directory.
        self._traverse_key = None
        self._last_stat_result = None
        self._last_list_result = None


class FileSystemFile(BrowserFile):
    """
    Represents a single file system file.
    Args:
        url (str): file url.
        list_entry (Optional[omni.client.ListEntry]): file list entry information. It is read while traversing, save for future usage. Default is None.
        thumbnail (Optional[str]): thumbnail url of file. Default is None.
        thumbnail_list_entry ((Optional[omni.client.ListEntry]): thumbnail list entry information. It is read while traversing, save for future usage. Default is None.
    """

    def __init__(
        self,
        url: str,
        list_entry: Optional[omni.client.ListEntry] = None,
        thumbnail: Optional[str] = None,
        thumbnail_list_entry: Optional[omni.client.ListEntry] = None,
    ):
        super().__init__(url, thumbnail)
        self.list_entry = list_entry
        self.thumbnail_list_entry = thumbnail_list_entry


class FileSystemFolder(AbstractBrowserFolder):
    """
    Represents a folder in file system. Could be local folder or folder on omniverse server.
    Keyword Args:
        root (bool): If a root folder need to check connection status. Default False
        ignore_empty_folder (bool): Ignore empty folder. Default False
        ignore_file_without_thumbnail (bool): Ignore file without thumbnail. Default False

    Overridden functions:
        async bool start_traverse(): Start travserse to get all sub folders and filess in this folder.
            Notices: This is a coroutine and needs to be called in the correct way.
            for example, use await in other coroutine,or use asyncio.ensure_furture.

    Other args and Keyword args: Please refer to AbstractBrowserFolder.
    """

    def __init__(self, *args, **kwargs):
        root = kwargs.pop("root", False)
        self._ignore_empty_folder = kwargs.pop("ignore_empty_folder", False)
        self._ignore_file_without_thumbnail = kwargs.pop("ignore_file_without_thumbnail", False)
        self._ignore_sub_folder_with_files = kwargs.pop("ignore_sub_folder_with_files", False)
        self._cached_file_count = 0
        self._cached_sub_folder_count = 0
        self.has_update = False
        super().__init__(*args, **kwargs)
        if root:
            # If root folder, need to check connection status when list contents
            self._connection_status: Optional[omni.client.ConnectionStatus] = None
            self._subscription = omni.client.register_connection_status_callback(self._on_server_status_changed)
        else:
            # If not root folder, assume connected since checked in root folder
            self._connection_status = omni.client.ConnectionStatus.CONNECTED

    def _on_server_status_changed(self, url, status):
        if self.url.startswith(url):
            carb.log_info(f"[{self.url}] {url}: {status}")
            self._connection_status = status

    def destroy(self) -> None:
        super().destroy()

    async def _traverse_async(
        self,
        try_connect_nucleus: bool = True,
        defer_unreachable: bool = False,
        visited: Optional[Set[str]] = None,
        key: Optional[str] = None,
    ) -> TraverseResult:
        """
        Traverse this folder and everything beneath it, and report how it went.

        This is the recursive entry point: sub folders are gathered on *this*, not on
        :meth:`start_traverse`, so every gathered element is a status rather than a bool. It owns
        all of the non-connection work - the preparation reset and the scheme handling - so the
        root path and the recursive path cannot drift apart.

        Keyword Args:
            try_connect_nucleus (bool): False skips the connection attempt entirely.
            defer_unreachable (bool): True returns ``URL_UNREACHABLE`` instead of classifying a
                failed stat, so the caller can decide whether to open a connection. Only
                :meth:`start_traverse` passes this.
            visited (Optional[Set[str]]): Directories already walked, shared down the recursion.
                None starts a new set, which is what the root call does.
            key (Optional[str]): This folder's identity, worked out by the parent. None resolves it
                here, which is what the root does - it has no parent to inherit from.
        Return the outcome for this folder and its whole sub tree.
        """
        if visited is None:
            visited = set()
        if key is None:
            # The root, or a caller driving this directly. Everything below is handed its key by
            # its parent, so this is the only resolve most traverses ever do.
            key = resolve_folder_key(self.url)
        self._traverse_key = key
        if key in visited:
            # Already walked, under this name or another. Windows reaches one directory by several
            # paths on purpose - "AppData/Local/Application Data" is its own parent - so descending
            # everything that reports children walks in circles. Success with nothing found: the
            # content was collected on the first visit, and an empty folder is pruned away.
            carb.log_info(f"Skipping {self.url}: already traversed as {key}")
            self.prepared = True
            self.has_timeout = False
            self.sub_folders = []
            self.files = []
            self.last_traverse_result = TraverseResult.OK
            return TraverseResult.OK
        visited.add(key)
        self._traverse_visited = visited

        self.prepared: bool = False
        self.has_timeout = False
        # A new traverse supersedes whatever the last one was interrupted in the middle of.
        self.traverse_cancelled = False

        # Now donot clean sub folders and files
        # Instead, let's keep them to check if something changed
        for sub_folder in self.sub_folders:
            sub_folder.prepared = False
        for file in self.files:
            file.prepared = False
        self._cached_sub_folder_count = len(self.sub_folders)
        self._cached_file_count = len(self.files)
        self.has_update = False

        # No path may read the previous traverse's outcome.
        self.last_traverse_result = None
        self._last_stat_result = None
        self._last_list_result = None

        # For HTTP/HTTPS URLs (e.g., S3), skip stat check and go directly to listing.
        # S3 doesn't support HEAD on directory-style paths, so stat_async may return
        # ERROR_NOT_FOUND even for valid S3 prefixes that can be listed.
        # This avoids the misleading "Invalid URL" warning for HTTP/HTTPS URLs.
        broken_url = omni.client.break_url(self.url)
        if broken_url.scheme in ("http", "https"):
            return coerce_result(await self._traverse_folder_async(self.url))

        # Verify URL
        result, _ = await omni.client.stat_async(self.url)
        if result == omni.client.Result.OK:
            return coerce_result(await self._traverse_folder_async(self.url))

        self._last_stat_result = result

        if self._connection_status is not None and self._connection_status == omni.client.ConnectionStatus.CONNECTED:
            # Already connected
            carb.log_error(f"Invalid URL: {self.url} with error code {result}")
            return classify_result(result)

        if not try_connect_nucleus:
            carb.log_info(f"Do not try connecting to {self.url}")
            return classify_result(result)

        if broken_url.scheme == "omniverse":
            # Only the root wrapper can act on this: it is the one that opens connections.
            if defer_unreachable:
                return TraverseResult.URL_UNREACHABLE
            return classify_result(result)

        # OM-75623: Without internet connection, url will be invalid
        # But with alias, it may be redirect to a valid url
        # So still try traversing for now.
        carb.log_warn(f"Invalid URL: {self.url}")
        return coerce_result(await self._traverse_folder_async(self.url))

    async def start_traverse(
        self, try_connect_nucleus: bool = True, on_connected_fn: Callable[[AbstractBrowserFolder, bool], None] = None
    ) -> bool:
        """
        Start traverse folder to get sub folders and files.

        Root-facing wrapper. It owns the nucleus connection handshake and nothing else; the
        traversal itself lives in :meth:`_traverse_async`. The bool return is unchanged, so
        existing callers keep working - the folded outcome is published on
        ``self.last_traverse_result`` instead.

        Keyword Args:
            try_connect_nucleus (bool): Try connection to nucleus if not connected. Default True.
            on_connected_fn (Callable): Callback function on connection result.
        Return True if traverse done. Otherwise False means waiting for connection result.
        """
        result = await self._traverse_async(try_connect_nucleus=try_connect_nucleus, defer_unreachable=True)
        if result is not TraverseResult.URL_UNREACHABLE:
            self.last_traverse_result = result
            return True

        if self.__connect_nucleus(on_connected_fn):
            # Connection launched; the answer arrives through on_connected_fn. Deliberately leave
            # last_traverse_result as None - nothing has been decided yet.
            return False

        # No connector available, so no callback will ever arrive: settle it here instead.
        self.last_traverse_result = classify_result(self._last_stat_result)
        return True

    def __connect_nucleus(self, on_connected_fn) -> bool:
        """
        Attempt to open a nucleus connection for this folder's server.

        Return True if a connection was actually launched, in which case the caller must wait for
        ``on_connected_fn``. False means nothing was started and no callback will arrive, so the
        caller has to settle the outcome itself.
        """
        broken_url = omni.client.break_url(self.url)
        server_url = omni.client.make_url(scheme="omniverse", host=broken_url.host)

        def __on_connect_result(result: bool):
            if on_connected_fn:
                on_connected_fn(self, result)

        # OMPE-31528: Make it compatible with different nucleus connector API
        if _legacy_nucleus_connector:
            nucleus_connector = get_connector_instance()
            if not nucleus_connector:
                carb.log_warn(f"No nucleus connector available, cannot connect {server_url}")
                return False
            carb.log_info(f"Trying to connect {server_url}")
            nucleus_connector.connect(
                broken_url.host,
                server_url,
                on_success_fn=lambda *_: __on_connect_result(True),
                on_failed_fn=lambda *_: __on_connect_result(False),
            )
            return True

        carb.log_info(f"Trying to connect {server_url}")
        connect(
            broken_url.host,
            server_url,
            on_success_fn=lambda *_: __on_connect_result(True),
            on_failed_fn=lambda *_: __on_connect_result(False),
        )
        return True

    def create_file_object(self, url: str) -> FileSystemFile:
        """
        Create file object.
        Args:
            url: File Url.
        Return file object.
        """
        return FileSystemFile(url)

    def create_folder_object(self, name: str, url: str, **kwargs) -> AbstractBrowserFolder:
        """
        Create a folder object when a sub folder found. Default using FileSystemFolder.
        User could overridden to create own folder object for special usage.
        Args and keyword args please reference to FileSystemFolder.
        """
        return FileSystemFolder(name, url, **kwargs)

    async def _traverse_folder_async(self, url: str, recurse: bool = True) -> TraverseResult:
        """
        Traverse folder to list files with thumbnail and sub folders.

        Return the folded outcome for this folder and its sub tree. A listing that failed is a
        failure even when nothing raised - a timed out listing reports a status, not an exception
        - so the caller must inspect the result rather than only catching.
        """
        if self._on_traverse_status_fn:
            self._on_traverse_status_fn(self, status=TraverseStatus.START)

        if not url.endswith("/"):
            url += "/"

        # One slot per folder for its own work, released before the children are gathered - a parent
        # holding a slot while it waits for children that need one is a deadlock. And a frame first:
        # the app only gets to draw when every folder is waiting on one.
        ctx = self.traverse_ctx
        slot = ctx.folder_slot() if ctx is not None else None
        if ctx is not None:
            await ctx.wait_for_frame()
        if slot is not None:
            await slot.acquire()
        released = [slot is None]

        def release_slot():
            if not released[0]:
                released[0] = True
                slot.release()

        try:
            result = TraverseResult.OK
            entries = await self._list_folder_async(url)
            if entries is None:
                # Listing failed. A timeout is worth retrying; anything else is not.
                result = (
                    TraverseResult.RETRYABLE_FAILURE if self.has_timeout else classify_result(self._last_list_result)
                )
            if entries:
                thumbnail_paths = []
                files: List[BrowserFile] = []
                # (url, entry): the entry is kept so the child can be built without listing
                # its parent again.
                sub_folders: List[Tuple[str, object]] = []
                # (path, entry, wanted) per non-folder entry, so the folder's file count is known
                # before the first one is resolved. Dropped as soon as the folder is done.
                file_entries = []
                for entry in entries:
                    path = omni.client.combine_urls(url, entry.relative_path)
                    #  "\" used in local path, convert to "/"
                    path = path.replace("\\", "/")
                    if entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
                        if recurse:
                            dirs = path.split("/")
                            sub_folder_name = dirs[-1]
                            if sub_folder_name == THUMBNAIL_PATH:
                                thunmnail_path = url + THUMBNAIL_FULL_PATH
                                # For thumbnail, list it later to make sure files are loaded first
                                thumbnail_paths.append(thunmnail_path)
                            else:
                                if self._filter_folder(sub_folder_name):
                                    # Carried with its own entry: created after the loop, they all
                                    # used to be given whichever entry the loop ended on.
                                    sub_folders.append((path, entry))
                    else:
                        # Classified now, resolved below. Deciding "wanted" here costs one filter call
                        # that would otherwise happen inside _on_file_found_async anyway.
                        wanted = self._filter_file_fn is None or bool(self._filter_file_fn(path))
                        file_entries.append((path, entry, wanted))

                ctx = self.traverse_ctx
                if ctx is not None:
                    # Published once per listing, before any of these files is resolved, so resolved
                    # climbs behind found rather than the two being pinned to the same number. Only
                    # files matching the browser's filter count: a drive holds tens of thousands of
                    # .dll and .txt that would bury the materials the user is waiting for.
                    ctx.note_files_found(sum(1 for _, _, wanted in file_entries if wanted))

                for path, entry, wanted in file_entries:
                    self._raise_if_cancelled()
                    file = await self._on_file_found_async(path)
                    if file:
                        file.list_entry = entry
                        files.append(file)
                    ctx = self.traverse_ctx
                    if ctx is not None and wanted:
                        # Guarded on the same predicate as the count above: the two must agree, or
                        # resolved overruns found.
                        ctx.note_file_resolved()
                        if file:
                            # Only accepted files contribute items. A file the browser walked and threw
                            # away still counts as resolved - the work happened - but it produces
                            # nothing for the user to see.
                            ctx.note_items_resolved(file._item_count)
                    await self._yield_if_due()
                file_entries = None

                # Find thumbnails
                for thumbnail_path in thumbnail_paths:
                    await self.__traverse_thumbnail(thumbnail_path, files)

                # Filter valid files
                if self._ignore_file_without_thumbnail:
                    kept = [file for file in files if file.thumbnail]
                    dropped = [file for file in files if not file.thumbnail]
                    if dropped:
                        ctx = self.traverse_ctx
                        if ctx is not None:
                            # Counted when they were resolved, above, because whether a file has a
                            # thumbnail is not known until the thumbnails are walked.
                            ctx.note_files_dropped(len(dropped), sum(file._item_count for file in dropped))
                    files = kept

                # Compare to cache files and update. Indexed by url rather than scanned: the scan
                # was quadratic in the size of one folder - 67 s at 40,000 files against 0.012 s.
                # The index only narrows the candidates and equals() still decides, because
                # subclasses widen identity; every one of them requires the urls to match first.
                cached_by_url: Dict[str, List[BrowserFile]] = {}
                for cached_file in self.files:
                    cached_by_url.setdefault(cached_file._url_identity(), []).append(cached_file)

                for file in files:
                    for cached_file in cached_by_url.get(file._url_identity(), ()):
                        if file.equals(cached_file):
                            # Already in cache
                            cached_file.prepared = True
                            if (
                                hasattr(cached_file, "list_entry")
                                and hasattr(file, "list_entry")
                                and cached_file.list_entry != file.list_entry
                            ):
                                # Update file list entry if different (may be None in cached_file)
                                cached_file.list_entry = file.list_entry
                            break
                    else:
                        # Not in cache, either new or thumbnail changed
                        self.files.append(file)
                        # Indexed too: the scan this replaces saw what it had just appended, so a
                        # listing naming the same file twice matched itself rather than duplicating.
                        cached_by_url.setdefault(file._url_identity(), []).append(file)

                to_traverse_sub_folders = []
                if not self._ignore_sub_folder_with_files or not self.files:
                    # Donot list sub folder if files found in this folder
                    cached_folders = {local_url_key(sub_folder.url): sub_folder for sub_folder in self.sub_folders}
                    for path, sub_entry in sub_folders:
                        sub_folder = cached_folders.get(local_url_key(path))
                        if sub_folder is not None:
                            sub_folder.has_update = False
                            sub_folder.prepared = True
                        else:
                            sub_folder = await self._on_sub_folder_found_async(path, sub_entry)
                        if sub_folder:
                            # The whole sub tree reports into the root's context.
                            sub_folder.traverse_ctx = self.traverse_ctx
                            to_traverse_sub_folders.append(sub_folder)
                # Only keep available sub folders
                self.sub_folders = sorted(to_traverse_sub_folders, key=lambda x: x.name)

                if self._on_traverse_status_fn and len(to_traverse_sub_folders) > 0:
                    self._on_traverse_status_fn(self, status=TraverseStatus.SUB_FOLDERS_FOUND)

                # The folder's own work is done; let another folder in before waiting on children.
                release_slot()

                # Traverse sub folders in parallel, in bounded batches. Gathering every sub folder at
                # once is fine for a normal collection and pathological for a drive, where each level
                # multiplies the last until the event loop starves.
                #
                # return_exceptions keeps every sibling running when one fails, so this folder cannot
                # report a result while its own sub tree is still mutating. Consumed as a queue rather
                # than indexed, so pruned children are freed instead of held until this returns.
                self._raise_if_cancelled()
                pending = list(to_traverse_sub_folders)
                to_traverse_sub_folders = None
                child_results = []
                # Handed down so the whole sub tree shares one record of where it has been. Normally
                # set by _traverse_async on the way in; a subclass driving this method itself gets a
                # fresh set rather than none, so a loop is still cut.
                visited = self._traverse_visited
                if visited is None:
                    visited = self._traverse_visited = {resolve_folder_key(self.url)}
                parent_key = self._traverse_key or resolve_folder_key(self.url)

                # One round trip for the whole folder: which children are links, and what they point
                # at. Everything not in the answer takes its key from this folder's, which is what
                # keeps a filesystem call per directory off the event loop.
                links = await find_links_async([sub_folder.url for sub_folder in pending])

                while pending:
                    batch = pending[:MAX_CONCURRENT_SUB_FOLDERS]
                    del pending[:MAX_CONCURRENT_SUB_FOLDERS]
                    child_results.extend(
                        await asyncio.gather(
                            *[
                                sub_folder._traverse_async(
                                    visited=visited,
                                    key=links.get(sub_folder.url) or derive_folder_key(parent_key, sub_folder.name),
                                )
                                for sub_folder in batch
                            ],
                            return_exceptions=True,
                        )
                    )
                    del batch
                    # Drop this batch's empties now rather than after the whole sub tree is built:
                    # deferring keeps every descendant alive at once, so peak memory grows with the
                    # tree. It cascades for free, since children finish before their parent is checked.
                    self._prune_empty_sub_folders()
                result = fold_results([result, *child_results])

                # Timeout
                if not self.has_timeout:
                    for sub_folder in self.sub_folders:
                        if sub_folder.has_timeout:
                            self.has_timeout = True
                            break

            if self._on_traverse_status_fn:
                self._on_traverse_status_fn(self, status=TraverseStatus.COMPLETED)
            self._on_traverse_async_done()
            return result
        finally:
            release_slot()

    def _prune_empty_sub_folders(self) -> None:
        """
        Forget sub folders that turned out to hold nothing this browser can show.

        Only runs when the browser opted in with ``ignore_empty_folder``. A folder that timed out
        is kept: it is unknown, not known-empty, and dropping it would hide a retryable failure.
        """
        if not self._ignore_empty_folder:
            return
        self.sub_folders = [
            folder
            for folder in self.sub_folders
            if folder.files or folder.sub_folders or folder.has_timeout or not folder.prepared
        ]

    async def __traverse_thumbnail(self, url: str, files: List[BrowserFile]):
        """
        List all thumbnails and assign to file
        """
        if not url.endswith("/"):
            url += "/"

        entries = await self._list_folder_async(url)
        if entries:
            for entry in entries:
                path = omni.client.combine_urls(url, entry.relative_path)
                if not path.endswith(".png"):
                    continue
                #  "\" used in local path, convert to "/"
                path = path.replace("\\", "/")

                # Assign to related file
                for file in files:
                    if file.set_thumbnail(path):
                        file.thumbnail_list_entry = entry
                        break

    async def _list_folder_async(self, url: str) -> Optional[Tuple[omni.client.ListEntry]]:
        """List files on a omniverse server folder"""
        retry_count = 0
        while retry_count < MAX_RETRY_COUNT:
            if self._connection_status and self._connection_status == omni.client.ConnectionStatus.CONNECTING:
                # Wait for connected
                await asyncio.sleep(1)
            else:
                try:
                    result, entries = await asyncio.wait_for(omni.client.list_async(url), timeout=self._timeout)
                    if result == omni.client.Result.OK:
                        return entries
                    else:
                        carb.log_warn(f"Cannot list {url}, error code: {result}.")
                        self._last_list_result = result
                        return None
                # Deliberately Exception, not BaseException: CancelledError is a BaseException on
                # 3.8+, so it passes through and the traverse unwinds, which is what cancel needs.
                # Widening this catch would turn a cancel into a retry loop.
                except Exception:  # MM-CHANGE: change to always retry
                    if (
                        self._connection_status is None
                        or self._connection_status == omni.client.ConnectionStatus.CONNECTED
                    ):
                        retry_count += 1
                    else:
                        # Not connected, try later
                        carb.log_info(f"[{url}] Not connected, try later")
        else:
            self.has_timeout = True
            carb.log_error(
                f"Timeout {self._timeout} seconds when listing {url}. Please check your network and connection to the url. Otherwise increase the timeout."
            )

    def _raise_if_cancelled(self) -> None:
        """
        Unwind if this traverse has been terminalized.

        Cancelling the root task already interrupts whatever it is awaiting, so this is not what
        makes cancel work - it is what makes it *prompt*. Between two awaits the loop can be part
        way through a folder's files, and without a check it would finish that folder, and every
        folder queued behind it in the same coroutine, before the cancellation was noticed.
        """
        ctx = self.traverse_ctx
        if ctx is not None and ctx.is_terminal:
            raise asyncio.CancelledError(f"traverse of {self.url} was {ctx.state.value}")

    async def _yield_if_due(self) -> None:
        """
        Give the app a frame every ``yield_every_n_files`` files.

        Without this the traversal holds the event loop for its whole duration: the app stops
        ticking, so the spinner does not animate and the progress popup never repaints - the very
        freeze this work exists to remove.

        Only yields when a context is attached. That deliberately excludes ``__warmup``, which
        drives traversal from its own private event loop where the app's ``next_update_async``
        future would never complete.
        """
        ctx = self.traverse_ctx
        if ctx is None:
            return
        await ctx.yield_if_due()

    def _on_traverse_async_done(self, loading_completed=True) -> None:
        """Callback when folder traverse done"""
        self.has_update = self._is_folder_updated()
        if self.has_update:
            carb.log_info(f"{self.name} updated")
        self.prepared = True
        if self._on_traverse_done_fn is not None:
            self._on_traverse_done_fn(self, loading_completed=loading_completed, updated=self.has_update)

    def _is_folder_updated(self):
        """
        Check if folder udpated after traverse.
        Changes in either files or sub folder means updated.
        """
        file_update = False
        if len(self.files) != self._cached_file_count:
            file_update = True

        # Files in cache but not in traverse result
        remove_files = [file for file in self.files if not file.prepared]
        if remove_files:
            for remove in remove_files:
                self.files.remove(remove)
            file_update = True

        if file_update:
            self.files.sort(key=lambda item: item.url)

        folder_updated = False
        if len(self.sub_folders) != self._cached_sub_folder_count:
            folder_updated = True

        # Sub folders in cache but not in traverse result
        remove_sub_folders = [folder for folder in self.sub_folders if not folder.prepared]
        if remove_sub_folders:
            for remove in remove_sub_folders:
                self.sub_folders.remove(remove)
            folder_updated = True

        if folder_updated:
            self.sub_folders.sort(key=lambda item: item.name)

        # Still need to look into sub folder to make sure all items in order
        for sub_folder in self.sub_folders:
            # Sub folder already check update status, just read
            if sub_folder.has_update:
                folder_updated = True
                break

        return file_update or folder_updated
