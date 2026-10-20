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
from typing import Awaitable

import simready.search as lib
from omni.kit.async_engine import run_coroutine

from . import SearchBackend
from .interface import AssetLibraryInterface, SearchResult


class AssetLibraryFileIndex(AssetLibraryInterface):
    def __init__(self):
        self._library: lib.AssetLibrary | None = None
        self._indexing_task: asyncio.Task | None = None
        self._indexed_locations: set[str] = set()

    @staticmethod
    def _normalize_location(location: str) -> str:
        location = location.strip()
        if not location:
            return ""
        if location.endswith("://"):
            return location
        return location if location.endswith("/") else f"{location}/"

    @classmethod
    def _is_location_covered(cls, location: str, indexed_locations: set[str]) -> bool:
        normalized_location = cls._normalize_location(location)
        if not normalized_location:
            return True
        return any(normalized_location.startswith(indexed_location) for indexed_location in indexed_locations)

    @property
    def backend_type(self) -> SearchBackend:
        return SearchBackend.FILE_INDEX

    async def initialize(self):
        self._library = lib.AssetLibrary(raise_on_network_error=True)

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
        )
        for result in response:
            results.append(SearchResult(result.asset_path, result.relevance_score))
        return results

    def index_locations(self, locations: list[str], directory_type: str = "s3") -> None | Awaitable[None]:
        if not self._library:
            return

        indexed_locations = set(self._indexed_locations)
        new_locations: list[str] = []
        for location in locations:
            normalized_location = self._normalize_location(location)
            if not normalized_location:
                continue
            if self._is_location_covered(normalized_location, indexed_locations):
                continue
            new_locations.append(location)
            indexed_locations.add(normalized_location)

        if not new_locations:
            return None

        self._indexed_locations = indexed_locations
        library = self._library

        async def _index_all():
            await asyncio.gather(*[library.add_indexed_source(loc, directory_type) for loc in new_locations])

        self._indexing_task = run_coroutine(_index_all())
        return self._indexing_task

    def is_indexing(self) -> bool:
        if self._library is not None and self._library.is_loading():
            return True
        return self._indexing_task is not None and not self._indexing_task.done()

    def num_indexed_files(self) -> int:
        if not self._library or self.is_indexing():
            return 0
        return self._library.entry_count()

    def get_available_profiles(self) -> list[str]:
        return []

    def get_available_features(self) -> list[str]:
        return []
