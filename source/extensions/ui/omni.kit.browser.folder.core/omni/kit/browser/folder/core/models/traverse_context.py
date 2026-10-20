# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TraverseState", "TraverseContext"]

import asyncio
import enum
import time

import carb.settings
import omni.kit.app

SETTING_MAX_CONCURRENT_FOLDERS = "/exts/omni.kit.browser.folder.core/traverse/max_concurrent_folders"
# How many folders may be doing their own work at once, across the whole tree. The existing batch of
# 8 is per level and levels nest - 740 folder traversals were measured in flight on a drive scan -
# and Kit's update observer drains asyncio until the loop goes idle, so a traverse that always has
# ready work starves the app of frames.
DEFAULT_MAX_CONCURRENT_FOLDERS = 16

SETTING_YIELD_EVERY_N_FILES = "/exts/omni.kit.browser.folder.core/traverse/yield_every_n_files"
DEFAULT_YIELD_EVERY_N_FILES = 32
# Counter updates are coalesced to this interval. Fast enough to look live, slow enough that the
# observer chain costs nothing next to the traversal.
PROGRESS_NOTIFY_INTERVAL = 0.1


class TraverseState(enum.Enum):
    """
    Lifecycle of one root collection's traverse.

    ``DONE``, ``FAILED`` and ``CANCELLED`` are terminal. Terminal contexts never appear in the model's
    ``active_folders``: the list holds pending and active work only, which is what lets the
    progress popup render it directly with no filtering.
    """

    QUEUED = "queued"
    CONNECTING = "connecting"
    SCANNING = "scanning"
    REFRESHING = "refreshing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (TraverseState.DONE, TraverseState.FAILED, TraverseState.CANCELLED)


class TraverseContext:
    """
    Per-root traverse state: what it is doing and how far it has got.

    One context exists per root collection while that collection is queued or scanning, and the
    whole sub tree shares it so file counts aggregate. It is owned by the folder object
    (``folder.traverse_ctx``), which gives identity for free - the model builds a new folder object
    on every add, so a removed-then-re-added collection cannot be confused with its predecessor.

    Args:
        folder: The root folder this context tracks.
        state: Initial state, normally ``QUEUED``.
        on_progress_fn: Called on the event loop when counters or state change. Counter updates
            are coalesced to ``PROGRESS_NOTIFY_INTERVAL``; state changes are always delivered.
    """

    def __init__(self, folder, state: TraverseState = TraverseState.QUEUED, on_progress_fn=None):
        self.folder = folder
        self.url = folder.url
        self.name = getattr(folder, "name", folder.url)
        self._state = state
        self._on_progress_fn = on_progress_fn

        self._folder_slot = None
        self.files_found: int = 0
        self.files_resolved: int = 0
        # Browsable items produced by the files resolved so far. Not the same as the file count:
        # one file can hold many items - a .usd with several UsdShade.Material prims becomes
        # several entries in the browser - or, once rejected, none at all.
        self.items_resolved: int = 0
        self.started_at: float = time.time()
        self._last_notify: float = 0.0

        # Set once when the traverse ends, for logs and for the failure surface.
        self.result = None
        # The task running this root's traverse, set by the worker when it starts one. Cancelling a
        # collection cancels this; the children fan out under it and unwind with it.
        self.task = None
        # Why it ended, for the log. The UI shows the state, never this.
        self.reason = None

        settings = carb.settings.get_settings()
        every = settings.get(SETTING_YIELD_EVERY_N_FILES)
        self._yield_every_n_files = every if isinstance(every, int) and every > 0 else DEFAULT_YIELD_EVERY_N_FILES

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"<TraverseContext {self.name} {self._state.value} "
            f"{self.files_resolved}/{self.files_found} files, {self.items_resolved} items>"
        )

    @property
    def state(self) -> TraverseState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state.is_terminal

    @property
    def cancelled(self) -> bool:
        """Derived from the state, never stored: one source of truth cannot go out of sync."""
        return self._state is TraverseState.CANCELLED

    def set_state(self, state: TraverseState) -> None:
        if state is self._state:
            return
        self._state = state
        self._notify()

    def note_files_found(self, count: int) -> None:
        """
        Add a whole folder's worth of files at once.

        Bulk by design: a listing reports every file in a folder in one go, so found jumps by the
        folder and resolved climbs behind it. Incrementing found per file instead - next to the
        resolved increment - would make the two counters move in lockstep and show the user the
        same number twice.
        """
        if count <= 0:
            return
        self.files_found += count
        self._notify(throttled=True)

    def note_file_resolved(self) -> None:
        self.files_resolved += 1
        self._notify(throttled=True)

    def note_files_dropped(self, files: int, items: int) -> None:
        """
        Take back files the browser walked and then refused to show.

        The counters report what the user will get, not what the walk touched: files the browser's
        filter rejects are never counted in the first place. A browser that hides files without a
        thumbnail rejects them later, after they have been counted, so the same rule is applied
        here rather than leaving the window promising items that never appear.
        """
        self.files_found = max(0, self.files_found - files)
        self.files_resolved = max(0, self.files_resolved - files)
        self.items_resolved = max(0, self.items_resolved - items)
        self._notify()

    def note_items_resolved(self, count: int) -> None:
        """Record the browsable items one resolved file turned into."""
        if count <= 0:
            return
        self.items_resolved += count
        self._notify(throttled=True)

    def folder_slot(self):
        """
        The tree-wide limit on folders doing their own work at once.

        Lives on the context because one context is shared by a root and everything beneath it,
        which is the scope the limit needs. Created on first use so it binds to the loop actually
        running the traverse.
        """
        if self._folder_slot is None:
            limit = carb.settings.get_settings().get(SETTING_MAX_CONCURRENT_FOLDERS)
            if not isinstance(limit, int) or limit <= 0:
                limit = DEFAULT_MAX_CONCURRENT_FOLDERS
            self._folder_slot = asyncio.Semaphore(limit)
        return self._folder_slot

    async def wait_for_frame(self) -> None:
        """
        Park until the app draws a frame.

        This is the only kind of wait that lets the app run: a coroutine waiting on a frame is not
        ready, so once every folder is waiting the asyncio loop goes idle and Kit's pump returns.
        Waiting on anything else just keeps the pump busy.
        """
        await omni.kit.app.get_app().next_update_async()

    async def yield_if_due(self) -> None:
        """Hand a frame back to the app every ``yield_every_n_files`` resolved files."""
        if self.files_resolved % self._yield_every_n_files:
            return
        await omni.kit.app.get_app().next_update_async()

    def _notify(self, throttled: bool = False) -> None:
        """
        Publish a change.

        Counter updates are throttled at the source, not just in the widgets that render them: a
        large scan resolves entries faster than any UI can use, and every notification runs the
        whole observer chain. Left unthrottled this costs more event-loop time than the traversal
        it is reporting on. State changes are rare and drive visible transitions, so they always
        go straight through.
        """
        if self._on_progress_fn is None:
            return
        if throttled:
            now = time.time()
            if now - self._last_notify < PROGRESS_NOTIFY_INTERVAL:
                return
            self._last_notify = now
        self._on_progress_fn(self)
