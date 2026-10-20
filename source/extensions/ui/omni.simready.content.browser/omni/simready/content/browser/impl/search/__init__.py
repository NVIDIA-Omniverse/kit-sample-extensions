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

from __future__ import annotations

import functools
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Literal
from urllib.parse import quote


@functools.total_ordering
class SearchBackend(Enum):
    USD_SEARCH = "AI Search"
    WORKSPACE_CACHE = "Database"
    FILE_INDEX = "File Index"

    def __lt__(self, other: SearchBackend) -> bool:
        if self.__class__ is other.__class__:
            members = list(self.__class__)
            return members.index(self) < members.index(other)
        return NotImplemented


@dataclass
class SearchParams:
    # Structured filter fields
    profile_filter: str = ""
    feature_filter: str = ""
    tag_filter: str = ""
    name_filter: str = ""
    # Natural-language phrase for USD Search backend
    phrase_filter: str = ""

    # Match mode: "any" = OR, "all" = AND
    match_mode: Literal["any", "all"] = "any"

    relevance_cutoff: float = 0.0

    # Available values for autocomplete (populated from AssetLibrary after loading)
    available_profiles: list[str] = field(default_factory=list)
    available_features: list[str] = field(default_factory=list)
    available_tags: list[str] = field(default_factory=list)

    def to_query_string(self) -> str:
        parts: list[str] = []

        def add_filter_parts(prefix: str, value: str):
            for v in value.split():
                # A stray double quote would close the quoting added below.
                v = v.replace('"', "").strip()
                if v:
                    parts.append(f"{prefix}:{v}")

        # Phrase is URL-encoded so it stays a single token through the space-delimited round-trip
        if self.phrase_filter:
            parts.append(f"phrase:{quote(self.phrase_filter, safe='')}")

        if self.profile_filter:
            add_filter_parts("profile", self.profile_filter)
        if self.feature_filter:
            add_filter_parts("feature", self.feature_filter)
        if self.tag_filter:
            add_filter_parts("tag", self.tag_filter)
        if self.name_filter:
            add_filter_parts("name", self.name_filter)

        if self.relevance_cutoff > 0.0:
            parts.append(f"relevance:{self.relevance_cutoff}")

        if not parts:
            return ""

        separator = "+" if self.match_mode == "all" else " "
        # Quoted as a single term because this string is handed to the Kit
        # search field, which parses it with `omni.search_grammar`. That grammar
        # only knows its own prefixes, so "profile"/"feature"/"phrase"/
        # "relevance" fall into its "error" bucket -- two or more of them warn
        # with "more than 1 value for query: error", and a stricter grammar can
        # reject the query, cancelling the search before it reaches
        # `AssetLibrarySearchModel`. `parse_query_string_to_filters` unwraps it.
        # Example (match_mode="any"): profile="vehicle", feature="rigid_body"
        #   -> '"profile:vehicle feature:rigid_body"'
        return f'"{separator.join(parts)}"'

    @property
    def raw_search_query(self) -> str:
        return self.to_query_string()


# Per-backend default SearchParams. Two roles:
#   1. Pre-populate the UI fields when a backend becomes active.
#   2. Act as the reference "unchanged" value against which the current
#      `State.search_params` is compared to decide whether clicking Search
#      (or auto-firing on edit) should actually run a query.
#
# Each backend owns its own default so we can tune UX per mode without
# cross-talk (e.g., a different `relevance_cutoff` only makes sense for
# USD_SEARCH).
SEARCH_PARAMETERS_DEFAULT: dict[SearchBackend, SearchParams] = {
    # USD search: non-zero default so the first query applies the same cutoff
    # the relevance slider shows (see panel ReadyState); 0.0 means "omit filter".
    SearchBackend.USD_SEARCH: SearchParams(relevance_cutoff=0.4),
    SearchBackend.WORKSPACE_CACHE: SearchParams(),
    SearchBackend.FILE_INDEX: SearchParams(),
}


def default_params_for(backend: SearchBackend) -> SearchParams:
    """Return a fresh copy of the default SearchParams for ``backend``.

    A copy is returned so callers can store the result in mutable state
    without risk of aliasing the shared default instance in
    ``SEARCH_PARAMETERS_DEFAULT``.
    """
    return replace(SEARCH_PARAMETERS_DEFAULT.get(backend, SearchParams()))


def is_default_params(backend: SearchBackend, params: SearchParams) -> bool:
    """True when ``params`` equals the default for ``backend``.

    Used to short-circuit search dispatch when the user hasn't changed
    anything meaningful — clicking Search (or an auto-fire on edit) with
    fully-default params is a no-op.
    """
    return params == SEARCH_PARAMETERS_DEFAULT.get(backend, SearchParams())


from .file_index import AssetLibraryFileIndex  # noqa: E402
from .interface import AssetLibraryInterface, SearchResult  # noqa: E402
from .usd_search import AssetLibraryUsdSearch  # noqa: E402
from .workspace_cache import AssetLibraryWorkspaceCache  # noqa: E402

__all__ = [
    "SearchBackend",
    "SearchParams",
    "SEARCH_PARAMETERS_DEFAULT",
    "default_params_for",
    "is_default_params",
    "AssetLibraryInterface",
    "SearchResult",
    "AssetLibraryUsdSearch",
    "AssetLibraryWorkspaceCache",
    "AssetLibraryFileIndex",
]
