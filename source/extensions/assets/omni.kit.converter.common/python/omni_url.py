# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Union

import omni.client

__all__ = ["OmniUrl"]


class OmniUrl:
    """
    Omniverse Url Helper Class
    """

    def __init__(self, url: Union[str, Path], list_entry=None):
        """
        Returns url as a OmniUrl()
        """
        self._url = str(url)
        self._parts = omni.client.break_url(self._url)
        self._path = PurePosixPath(self._parts.path)
        self._list_entry: omni.client.ListEntry = list_entry

    def __str__(self):
        return self._url

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: url={self._url}>"

    def __eq__(self, other: object) -> bool:
        return self._url == str(other)

    @property
    def scheme(self):
        return self._parts.scheme

    def get_local_file(self) -> Path:
        """
        Returns: Path() object for local file
        """
        if self.scheme == "file":  # If scheme is file, then just return the path component as Path
            # workaround to remove leading slash on Windows
            path = self._parts.path
            if os.name == "nt" and path.startswith("/"):
                path = path[1:]

            return Path(path)
        res, path = omni.client.get_local_file(self._url, download=True)
        if res != omni.client.Result.OK:
            raise BaseException(f"Could not get local file: {self._url}. Reason: {res}")
        return Path(path)

    async def get_local_file_async(self) -> tuple[omni.client.Result, Path]:
        """
        Returns: Path() object for local file
        """
        if self.scheme == "file":  # If scheme is file, then just return the path component as Path
            # workaround to remove leading slash on Windows
            path = self._parts.path
            if os.name == "nt" and path.startswith("/"):
                path = path[1:]
            return Path(path)
        res, path = await omni.client.get_local_file_async(self._url, download=True)

        return res, Path(path)

    def sync_stat(self):
        """
        Returns the status of the url
        """
        result, stat = omni.client.stat(self._url)
        if result == omni.client.Result.OK:
            self._list_entry = stat

    @property
    def stat(self):
        """
        Status of the url
        """
        if not self._list_entry:
            self.sync_stat()
        return self._list_entry

    @property
    def exists(self):
        """
        Returns: True if exists; else False
        """
        if self.stat:
            return True
        return False

    @property
    def writeable(self):
        """
        Checks if the url path is writeable
        """
        stat = self.stat

        if not stat:
            return False

        if not stat.access & omni.client.AccessFlags.WRITE:
            # No access
            return False

        if stat.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
            # This is a folder
            return False

        if stat.flags & omni.client.ItemFlags.IS_INSIDE_MOUNT:
            # Inside a mounted folder
            return False

        return stat.flags & omni.client.ItemFlags.WRITEABLE_FILE

    @property
    def path(self):
        """
        Returns the path
        """
        return self._path

    @property
    def parent_url(self) -> OmniUrl:
        """
        Returns: OmniUrl object
        """
        return OmniUrl(
            omni.client.make_url(
                scheme=self._parts.scheme,
                host=self._parts.host,
                path=str(self._path.parent),
            )
        )

    @property
    def name(self) -> str:
        """The final path component, if any."""
        return self._path.name

    @property
    def stem(self) -> str:
        """The final path component, minus its suffix(s)."""
        return self._path.stem

    @property
    def suffix(self) -> str:
        """
        The final component's last suffix, if any.

        This includes the leading period. For example: '.txt'
        """
        return self._path.suffix

    @property
    def full_suffix(self) -> str:
        """Return path suffix(s) if any.

        This includes the leading period. For example: '.skelanim.usd'
        """
        return "".join(self._path.suffixes)

    def url_with_path(self, path: Path) -> OmniUrl:
        """Return a new url with the path changed."""
        return OmniUrl(
            omni.client.make_url(
                scheme=self._parts.scheme,
                host=self._parts.host,
                path=str(path.as_posix()),
            )
        )

    def url_with_name(self, name: str) -> OmniUrl:
        """Return a new url with the url path final component changed."""

        return OmniUrl(
            omni.client.make_url(
                scheme=self._parts.scheme,
                host=self._parts.host,
                path=str(self._path.with_name(name)),
            )
        )

    def url_with_suffix(self, suffix: str) -> OmniUrl:
        """Return a url with the file full suffix changed.  If the url path
        has no suffix, add given suffix.  If the given suffix is an empty
        string, remove the suffix from the url path.
        """
        new_name = self.stem + suffix
        return OmniUrl(
            omni.client.make_url(
                scheme=self._parts.scheme,
                host=self._parts.host,
                path=str(self._path.with_name(new_name)),
            )
        )

    def __truediv__(self, arg):
        new_path = self.path / PurePosixPath(arg)
        return self.url_with_path(new_path)
