# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from functools import partial, wraps
from typing import Optional

import carb
from omni.kit.async_engine import run_coroutine
from omni.kit.browser.folder.core import FileSystemFile, FileSystemFolder
from omni.kit.environment.core import ENVIRONMENT_PRIM_ROOT
from pxr import Usd


class EnvType:
    USD = "usd"
    HDR = "hdr"
    TEMPLATE = "template"


def get_env_type(url: str) -> EnvType:
    if url.lower().endswith(".hdr"):
        type = EnvType.HDR
    else:
        # Get type from usd contents
        try:
            source_stage = Usd.Stage.Open(url)
            # source_layer = Sdf.Layer.FindOrOpen(file.url)
            if source_stage and source_stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT):
                type = EnvType.TEMPLATE
            else:
                type = EnvType.USD

            source_stage = None
        except Exception as e:
            carb.log_warn(f"Failed to open {url}, set environment type to default.")
            type = EnvType.TEMPLATE

    return type


async def get_env_type_async(url: str) -> EnvType:
    if url.lower().endswith(".hdr"):
        type = EnvType.HDR
    else:

        def _run_asyncio(sync_fn, *args, **kwargs):
            async def async_fn():
                return sync_fn(*args, **kwargs)

            return run_coroutine(async_fn())

        def aio_open_stage(path):
            return _run_asyncio(Usd.Stage.Open, path)

        source_stage = await aio_open_stage(url)
        if source_stage and source_stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT):
            type = EnvType.TEMPLATE
        else:
            type = EnvType.USD
    return type


class EnvFile(FileSystemFile):
    """
    Represent a environment file object.
    Args:
        url (str): Url of environment file.
        type (EnvType): Env type. Default None means read from file contents.
    """

    def __init__(self, url: str, thumbnail: Optional[str] = None, type: Optional[EnvType] = None):
        super().__init__(url, thumbnail=thumbnail)
        # Load type form argument or set default type USD here to change it later in async mode in EnvFolder._on_file_found_async
        self.type = type or EnvType.USD

    def equals(self, other: "EnvFile") -> bool:
        if self.url != other.url:
            return False
        elif self.thumbnail != other.thumbnail:
            return False
        elif hasattr(self, "type") and hasattr(other, "type") and self.type != other.type:
            return False
        return True


class EnvFolder(FileSystemFolder):
    """
    Represent a environment folder.
    """

    async def _on_file_found_async(self, url: str) -> Optional[EnvFile]:
        file = await super()._on_file_found_async(url)
        if file:
            # Get environment type
            file.type = await get_env_type_async(url)
        return file

    def create_folder_object(self, *args, **kwargs) -> FileSystemFolder:
        """
        Overridden. Create folder object when a sub folder found
        """
        return EnvFolder(*args, **kwargs)

    def create_file_object(self, url: str) -> Optional[EnvFile]:
        """
        Overridden. Create file object.
        """
        file = EnvFile(url)
        return file
