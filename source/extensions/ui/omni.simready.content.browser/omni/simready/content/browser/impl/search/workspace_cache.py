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
from pathlib import Path
from typing import TYPE_CHECKING

import carb
import omni.client
import simready.search as lib

from . import SearchBackend
from .interface import AssetLibraryInterface, SearchResult

if TYPE_CHECKING:
    from .._url import Url


class AssetLibraryWorkspaceCache(AssetLibraryInterface):
    """Workspace cache from S3 (`add_s3_source`) or local library (`add_cache_source`).

    Args:
        wscache_location: URL of the workspace cache (S3, Nucleus, or local path).
        cache_root_url: Optional URL of the cache root.
    """

    WSCACHE_JSON_FILENAME = "workspace_cache.json"

    def __init__(
        self,
        wscache_location: Url,
        cache_root_url: str | None = None,
    ):
        self._library: lib.AssetLibrary | None = None
        self._wscache_location = wscache_location
        self._cache_root_url = cache_root_url
        self._available_profiles: list[str] = []
        self._available_features: list[str] = []

    @property
    def backend_type(self) -> SearchBackend:
        return SearchBackend.WORKSPACE_CACHE

    async def initialize(self):
        from .._url import UrlOrigin

        self._library = lib.AssetLibrary(raise_on_network_error=True)
        location_url = str(self._wscache_location)
        match self._wscache_location.origin:
            case UrlOrigin.LOCAL:
                project_config_path = Path(location_url).joinpath("project_config.toml").as_posix()
                carb.log_info(f"Initializing Workspace Cache from local project config: {project_config_path}")
                await self._library.add_cache_source(
                    project_config_path,
                    None,
                )
            case UrlOrigin.S3:
                carb.log_warn(f"Initializing Workspace Cache asset library: {location_url}")
                await self._library.add_s3_source(location_url, raise_on_network_error=True)
            case UrlOrigin.NUCLEUS:
                carb.log_info(f"Initializing Workspace Cache from Nucleus: {location_url}")

                def read_file_to_string(file_path: str) -> str | None:
                    _result, _, content = omni.client.read_file(file_path)
                    if _result == omni.client.Result.OK:
                        try:
                            return memoryview(content).tobytes().decode()
                        except UnicodeDecodeError:
                            carb.log_error("Could not decode file as text. Maybe improperly named binary file?")
                    else:
                        carb.log_error(f"Error ({_result}) reading file: {file_path}")
                    return None

                project_config_path = f"{location_url.strip('/')}/project_config.toml"
                await self._library.add_cache_source(
                    project_config_path,
                    file_reader=read_file_to_string,
                )
            case _:
                raise ValueError(f"Unsupported workspace cache location origin: {self._wscache_location.origin}")

    async def search(self, query: str, base_path: str | None = None) -> list[SearchResult]:
        results = []
        filters = self.parse_query_string_to_filters(query)
        if not self._library:
            carb.log_warn(f"[SimReady Search] workspace cache not initialized; dropping query {query!r}")
            return results
        base_path = [base_path] if base_path else None
        carb.log_info(
            f"[SimReady Search] workspace cache search: base_paths={base_path} "
            f"include_any={filters['include_any']} include_all={filters['include_all']}"
        )
        response = await asyncio.to_thread(
            self._library.search,
            **filters,
            remove_duplicates=True,
            base_paths=base_path,
        )
        for result in response:
            results.append(SearchResult(result.asset_path, result.relevance_score))
        carb.log_info(f"[SimReady Search] workspace cache returned {len(results)} result(s)")
        return results

    def get_available_features(self) -> list[str]:
        if not self._library:
            return []
        if self._available_features:
            return self._available_features
        all_features = self._library.get_all_values(lib.SearchFilterFeature())
        self._available_features = list(filter(len, sorted(f.strip() for f in all_features if f)))
        return self._available_features

    def get_available_profiles(self) -> list[str]:
        if not self._library:
            return []
        if self._available_profiles:
            return self._available_profiles
        all_profiles = self._library.get_all_values(lib.SearchFilterProfile())
        self._available_profiles = list(filter(len, sorted(p[0].strip() for p in all_profiles if p)))
        return self._available_profiles
