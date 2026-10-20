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

from dataclasses import dataclass, field
from enum import Enum

from ._url import Url
from .search import SearchBackend, SearchParams, default_params_for


class UiPhase(Enum):
    """UI lifecycle phase — stored in State so the view can be driven from it."""

    Loading = "Loading"
    Ready = "Ready"
    LoadingError = "Error"
    Unsupported = "Unsupported"
    UnsupportedMultipleItems = "UnsupportedMultipleItems"


def _initial_search_params() -> SearchParams:
    """Match ``SEARCH_PARAMETERS_DEFAULT`` for the default active backend (USD)."""
    return default_params_for(SearchBackend.USD_SEARCH)


@dataclass
class State:
    active_backend: SearchBackend = SearchBackend.USD_SEARCH
    search_params: SearchParams = field(default_factory=_initial_search_params)
    # Display any status message at the bottom of the window
    status_message: None | str = None
    # selected content location
    selected_url: Url | None = None
    # tree location selected in the context menu
    search_location_anchor: Url | None = None
    usd_search_endpoint: str | None = None
    # locations to index files from
    file_index_locations: list[Url] = field(default_factory=list)
    # number of assets indexed
    indexing_asset_count: int | None = None
    # Autocomplete suggestion pools populated from the loaded AssetLibrary.
    # These describe what the UI can offer, not what the user has picked, so
    # they live on State rather than on SearchParams.
    available_profiles: list[str] = field(default_factory=list)
    available_features: list[str] = field(default_factory=list)
    available_tags: list[str] = field(default_factory=list)
    # UI lifecycle phase — drives which panel SearchWizardUi renders
    ui_phase: UiPhase = UiPhase.Loading
    # Set by `BackendSelected` and consumed by `BackendLoaded` to gate the
    # tree-view re-filter + shortcut re-selection to *mode switches only*.
    # Without this, every library load (including the one triggered by a user
    # click in the tree) would re-apply the filter and snap selection back to
    # the injected shortcut.
    pending_tree_filter_backend: SearchBackend | None = None
