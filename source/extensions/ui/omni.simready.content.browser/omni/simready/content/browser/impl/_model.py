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
import time
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable

import carb
from omni.kit.search_core import AbstractSearchItem, AbstractSearchModel

from .search import AssetLibraryInterface, SearchResult


class SearchResultItem(AbstractSearchItem):
    def __init__(self, path: str, name: str, relevance: float = 1.0):
        self._path = path
        self._name = name
        self.relevance: float = relevance

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._name

    @property
    def path(self) -> str:  # type: ignore[override]
        return self._path

    @property
    def date(self) -> datetime:  # type: ignore[override]
        return datetime.now()

    @property
    def size(self) -> int:  # type: ignore[override]
        return 999


class AssetLibrarySearchModel(AbstractSearchModel):
    """Search model for assets using the AssetLibrary search package"""

    _asset_library: AssetLibraryInterface | None = None
    _search_path_anchor: str | None = None
    _search_complete_callback: Callable[[int, float], Awaitable[None]] | None = None
    _search_started_callback: Callable[[], Awaitable[None]] | None = None
    _search_error_callback: Callable[[Exception], None] | None = None
    _s3_bucket_base_url: str

    def __init__(self, search_text: str, current_dir: str, search_lifetime=None):
        super().__init__()
        self._items: list[SearchResultItem] = []
        # Reaching here proves the content browser routed the query to *our*
        # engine; if a Search click never logs this, it was lost upstream.
        carb.log_info(
            f"[SimReady Search] search model created: text={search_text!r} dir={current_dir!r} "
            f"library={type(self._asset_library).__name__ if self._asset_library else None}"
        )
        if search_text:
            asyncio.ensure_future(self._do_search(search_text, current_dir))
        else:
            carb.log_info("[SimReady Search] empty search text - no query dispatched")

    @classmethod
    def set_asset_library(cls, asset_library: AssetLibraryInterface | None):
        cls._asset_library = asset_library

    @classmethod
    def set_search_started_callback(cls, callback: Callable[[], Awaitable[None]]):
        cls._search_started_callback = callback

    @classmethod
    def set_search_complete_callback(cls, callback: Callable[[int, float], Awaitable[None]]):
        cls._search_complete_callback = callback

    @classmethod
    def set_search_error_callback(cls, callback: Callable[[Exception], None] | None):
        cls._search_error_callback = callback

    @classmethod
    def set_s3_bucket_base_url(cls, base_url: str):
        cls._s3_bucket_base_url = base_url

    @classmethod
    def set_search_path_anchor(cls, anchor: str):
        cls._search_path_anchor = anchor

    async def _do_search(self, query: str, _: str):
        """Perform actual search operation"""

        if not self._asset_library:
            carb.log_warn("Asset library and project root should be loaded at this point")
            return

        if self._search_started_callback:
            await self._search_started_callback()

        carb.log_info(
            f"[SimReady Search] querying {type(self._asset_library).__name__}: "
            f"query={query!r} anchor={self._search_path_anchor!r}"
        )
        start_time = time.perf_counter()
        try:
            results: list[SearchResult] = await self._asset_library.search(query, base_path=self._search_path_anchor)
        except Exception as e:
            if self._search_error_callback:
                self._search_error_callback(e)
            if self._search_complete_callback:
                await self._search_complete_callback(0, time.perf_counter() - start_time)
            return

        self._items = [
            SearchResultItem(
                path=result.asset_path,
                name=Path(result.asset_path).stem,
                relevance=result.relevance,
            )
            for result in results
        ]

        carb.log_info(f"[SimReady Search] {len(results)} result(s) in {time.perf_counter() - start_time:.2f}s")

        # Notify Content Browser that results are ready
        self._item_changed(None)
        if self._search_complete_callback:
            await self._search_complete_callback(len(results), time.perf_counter() - start_time)

    @property
    def items(self) -> list[SearchResultItem]:  # type: ignore[override]
        return self._items

    def destroy(self):
        self._items = []
        super().destroy()
