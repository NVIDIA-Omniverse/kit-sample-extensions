# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["OmniUriResolver"]

import omni.client


class OmniUriResolver:
    """A :py:class:`~omni.asset_validator.UriResolver` backed by ``omni.client``."""

    @staticmethod
    def _ensure_container(uri: str) -> str:
        """Return *uri* with a trailing slash so ``combine_urls`` treats it as a container, not a file."""
        return uri.rstrip("/") + "/"

    def is_uri_found(self, uri: str) -> bool:
        status, _ = omni.client.stat(uri)
        return status == omni.client.Result.OK

    def is_uri_prefix(self, uri: str) -> bool:
        status, entry = omni.client.stat(uri)
        if status != omni.client.Result.OK:
            return False
        return bool(entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN)

    def list_uris(self, uri: str) -> list[str]:
        status, entries = omni.client.list(uri)
        if status != omni.client.Result.OK:
            return []
        return [omni.client.combine_urls(self._ensure_container(uri), entry.relative_path) for entry in entries]

    def parent_uri(self, uri: str) -> str:
        b_url = omni.client.break_url(uri)
        parent_path = b_url.path.rsplit("/", 1)[0] or b_url.path
        return omni.client.make_url(
            b_url.scheme, b_url.user, b_url.host, b_url.port, parent_path, b_url.query, b_url.fragment
        )

    def join_uri(self, base_uri: str, child: str) -> str:
        return omni.client.combine_urls(self._ensure_container(base_uri), child)

    def basename(self, uri: str) -> str:
        return omni.client.break_url(uri).path.rstrip("/").rsplit("/", 1)[-1]

    def relative_uri(self, base_uri: str, child_uri: str) -> str:
        return omni.client.make_relative_url(self._ensure_container(base_uri), child_uri)
