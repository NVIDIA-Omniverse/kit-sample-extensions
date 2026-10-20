# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["ThumbnailManager"]

import asyncio
import secrets
import string
import time
from typing import Optional

import carb
import carb.settings
import omni.client
import omni.usd
from omni.kit.widget.viewport import ViewportWidget

from .constants import DEFAULT_TIMEOUT, SETTING_TIMEOUT
from .viewport_thumbnail_generator import ViewportThumbnailGenerator


class ThumbnailManager:
    """
    Manager to generate thumbnails one by one.
    Keyword args:
        max_retry_count: Max retry count to generating a thumbnail if timeout. Default 3.
    """

    def __init__(self, max_retry_count: int = 3):
        self._max_retry_count = max_retry_count
        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()
        self._active_thumbnail_generator: Optional[ViewportThumbnailGenerator] = None
        self._timeout = None
        self._usd_context_name = ""
        self._viewport = None

        self._run_task = asyncio.ensure_future(self._run())

    def destroy(self):
        """Stops the thumbnail manager and cleans up resources."""
        self._stop_event.set()
        self._work_queue.put_nowait((None, None, None))
        # asyncio.wait_for(self._run_task)
        self._run_task.cancel()

        if self._usd_context_name:
            self._viewport.destroy()
            self._viewport = None

            omni.usd.destroy_context(self._usd_context_name)
            self._usd_context_name = ""

    def put(self, thumbnail_generator: ViewportThumbnailGenerator, timeout: int = None, retry: int = 0):
        """Add a new thumbnail generation request.

        Args:
            thumbnail_generator (ViewportThumbnailGenerator): A request for thumbnail generation.
            timeout (int): Timeout in seconds to generate the thumbnail. If ``None``, reads
                from the extension setting ``/exts/omni.kit.thumbnails.mdl/timeout``
                (default 120s). The default is generous to accommodate first-time MDL
                material compilation which can be significantly slower than cached materials.
                A value of ``0`` (or any non-positive value) is treated as
                "disable timeout" - generation runs until completion. Only ``None``
                falls back to the default; an explicit ``0`` is preserved so that users
                who configure ``/exts/omni.kit.thumbnails.mdl/timeout = 0`` actually get
                the disabled behavior rather than silently reverting to ``DEFAULT_TIMEOUT``.
            retry (int): Current retry count for generating the thumbnail. Default 0.
        """
        if timeout is None:
            # Only fall back to DEFAULT_TIMEOUT when the setting is truly unset
            # (returns None from carb). Do NOT use ``or`` - that would clobber a
            # legitimate user value of 0 which means "disable timeout".
            settings = carb.settings.get_settings()
            timeout = settings.get(SETTING_TIMEOUT)
            if timeout is None:
                timeout = DEFAULT_TIMEOUT
        self._work_queue.put_nowait((thumbnail_generator, timeout, retry))

    async def _run(self):
        while not self._stop_event.is_set():
            if self._active_thumbnail_generator is None:
                self._active_thumbnail_generator, self._timeout, self._retry = await self._work_queue.get()
                if self._active_thumbnail_generator is None:
                    break
                self._ensure_context()  # defer context creation until we actually need one
                self._generation_start_time = time.time()
                self._active_thumbnail_generator.generate(self._usd_context_name, self._viewport.viewport_api)
            else:
                # A non-positive timeout means "disable timeout" - generation runs
                # until completion. This lets users opt out entirely by configuring
                # ``/exts/omni.kit.thumbnails.mdl/timeout = 0``.
                timeout_enabled = self._timeout is not None and self._timeout > 0
                if timeout_enabled and time.time() - self._generation_start_time > self._timeout:
                    carb.log_warn(f"[Thumbnail] Timeout when creating {self._active_thumbnail_generator.output_url}")
                    self._active_thumbnail_generator.stop()
                    self._retry += 1
                    if self._retry < self._max_retry_count:
                        # Sometimes timeout due to AssetLoaded event not triggered after creating and binding material
                        # Recreating and binding do help. So we retry here.
                        await self._work_queue.put((self._active_thumbnail_generator, self._timeout, self._retry))
                    self._active_thumbnail_generator = None
                else:
                    result, _ = await omni.client.stat_async(self._active_thumbnail_generator.output_url)
                    # Sometimes file deleted from remote but here still get OK - maybe due to the cache
                    # We need to make sure generation is done here.
                    if result == omni.client.Result.OK and self._active_thumbnail_generator.done:
                        self._active_thumbnail_generator.stop()
                        self._active_thumbnail_generator = None

    def _ensure_context(self):
        if not self._usd_context_name:
            self._usd_context_name = "Thumbnail_" + "".join(secrets.choice(string.ascii_uppercase) for i in range(5))
            ctx = omni.usd.create_context(self._usd_context_name)
            ctx.new_stage()
            self._viewport = ViewportWidget(
                usd_context_name=self._usd_context_name,
                resolution=(256, 256),
                hd_engine="rtx",
            )
