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

from functools import lru_cache

import carb.settings

from ._url import Url, UrlOrigin, ensure_trailing_slash


def _sanitize_url_list(raw: list[str]) -> list[str]:
    """Strip, ensure trailing slash, and drop empties from a settings list.

    Duplicates are preserved in their original order so that index-based access
    into ``_wscache_root_urls`` remains stable (``[0]`` is the S3 entry,
    ``[1]`` is the Nucleus entry, per extension.toml convention).
    """
    sanitized: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        sanitized.append(ensure_trailing_slash(entry))
    return sanitized


class ExtensionConfig:
    def __init__(
        self,
        wscache_root_urls: list[str],
        default_wscache_root_url_index: int,
        usd_search_endpoint: str,
        file_index_locations: list[str],
        usd_search_index_mapping: dict[str, str],
        usd_search_tree_root_subpath: str = "",
    ):
        # Normalize once at the boundary: user-supplied settings may omit
        # trailing slashes or contain stray whitespace. Sanitizing here means
        # every accessor below can trust the stored values are directory-style.
        self._wscache_root_urls = _sanitize_url_list(wscache_root_urls)
        # Clamp the default index into the valid range so an out-of-range
        # setting doesn't crash the extension.
        if self._wscache_root_urls:
            self._default_wscache_root_url_index = max(
                0, min(default_wscache_root_url_index, len(self._wscache_root_urls) - 1)
            )
        else:
            self._default_wscache_root_url_index = 0
        self._usd_search_endpoint = (usd_search_endpoint or "").strip()
        self._file_index_locations = _sanitize_url_list(file_index_locations)
        self._usd_search_index_mapping = usd_search_index_mapping
        # Bucket-relative, so the same value applies to whichever index bucket
        # the active endpoint maps to. Leading/trailing slashes are stripped so
        # joining onto the index URL can't produce a double slash.
        self._usd_search_tree_root_subpath = (usd_search_tree_root_subpath or "").strip().strip("/")

    @property
    def default_wscache_root_urls(self) -> list[Url]:
        """All configured workspace-cache roots as parsed ``Url`` values.

        Entries that fail origin detection (e.g. an unsupported scheme) are
        silently dropped so callers never need to handle ``None``.
        """
        urls: list[Url] = []
        for raw in self._wscache_root_urls:
            parsed = Url.parse_from_str(raw)
            if parsed is not None:
                urls.append(parsed)
        return urls

    @property
    def default_wscache_s3_url(self) -> Url | None:
        """The preferred (S3) workspace-cache root, or ``None`` if not configured."""
        if not self._wscache_root_urls:
            return None
        raw = self._wscache_root_urls[self._default_wscache_root_url_index]
        return Url(url=raw, origin=UrlOrigin.S3)

    @property
    def default_usd_search_index_url(self) -> Url | None:
        """S3 index URL mapped to the active USD Search endpoint."""
        endpoint = self._usd_search_endpoint.rstrip("/")
        if not endpoint:
            return None
        for mapped_endpoint, index_url in self._usd_search_index_mapping.items():
            if str(mapped_endpoint).rstrip("/") == endpoint:
                return Url.parse_from_str(ensure_trailing_slash(str(index_url)))
        return None

    @property
    def default_usd_search_tree_root_url(self) -> Url | None:
        """Folder that anchors the tree when the USD Search mode is active.

        The index URL is a bucket root, which would expose the whole bucket in
        the tree. ``usd_search_tree_root_subpath`` narrows it to the asset
        folder (mirroring how the workspace-cache roots point straight at
        "SimReady"). Falls back to the index URL when no subpath is configured.
        """
        index_url = self.default_usd_search_index_url
        if index_url is None:
            return None
        if not self._usd_search_tree_root_subpath:
            return index_url
        return index_url.join(ensure_trailing_slash(self._usd_search_tree_root_subpath))

    @property
    def default_wscache_nucleus_url(self) -> Url | None:
        """The Nucleus workspace-cache root, by convention the second entry."""
        try:
            nucleus_url = self._wscache_root_urls[1]
        except IndexError:
            return None
        # Validate the scheme before trusting the origin — a misconfigured
        # entry (e.g. a second S3 URL) should not be reported as Nucleus.
        if not nucleus_url.lower().startswith("omniverse://"):
            return None
        return Url(url=nucleus_url, origin=UrlOrigin.NUCLEUS)

    @property
    def default_file_index_locations(self) -> list[Url]:
        """File-index locations parsed into ``Url`` values with correct origins.

        Origins are detected from each entry rather than hardcoded, because a
        user can legitimately configure either S3 or local directories here.
        """
        urls: list[Url] = []
        for raw in self._file_index_locations:
            parsed = Url.parse_from_str(raw)
            if parsed is not None:
                urls.append(parsed)
        return urls

    @property
    def default_usd_search_endpoint(self) -> str:
        return self._usd_search_endpoint

    @property
    def default_usd_search_index_mapping(self) -> dict[str, str]:
        return self._usd_search_index_mapping

    @staticmethod
    def from_settings() -> ExtensionConfig:
        from .extension import (
            DEFAULT_WSCACHE_ROOT_URL_INDEX_SETTING,
            FILE_INDEX_LOCATIONS_SETTING,
            USD_SEARCH_ENDPOINT_SETTING,
            USD_SEARCH_TREE_ROOT_SUBPATH_SETTING,
            WSCACHE_ROOT_URLS_SETTING,
        )

        settings = carb.settings.get_settings()
        # TODO: use constants for the settings
        pairs = settings.get("/exts/omni.simready.content.browser/usd_search_index_mapping")
        usd_search_index_mapping = {pair[0]: pair[1] for pair in pairs}
        wscache_root_urls = list(settings.get(WSCACHE_ROOT_URLS_SETTING) or [])
        try:
            default_index = int(settings.get(DEFAULT_WSCACHE_ROOT_URL_INDEX_SETTING) or 0)
        except (TypeError, ValueError):
            default_index = 0
        file_index_locations = list(settings.get(FILE_INDEX_LOCATIONS_SETTING) or [])
        usd_search_endpoint = settings.get(USD_SEARCH_ENDPOINT_SETTING) or ""
        usd_search_tree_root_subpath = settings.get(USD_SEARCH_TREE_ROOT_SUBPATH_SETTING) or ""

        return ExtensionConfig(
            wscache_root_urls=wscache_root_urls,
            default_wscache_root_url_index=default_index,
            usd_search_endpoint=usd_search_endpoint,
            file_index_locations=file_index_locations,
            usd_search_index_mapping=usd_search_index_mapping,
            usd_search_tree_root_subpath=usd_search_tree_root_subpath,
        )


@lru_cache(maxsize=1)
def get_extension_config() -> ExtensionConfig:
    return ExtensionConfig.from_settings()
