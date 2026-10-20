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
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import carb
from omni.kit.async_engine import run_coroutine

from ._url import Url, UrlOrigin
from .search import (
    AssetLibraryFileIndex,
    AssetLibraryInterface,
    AssetLibraryUsdSearch,
    AssetLibraryWorkspaceCache,
    SearchBackend,
)

LibraryKey = tuple[SearchBackend, Url | None]


class AssetLibraryLoaderError(Exception):
    pass


class AssetLibraryInvalidProjectRootUrl(AssetLibraryLoaderError):
    pass


@dataclass
class LibraryConfig:
    backend: SearchBackend = SearchBackend.USD_SEARCH
    workspace_cache_location: Url | None = None
    usd_search_endpoint: str = ""
    index_locations: list[str] = field(default_factory=list)
    selected_url: Url | None = None


class AssetLibraryLoader:
    """Orchestrates backend loading, caching, and file indexing."""

    def __init__(self):
        self._interfaces: dict[LibraryKey, AssetLibraryInterface] = {}

    def _key(self, backend: SearchBackend, url: Url | None = None) -> LibraryKey:
        return (backend, url)

    def get_interface(self, backend: SearchBackend, url: Url | None = None) -> AssetLibraryInterface | None:
        return self._interfaces.get(self._key(backend, url))

    def is_library_loaded(self, backend: SearchBackend, url: Url | None = None) -> bool:
        return self._key(backend, url) in self._interfaces

    def unload_library(self, backend: SearchBackend, url: Url | None = None):
        """Remove a cached backend interface so it is re-initialized on next activation."""
        self._interfaces.pop(self._key(backend, url), None)

    def _resolve_file_index_interface(self, url: Url | None) -> AssetLibraryFileIndex | None:
        # Prefer exact URL-keyed library, then global FILE_INDEX entry, then any FILE_INDEX interface.
        if interface := self.get_interface(SearchBackend.FILE_INDEX, url):
            if isinstance(interface, AssetLibraryFileIndex):
                return interface

        if interface := self.get_interface(SearchBackend.FILE_INDEX, None):
            if isinstance(interface, AssetLibraryFileIndex):
                return interface

        for (backend, _), interface in self._interfaces.items():
            if backend == SearchBackend.FILE_INDEX and isinstance(interface, AssetLibraryFileIndex):
                return interface
        return None

    async def load(
        self, config: LibraryConfig, load_completed_callback: Callable[[AssetLibraryInterface | None], Awaitable[None]]
    ):
        """Initialize the requested backend and invoke *load_completed_callback* when ready."""
        key = self._key(config.backend, config.selected_url)

        if key in self._interfaces:
            run_coroutine(load_completed_callback(self._interfaces[key]))
            return

        match config.backend:
            case SearchBackend.WORKSPACE_CACHE:
                load_func = self.load_workspace_cache
            case SearchBackend.USD_SEARCH:
                load_func = self.load_usd_search
            case SearchBackend.FILE_INDEX:
                load_func = self.load_file_index

        carb.log_info(f"Loading Search Library Backend: {config.backend} for url: {config.selected_url}")
        self._interfaces[key] = await load_func(config)
        run_coroutine(load_completed_callback(self._interfaces[key]))

    async def load_file_index(self, config: LibraryConfig) -> AssetLibraryInterface:
        carb.log_info(f"Loading Asset Search Library from File Index: {config.index_locations}")
        loaded = AssetLibraryFileIndex()
        await loaded.initialize()
        return loaded

    async def load_usd_search(self, config: LibraryConfig) -> AssetLibraryInterface:
        carb.log_info(f"Loading Asset Search Library from USD Search: {config.usd_search_endpoint}")
        loaded = AssetLibraryUsdSearch(config.usd_search_endpoint)
        await loaded.initialize()
        return loaded

    async def load_workspace_cache(self, config: LibraryConfig) -> AssetLibraryInterface:
        if not config.workspace_cache_location:
            raise AssetLibraryLoaderError("Workspace cache location was not provided")
        carb.log_info(f"Loading Asset Search Library from: {config.workspace_cache_location}")
        try:
            library = AssetLibraryWorkspaceCache(wscache_location=config.workspace_cache_location)
            await library.initialize()
            return library
        except Exception as e:
            carb.log_error(f"Failed to load AssetLibrary: {e}")
            raise AssetLibraryLoaderError(e) from e

    def start_indexing(
        self,
        urls_to_index: list[Url],
        url: Url | None = None,
        on_done: Callable[[], int] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> Awaitable[None]:
        file_index_library = self._resolve_file_index_interface(url)
        if not file_index_library:
            return run_coroutine(asyncio.sleep(0))

        # Local POSIX paths have no URL scheme; everything else is treated as S3.
        directory_type = "local" if urls_to_index and urls_to_index[0].origin == UrlOrigin.LOCAL else "s3"

        def _on_future_done(fut):
            try:
                exc = fut.exception()
            except asyncio.CancelledError:
                return
            if exc:
                carb.log_error(f"Indexing failed: {exc}")
                if on_error:
                    on_error(exc)
            else:
                carb.log_info("Indexing complete")
                if on_done:
                    on_done(file_index_library.num_indexed_files())

        future = file_index_library.index_locations([str(url) for url in urls_to_index], directory_type)
        if future:
            future.add_done_callback(_on_future_done)
            return future
        else:
            if on_done:
                on_done(file_index_library.num_indexed_files())
            return run_coroutine(asyncio.sleep(0))

    def get_asset_profiles(self, backend: SearchBackend, url: Url | None = None) -> list[str]:
        if interface := self.get_interface(backend, url):
            return interface.get_available_profiles()
        return []

    def get_asset_features(self, backend: SearchBackend, url: Url | None = None) -> list[str]:
        if interface := self.get_interface(backend, url):
            return interface.get_available_features()
        return []
