# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pure state-transition function for the Elm-like update loop.

``update(msg, state)`` is the single location where every state change is
defined.  It is deliberately free of I/O, Kit API calls, and UI manipulation
so that all branches can be unit-tested without a running application.

Side effects (loading backends, firing searches, etc.) are communicated back to
the runtime as ``Cmd`` values in the returned list.
"""

from __future__ import annotations

import dataclasses

from omni.kit.widget.filebrowser import FileBrowserItem, FileSystemItem

from ._cmd import (
    ActivateAssetSearch,
    ApplyTreeFilter,
    ClearTreeFilter,
    Cmd,
    DeactivateAssetSearch,
    LoadBackend,
    SetBrowserSearchEngine,
    StartIndexing,
    TriggerSearch,
)
from ._msg import (
    AssetSearchMenuClicked,
    AssetSearchModeSelected,
    BackendLoaded,
    BackendLoadFailed,
    BackendsResolved,
    BrowserSelectionChanged,
    IndexFilesClicked,
    IndexingDone,
    IndexingFailed,
    IndexingProgress,
    MatchModeChanged,
    Msg,
    SearchClicked,
    SearchCompleted,
    SearchEngineActivated,
    SearchParamsChanged,
    SearchStarted,
    WizardUiClosed,
)
from ._state import State, UiPhase
from ._url import Url, UrlOrigin
from .search import default_params_for, is_default_params

# Shown in the wizard's status line when Search is triggered (by click or
# auto-fire) while every field still matches the active backend's default.
_EMPTY_SEARCH_HINT = "Set at least one filter to search."


def update(msg: Msg, state: State) -> tuple[State, list[Cmd], bool]:  # noqa: C901 — intentionally exhaustive
    """Return a new ``State``, a list of side-effect commands, and a rebuild flag.

    The rebuild flag tells the runtime whether the view should be fully
    reconstructed from the new state (``True``) or whether the state change
    is purely internal and the existing widgets remain valid (``False``).

    The input ``state`` is never mutated; a shallow copy is made at the
    start of every branch.
    """
    s = dataclasses.replace(state)

    # ------------------------------------------------------------------
    # External events
    # ------------------------------------------------------------------

    if isinstance(msg, BrowserSelectionChanged):
        # Selection changes are anchor-only: no backend discovery, no library
        # (re)load. Mode/backend is driven by the search-mode selector alone;
        # picking a folder in the tree just narrows the search anchor. This
        # is what keeps the programmatic `select_and_center` on our injected
        # shortcut from feeding back into the load loop.
        if msg.selected_items and len(msg.selected_items) > 1:
            s.selected_url = None
            s.search_location_anchor = None
            s.ui_phase = UiPhase.UnsupportedMultipleItems
            return s, [], True

        url: Url | None = None
        if msg.selected_items:
            item = msg.selected_items[0]
            # Selection API returns `str` (tree pane) or `FileBrowserItem`
            # (list pane) in different situations.
            item_path = item
            if isinstance(item, (FileBrowserItem, FileSystemItem)):
                if not item.is_folder:
                    return state, [], False
                item_path = item.path
            url = Url.parse_from_str(item_path)

        if state.selected_url == url:
            # No-op on redundant events (notably: the filepicker re-emits the
            # selection right after our programmatic `select_and_center`).
            return state, [], False

        s.selected_url = url
        s.search_location_anchor = url
        if url is not None and url.origin == UrlOrigin.LOCAL and state.file_index_locations != [str(url)]:
            s.file_index_locations = [str(url)]
        # Nudge the UI out of UnsupportedMultipleItems if we were there.
        if state.ui_phase == UiPhase.UnsupportedMultipleItems:
            s.ui_phase = UiPhase.Ready
        return s, [], True

    if isinstance(msg, BackendsResolved):
        # Retained for backwards-compat; no longer part of the active flow.
        return s, [], False

    if isinstance(msg, SearchEngineActivated):
        # No state change needed; the runtime will open the wizard UI.
        return s, [], True

    if isinstance(msg, AssetSearchMenuClicked):
        url = Url.parse_from_str(msg.item_path)
        if url is None:
            return state, [], False
        s.selected_url = url
        s.search_location_anchor = url
        return s, [SetBrowserSearchEngine("SimReady Search")], True

    if isinstance(msg, BackendLoaded):
        s.ui_phase = UiPhase.Ready
        cmds: list[Cmd] = []
        if state.pending_tree_filter_backend == state.active_backend:
            cmds.append(ApplyTreeFilter(state.active_backend))
            s.pending_tree_filter_backend = None
        return s, cmds, True

    if isinstance(msg, BackendLoadFailed):
        s.status_message = str(msg.error)
        s.ui_phase = UiPhase.LoadingError
        return s, [], True

    if isinstance(msg, IndexingProgress):
        s.status_message = f"Indexed {msg.file_count} files in [{msg.elapsed:.1f}s]"
        return s, [], True

    if isinstance(msg, IndexingDone):
        s.indexing_asset_count = msg.asset_count
        s.status_message = f"Indexed {msg.asset_count} files"
        return s, [], True

    if isinstance(msg, IndexingFailed):
        s.status_message = f"Indexing failed: {msg.error}"
        return s, [], True

    if isinstance(msg, SearchCompleted):
        s.status_message = f"{msg.asset_count} entries found in [{msg.duration:.1f}s]"
        return s, [], True

    if isinstance(msg, SearchStarted):
        s.status_message = "Searching..."
        return s, [], True

    # ------------------------------------------------------------------
    # User actions from the UI
    # ------------------------------------------------------------------

    if isinstance(msg, AssetSearchModeSelected):
        if msg.backend is None:
            s.selected_url = None
            s.search_location_anchor = None
            s.status_message = None
            s.pending_tree_filter_backend = None
            return s, [DeactivateAssetSearch()], True

        # if msg.backend == state.active_backend:
        #     return state, [], False
        s.active_backend = msg.backend
        s.selected_url = None
        s.search_location_anchor = None
        # Seed from the per-backend defaults so the UI pre-populates sensible
        # values for the newly-activated mode (and so `SearchClicked` knows
        # when the user hasn't actually changed anything — see below).
        s.search_params = default_params_for(msg.backend)
        s.status_message = None
        s.ui_phase = UiPhase.Loading
        # Mark this load as a mode switch so `BackendLoaded` knows to re-filter
        # the tree (and re-select the backend's default shortcut) on success.
        # Plain URL-change loads leave this flag alone and skip re-filtering.
        s.pending_tree_filter_backend = msg.backend
        return s, [ActivateAssetSearch(), LoadBackend(msg.backend, url=None)], True

    if isinstance(msg, MatchModeChanged):
        # Pure combinator — update the stored params, but deliberately emit
        # no `TriggerSearch`. Also leave `status_message` untouched: an
        # active "Set at least one filter..." hint is still valid because
        # match mode alone never produces a meaningful query.
        if s.search_params.match_mode == msg.mode:
            return state, [], False
        s.search_params = dataclasses.replace(s.search_params, match_mode=msg.mode)
        return s, [], False

    if isinstance(msg, SearchParamsChanged):
        s.search_params = msg.params
        # Don't auto-fire a search when the user has reverted every field back
        # to its default — an empty phrase (USD) or empty filters (cache/index)
        # would produce a meaningless query.
        if is_default_params(s.active_backend, msg.params):
            s.status_message = _EMPTY_SEARCH_HINT
            return s, [], False
        # A real search is about to fire — clear any lingering hint so the
        # status line is blank until `SearchStarted` arrives from the runtime.
        s.status_message = None
        return s, [TriggerSearch(msg.params)], False

    if isinstance(msg, IndexFilesClicked):
        from ._config import get_extension_config

        locations = [s.selected_url] if s.selected_url else get_extension_config().default_file_index_locations
        return s, [StartIndexing(locations, url=s.selected_url)], True

    if isinstance(msg, SearchClicked):
        # Ignore the click if the user hasn't deviated from the backend's
        # default filters — nothing meaningful to search for. Surface a hint
        # in the status line so the click isn't silently swallowed.
        if is_default_params(s.active_backend, s.search_params):
            s.status_message = _EMPTY_SEARCH_HINT
            return s, [], False
        # Real search — clear any lingering hint before the runtime takes
        # over and dispatches `SearchStarted` → "Searching...".
        s.status_message = None
        return s, [TriggerSearch(s.search_params)], False

    if isinstance(msg, WizardUiClosed):
        # Drop any pending filter bookkeeping so reopening the wizard will re-arm the filter.
        s.pending_tree_filter_backend = None
        return s, [ClearTreeFilter()], False

    # Unknown message — return state unchanged (future-proof).
    return state, [], False
