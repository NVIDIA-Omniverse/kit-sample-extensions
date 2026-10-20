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
import hashlib
from typing import Dict, Optional

import carb
import omni.client


class DownloadState:
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class PredownloadHelper:
    """
    Pre-download remote folders to local.
    Args:
        save_folder: Folder to save download items in.
    """

    def __init__(self, save_folder: str):
        self._save_folder = save_folder

        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()
        self._download_folders: Dict[str, DownloadState] = {}
        self._run_future = None

    def destroy(self) -> None:
        self._stop_event.set()
        self._work_queue.put_nowait((None, None))
        self._run_future = None

    def append_folder(self, folder: str, save_folder: Optional[str] = None) -> bool:
        """
        Append a remote folder to download.
        Return False if already appended, otherwise True.
        Args:
            folder: Url of folder to download.
            save_folder: Url of folder to save. If None, use name from hash of remote folder.
        """
        if folder in self._download_folders:
            return False  # pragma: no cover
        if save_folder is None:
            hash_object = hashlib.sha256(folder.encode("utf-8"))
            save_folder = self._save_folder + "/" + hash_object.hexdigest()
        self._work_queue.put_nowait((folder, save_folder))
        self._download_folders[folder] = DownloadState.PENDING
        if not self._run_future:
            self._run_future = asyncio.ensure_future(self._run())
        return True

    def get_download_state(self, folder: str) -> Optional[DownloadState]:
        """
        Get folder download state.
        Return None if never downloaded.
        """
        if folder in self._download_folders:
            return self._download_folders[folder]
        else:
            return None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                remote_folder, save_folder = await self._work_queue.get()
                if remote_folder is None:
                    break
            except TypeError:  # pragma: no cover
                break
            await self._predownload(remote_folder, save_folder)

    async def _predownload(self, remote_folder: str, save_folder: str) -> None:
        self._download_folders[remote_folder] = DownloadState.IN_PROGRESS
        download_folder = remote_folder if remote_folder.endswith("/") else remote_folder + "/"
        if not save_folder.endswith("/"):
            save_folder += "/"

        carb.log_info(f"Preload folder: {download_folder}")
        await omni.client.copy_async(download_folder, save_folder, behavior=omni.client.CopyBehavior.OVERWRITE)
        carb.log_info(f"loaded {download_folder}")
        self._download_folders[remote_folder] = DownloadState.DONE
