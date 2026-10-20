# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import time
from typing import Optional

import carb
import omni.client

from .viewport_thumbnail_generator import ViewportThumbnailGenerator


class ThumbnailManager:
    """
    Manager to generate thumbnails one by one.
    """

    def __init__(self):
        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()
        self._active_thumbnail_generator: Optional[ViewportThumbnailGenerator] = None
        self._timeout = None

        self._future = asyncio.ensure_future(self._run())

    # we need to make this function async, otherwise we can't wait for the background task to finish
    # in an async caller without running into nested event loop issues
    async def destroy(self):
        self._stop_event.set()
        self._work_queue.put_nowait((None, None))
        # wait until background task finished
        self._future.cancel()

    def put(self, thumbnail_generator: ViewportThumbnailGenerator, timeout: int = 10):
        """
        Add a new thumbnail generation request.
        Args:
            thumnail_generator (ViewportThumbnailGenerator): A request on thumbnail generation
            timeout (int): Timeout to generate the thumbnail, in seconds. Default 20.
        """
        self._work_queue.put_nowait((thumbnail_generator, timeout))

    async def _run(self):
        while not self._stop_event.is_set():
            if self._active_thumbnail_generator is None:
                self._active_thumbnail_generator, self._timeout = await self._work_queue.get()
                if self._active_thumbnail_generator is None:
                    break
                self._generation_start_time = time.time()
                self._active_thumbnail_generator.generate()
            else:
                if time.time() - self._generation_start_time > self._timeout:
                    carb.log_warn(f"[Thumbnail] Timeout when creating {self._active_thumbnail_generator.output_url}")
                    self._active_thumbnail_generator.stop()
                    self._active_thumbnail_generator = None
                else:
                    result, entries = await omni.client.stat_async(self._active_thumbnail_generator.output_url)
                    if result == omni.client.Result.OK:
                        self._active_thumbnail_generator.stop()
                        self._active_thumbnail_generator = None

        if self._active_thumbnail_generator is not None:
            self._active_thumbnail_generator.stop()
            self._active_thumbnail_generator = None
