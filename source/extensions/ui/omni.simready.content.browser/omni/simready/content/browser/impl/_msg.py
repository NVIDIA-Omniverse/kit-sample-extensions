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

"""All message types for the Elm-like update loop.

Every external event and every user action is represented as a frozen dataclass.
The runtime receives a ``Msg``, passes it to ``update()``, and never mutates
state directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from omni.kit.widget.filebrowser import FileBrowserItem

    from ._url import Url
    from .search import AssetLibraryInterface, SearchBackend, SearchParams

# ---------------------------------------------------------------------------
# External events — originate outside the UI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrowserSelectionChanged:
    """A new item was selected (or deselected) in the content browser tree."""

    selected_items: list[FileBrowserItem] | None


@dataclass(frozen=True)
class SearchEngineActivated:
    """Our search engine was made the active engine in the content browser."""


@dataclass(frozen=True)
class AssetSearchMenuClicked:
    """User triggered "AssetSearch here" from the context menu."""

    item_path: str


@dataclass(frozen=True)
class BackendLoaded:
    """A search backend finished loading successfully."""

    library: "AssetLibraryInterface"


@dataclass(frozen=True)
class BackendLoadFailed:
    """A search backend failed to load."""

    error: Exception


@dataclass(frozen=True)
class IndexingProgress:
    """Periodic progress update during file indexing."""

    file_count: int
    elapsed: float


@dataclass(frozen=True)
class IndexingDone:
    """File indexing completed successfully."""

    asset_count: int


@dataclass(frozen=True)
class IndexingFailed:
    """File indexing failed with an error."""

    error: Exception


@dataclass(frozen=True)
class SearchCompleted:
    """A search query finished and returned results."""

    asset_count: int
    duration: float


@dataclass(frozen=True)
class SearchStarted:
    """A search query was dispatched to the backend."""


@dataclass(frozen=True)
class BackendsResolved:
    """The runtime determined which backends are available for a URL."""

    url: "Url"
    available: list["SearchBackend"]


# ---------------------------------------------------------------------------
# User actions — originate from the UI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SearchParamsChanged:
    """User changed any search filter field."""

    params: "SearchParams"


@dataclass(frozen=True)
class MatchModeChanged:
    """User toggled the Any/All match-mode switch.

    Distinct from ``SearchParamsChanged`` because the match mode is purely
    a combinator: changing it should update the stored ``SearchParams`` but
    must NOT fire a new search on its own (see `_update.py`).
    """

    mode: Literal["any", "all"]


@dataclass(frozen=True)
class IndexFilesClicked:
    """User clicked the "Index Files" button."""


@dataclass(frozen=True)
class SearchClicked:
    """User clicked the "Search" button."""


@dataclass(frozen=True)
class WizardUiClosed:
    """The search wizard window was hidden/closed by the user."""


@dataclass(frozen=True)
class AssetSearchModeSelected:
    """User changed the Asset Search toolbar mode dropdown."""

    backend: "SearchBackend | None"


# ---------------------------------------------------------------------------
# Union alias — use as the type annotation for the dispatch callable
# ---------------------------------------------------------------------------

Msg = Union[
    BrowserSelectionChanged,
    SearchEngineActivated,
    AssetSearchMenuClicked,
    BackendLoaded,
    BackendLoadFailed,
    BackendsResolved,
    IndexingProgress,
    IndexingDone,
    IndexingFailed,
    SearchCompleted,
    SearchStarted,
    SearchParamsChanged,
    MatchModeChanged,
    IndexFilesClicked,
    SearchClicked,
    WizardUiClosed,
    AssetSearchModeSelected,
]
