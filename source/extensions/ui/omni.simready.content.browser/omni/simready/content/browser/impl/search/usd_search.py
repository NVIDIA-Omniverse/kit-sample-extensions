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

import asyncio

import simready.search as lib

from . import SearchBackend
from .interface import AssetLibraryInterface, SearchResult


class AssetLibraryUsdSearch(AssetLibraryInterface):
    def __init__(self, endpoint: str):
        self._library: lib.AssetLibrary | None = None
        self._endpoint = endpoint

    @property
    def backend_type(self) -> SearchBackend:
        return SearchBackend.USD_SEARCH

    async def initialize(self):
        self._library = lib.AssetLibrary(raise_on_network_error=True)
        self._library.add_service_source(self._endpoint)

    async def search(self, query: str, base_path: str | None = None) -> list[SearchResult]:
        results = []
        filters = self.parse_query_string_to_filters(query)
        if not self._library:
            return results
        base_path = [base_path] if base_path else None
        response = await asyncio.to_thread(
            self._library.search,
            **filters,
            remove_duplicates=True,
            base_paths=base_path,
            max_count=64,
        )
        for result in response:
            results.append(SearchResult(result.asset_path, result.relevance_score))
        return results

    def get_available_profiles(self) -> list[str]:
        return []

    def get_available_features(self) -> list[str]:
        return []
