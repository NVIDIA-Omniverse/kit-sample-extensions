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

"""
update() returns a list of Cmd values describing what the runtime should *do*
after a state transition, no logic lives here, these are pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ._url import Url
    from .search import SearchBackend, SearchParams


@dataclass(frozen=True)
class LoadBackend:
    """Ask the runtime to load (or attach) the given search backend."""

    backend: "SearchBackend"
    url: "Url | None" = None


@dataclass(frozen=True)
class StartIndexing:
    """Ask the runtime to start file indexing at the given locations."""

    locations: list = field(default_factory=list)
    url: "Url | None" = None


@dataclass(frozen=True)
class TriggerSearch:
    """Ask the runtime to fire a search query through the content browser delegate."""

    search_params: "SearchParams"


@dataclass(frozen=True)
class SetBrowserSearchEngine:
    """Ask the runtime to switch the active search engine in the content browser."""

    name: str


@dataclass(frozen=True)
class ShowErrorPrompt:
    """Ask the runtime to display a modal error prompt to the user."""

    title: str
    message: str


@dataclass(frozen=True)
class ResolveBackends:
    """Ask the runtime to determine which backends are available for a URL."""

    url: "Url"


@dataclass(frozen=True)
class ApplyTreeFilter:
    """Ask the runtime to re-filter the Content Browser tree for the given backend."""

    backend: "SearchBackend"


@dataclass(frozen=True)
class ClearTreeFilter:
    """Ask the runtime to drop the Content Browser tree filter and deactivate it.

    Emitted when the search wizard UI is closed — the tree should return to
    its unfiltered default behavior, and the next wizard activation re-arms
    the filter from scratch.
    """


@dataclass(frozen=True)
class ActivateAssetSearch:
    """Ask the runtime to activate SimReady asset-search functionality."""


@dataclass(frozen=True)
class DeactivateAssetSearch:
    """Ask the runtime to deactivate SimReady asset-search functionality."""


# Cmd union alias

Cmd = Union[
    LoadBackend,
    StartIndexing,
    TriggerSearch,
    SetBrowserSearchEngine,
    ShowErrorPrompt,
    ResolveBackends,
    ApplyTreeFilter,
    ClearTreeFilter,
    ActivateAssetSearch,
    DeactivateAssetSearch,
]
