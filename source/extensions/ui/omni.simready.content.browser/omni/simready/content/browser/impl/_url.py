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

import urllib.parse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .search import SearchBackend


class UrlOrigin(Enum):
    S3 = "s3"
    LOCAL = "local"
    NUCLEUS = "nucleus"


def ensure_trailing_slash(raw: str) -> str:
    """Strip whitespace from *raw* and append ``"/"`` if missing.

    Returns ``None`` when the stripped input is empty. Intended for
    directory-style URLs loaded from user-configurable settings so downstream
    ``startswith`` prefix checks are well-defined.
    """
    if raw := raw.strip():
        return raw if raw.endswith("/") else raw + "/"
    return ""


@dataclass(frozen=True, eq=False)
class Url:
    url: str
    origin: UrlOrigin

    def is_subpath_of(self, other: Url) -> bool:
        if self.origin != other.origin:
            return False
        return self.url.startswith(other.url)

    def __fspath__(self) -> str:
        return self.url

    def __str__(self) -> str:
        return self.url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Url):
            return False
        return self.url.rstrip("/") == other.url.rstrip("/") and self.origin == other.origin

    def __hash__(self) -> int:
        return hash((self.url.rstrip("/"), self.origin))

    def join(self, path: str) -> Url:
        return Url(url=ensure_trailing_slash(str(self.url)) + path, origin=self.origin)

    @staticmethod
    def parse_from_str(url: str) -> Url | None:
        if not url or not (url := url.strip()):
            return None

        # Nucleus: omniverse:// scheme
        if url.lower().startswith("omniverse://"):
            return Url(url=url, origin=UrlOrigin.NUCLEUS)

        # S3: https:// pointing to an AWS S3 bucket
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme in ("https", "http"):
            host = parsed.netloc.lower()
            if ".s3" in host or ".amazonaws.com" in host:
                return Url(url=url, origin=UrlOrigin.S3)
            return None

        if parsed.scheme in (None, "file", "") or parsed.netloc in (None, ""):
            return Url(url=url, origin=UrlOrigin.LOCAL)

        return None


async def get_available_backends_for_url(url: Url) -> list[SearchBackend]:
    from ._config import get_extension_config

    config = get_extension_config()

    available: list[SearchBackend] = []

    match url.origin:
        case UrlOrigin.S3 | UrlOrigin.NUCLEUS:
            if url.origin == UrlOrigin.S3:
                available.append(SearchBackend.USD_SEARCH)
            for wscache_root_url in config.default_wscache_root_urls:
                # Direct match with supported WS roots
                if url == wscache_root_url:
                    available.append(SearchBackend.WORKSPACE_CACHE)
                    break
                # Assume any S3 path ending in "SimReady" is a workspace cache
                if str(url).rstrip("/").endswith("SimReady"):
                    available.append(SearchBackend.WORKSPACE_CACHE)
                    break
            for index_location in config.default_file_index_locations:
                if url.is_subpath_of(index_location):
                    available.append(SearchBackend.FILE_INDEX)
                    break
        case UrlOrigin.LOCAL:
            available.append(SearchBackend.FILE_INDEX)
            workspace_json = Path(url).joinpath("workspace_cache.json")
            if workspace_json.is_file():
                available.append(SearchBackend.WORKSPACE_CACHE)

    return sorted(available)
