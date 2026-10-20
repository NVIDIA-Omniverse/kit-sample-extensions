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

import abc
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING

import carb
import simready.search as lib

if TYPE_CHECKING:
    from . import SearchBackend


@dataclass
class SearchResult:
    asset_path: str
    relevance: float = 1.0


class AssetLibraryInterface(abc.ABC):
    @property
    @abc.abstractmethod
    def backend_type(self) -> SearchBackend:
        pass

    @abc.abstractmethod
    async def search(self, query: str, base_path: str | None = None) -> list[SearchResult]:
        pass

    @abc.abstractmethod
    async def initialize(self):
        pass

    @abc.abstractmethod
    def get_available_profiles(self) -> list[str]:
        pass

    @abc.abstractmethod
    def get_available_features(self) -> list[str]:
        pass

    @staticmethod
    def parse_query_string_to_filters(query: str) -> dict[str, list[lib.AssetLibrarySearchFilter]]:
        """Parse the search query string into a list of `AssetLibrarySearchFilter`"""
        # `SearchParams.to_query_string` quotes the whole query so the Kit search
        # field forwards it as one opaque term. Queries typed straight into that
        # field arrive unquoted, so only unwrap when the quotes are actually there.
        query = query.strip()
        if len(query) > 1 and query.startswith('"') and query.endswith('"'):
            query = query[1:-1]

        _all_filters: dict[str, list] = {"include_any": [], "include_all": []}

        def _parse_single_filter_str(_filter_str: str) -> lib.AssetLibrarySearchFilter | None:
            *klass, parameter = _filter_str.strip().split(":", 1)
            parameter = urllib.parse.unquote(parameter.lower())
            if klass and (klass := klass[0].strip()):
                match klass.lower():
                    case "feature":
                        return lib.SearchFilterFeature(parameter)
                    case "name":
                        return lib.SearchFilterPathContains(parameter)
                    case "tag":
                        return lib.SearchFilterTag(parameter)
                    case "profile":
                        return lib.SearchFilterProfile(parameter)
                    case "phrase":
                        return lib.SearchFilterPhrase(parameter)
                    case "relevance":
                        return lib.SearchFilterRelevance(minimum=float(parameter))
                    case _other:
                        carb.log_warn(f'Unsupported asset search filter type: "{_other}". Skipping')
                        return None
            elif parameter:
                return lib.SearchFilterPathContains(parameter)
            else:
                carb.log_warn(f'Invalid asset search query: "{_filter_str}". Skipping')
                return None

        for filter_str in query.split(" "):
            if "+" in filter_str:
                for _part in filter_str.split("+"):
                    if _filter := _parse_single_filter_str(_part.strip()):
                        _all_filters["include_all"].append(_filter)
            else:
                if _filter := _parse_single_filter_str(filter_str):
                    _all_filters["include_any"].append(_filter)

        return _all_filters
