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
from typing import Callable, Optional

import carb
from omni.kit.widget.material_preview import MaterialPreviewProducer
from pxr import Sdf

from ..models import MaterialPrimDetailItem


class CaptureThumbnailRequest:
    """
    Request to capture material thumbnail.
    Args:
        item (MaterialPrimDetailItem): Material item to capture thumbnail.
        on_captured_fn (Callable): Function called when thumnail captured. Function signure:
            void on_captured_fn(item: MaterialPrimDetailItem, raw_data)
    """

    def __init__(self, item: MaterialPrimDetailItem, on_captured_fn: Callable):
        self.item = item
        self.on_captured_fn = on_captured_fn
        self.done = False


class CaptureThumbnailGenerator:
    """
    Thumbnail generator by capturing.
    """

    def __init__(self):
        self._material_preview_producer = None
        self._generate_thumbnail_future = None

    def destroy(self) -> None:
        if self._material_preview_producer is not None:
            self._material_preview_producer.destroy()

    async def capture_async(self, request: CaptureThumbnailRequest) -> None:
        """
        Capture material thumbnail in async.
        Args:
            request (CaptureThumbnailRequest): A request to capture thumbnail.
        """
        try:
            if request.item.prim.IsInstanceProxy():
                # TODO: Failed to create attribute for such prim with error "authoring to an instance proxy is not allowed"
                carb.log_error(f"{request.item.url}: capture thumbnail on an instance proxy is not allowed")
                return
            # Config material to be captured
            material_path = Sdf.Path(request.item.url)
            if self._material_preview_producer is None:
                self._material_preview_producer = MaterialPreviewProducer()
            self._material_preview_producer.material_path = Sdf.Path(material_path)

            # Wait for renderer ready
            while not self._material_preview_producer.ready_for_capture:
                await asyncio.sleep(1)

            # Wait for material fully loaded
            await asyncio.sleep(3)

            # Capture thumbnail
            raw_data = await self._material_preview_producer.set_captured_data_async()
            if raw_data is not None:
                request.on_captured_fn(request.item, raw_data)
                request.done = True
                carb.log_info(f"Thumbnail captured for {request.item}")
            else:
                carb.log_error(f"Failed to capture thumbnail for {request.item.url}")
        except Exception as e:
            carb.log_error(f"Exception happens when capture thumbnail for {request.item.url}: {str(e)}")

    def capture(self, item: CaptureThumbnailRequest) -> None:
        """
        Capture material thumbnail.
        Args:
            request (CaptureThumbnailRequest): A request to capture thumbnail.
        """
        asyncio.ensure_future(self.capture_async(item))


class CaptureThumbnailManager:
    """
    Manager to capture thumbnails one by one.
    """

    def __init__(self):
        self._generator = CaptureThumbnailGenerator()
        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()
        self._active_item: Optional[CaptureThumbnailRequest] = None

        asyncio.ensure_future(self._run())

    def destroy(self):
        self._stop_event.set()
        self._work_queue.put_nowait(None)
        self._generator.destroy()

    def put(self, request: CaptureThumbnailRequest) -> bool:
        """
        Add a new thumbnail request.
        Args:
            request (CaptureThumbnailRequest): A request to capture thumbnail
        """
        if request.item and request.item.prim:
            if request.item.prim.IsInstanceProxy():
                # TODO: Failed to create attribute for such prim with error "authoring to an instance proxy is not allowed"
                carb.log_error(f"{request.item.url}: capture thumbnail on an instance proxy is not allowed")
                return False
            self._work_queue.put_nowait(request)
            return True
        else:
            return False

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            self._active_item = await self._work_queue.get()
            if self._active_item is None:
                break
            await self._generator.capture_async(self._active_item)
