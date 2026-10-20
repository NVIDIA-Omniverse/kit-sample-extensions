# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import inspect
import os
import re
import tarfile
import urllib.parse
import zipfile
from pathlib import Path
from typing import List, Optional

import omni.client
import pydantic

SUPPORTED_ARCHIVE_FORMATS = {".zip", ".tar", ".tar.gz"}


def create_dynamic_model(name: str, cls) -> pydantic.BaseModel:

    members = inspect.getmembers(cls, lambda member: not (inspect.isroutine(member)))

    model_args = {}
    for key, value in dict(members).items():
        if key.startswith("_"):
            continue

        value = "" if value is None else value

        model_args[key] = (type(value), value)

    model = pydantic.create_model(name, **model_args)
    return model


def get_archive_file_format(archive_path: str) -> str:
    """Returns the full extension of a given archive path."""
    path = Path(archive_path)
    return "".join(path.suffixes)


def is_archive_supported(archive_ext: str) -> bool:
    """Checks if the archive extension is supported."""
    return archive_ext in SUPPORTED_ARCHIVE_FORMATS


def _extract_tar_file(archive_path: str, mode: str) -> bool:
    """Check compression ratio to prevent zip bomb attacks OMPE-22821"""
    THRESHOLD_ENTRIES = 10000
    THRESHOLD_SIZE = 1000000000
    THRESHOLD_RATIO = 10

    totalSizeArchive = 0
    totalEntryArchive = 0

    tfile = tarfile.open(archive_path, mode=mode)
    success = True
    for entry in tfile:
        tarinfo = tfile.extractfile(entry)

        totalEntryArchive += 1
        sizeEntry = 0
        result = b""
        while True:
            sizeEntry += 1024
            totalSizeArchive += 1024

            ratio = sizeEntry / entry.size
            if ratio > THRESHOLD_RATIO:
                # ratio between compressed and uncompressed data is highly suspicious, looks like a Zip Bomb Attack
                success = False
                break

            chunk = tarinfo.read(1024)
            if not chunk:
                break

            result += chunk

        if totalEntryArchive > THRESHOLD_ENTRIES:
            # too much entries in this archive, can lead to inodes exhaustion of the system
            success = False
            break

        if totalSizeArchive > THRESHOLD_SIZE:
            # the uncompressed data size is too much for the application resource capacity
            success = False
            break

    tfile.close()
    return success


def unpack_archive(archive_path: str) -> bool:
    """Unpacks the archive if it's a supported format."""
    ext = get_archive_file_format(archive_path)

    if not is_archive_supported(ext):
        return False

    parent_folder = Path(archive_path).parent

    try:
        if ext == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(parent_folder.as_posix())
        elif ext == ".tar.gz":
            return _extract_tar_file(archive_path, mode="r:gz")
        elif ext == ".tar":
            return _extract_tar_file(archive_path, mode="r")

        return True

    except Exception as e:
        return False
