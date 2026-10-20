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
import ctypes
import importlib
import os
from typing import Callable, List, Optional, Tuple

import carb
import omni.kit.app
import omni.timeline
import omni.usd
from omni.kit.viewport.utility import capture_viewport_to_buffer, get_active_viewport
from PIL import Image
from pxr import Sdf, Usd

from ..external import UsdBakedPreview
from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_THUMBNAIL_PATH = "thumbnail_path"
THUMBNAIL_SIZE = (160, 90)


class ThumbnailSetting(AbstractWaypointSetting):
    def __init__(self, edit_context=None, viewport_widget=None, thumbnail_path=None):
        super().__init__(edit_context)
        self.thumbnail_path = thumbnail_path
        if self.thumbnail_path:
            self.save_thumnail_path()
        self.on_created_fn: "Callable[..., None]|None" = None
        self._renderer_capture = None
        # In the case that the viewport is a widget, using viewport_widget
        self._viewport_api = viewport_widget or get_active_viewport()

    @property
    def thumbnail_data(self) -> Optional[Tuple[bytes, int, int]]:
        if self.prim is None:
            return None

        loaded = False
        if self.prim.HasAttribute(WAYPOINT_ATTR_THUMBNAIL_PATH):
            if not self.thumbnail_path:
                self.thumbnail_path = self.prim.GetAttribute(WAYPOINT_ATTR_THUMBNAIL_PATH).Get()
            try:
                height = width = 0
                bytes = None
                with Image.open(self.thumbnail_path) as im:
                    # Check if image has valid dimensions
                    if im.width <= 0 or im.height <= 0:
                        raise ValueError("Invalid image dimensions")

                    height = im.height
                    width = im.width

                    # Convert to RGBA mode if necessary
                    if im.mode != "RGBA":
                        im = im.convert("RGBA")

                    bytes = im.tobytes("raw", "RGBA")

                    # Validate that we got valid bytes
                    if not bytes or len(bytes) != width * height * 4:
                        raise ValueError("Invalid image data")

                baked_data = (bytes, width, height)
                loaded = True
            except (OSError, IOError, ValueError, SyntaxError) as e:
                # Handle file system errors, corrupted images, and invalid data
                carb.log_error(f"[Waypoint] Failed to load thumbnail from {self.thumbnail_path}: {e}")
                loaded = False

        if not loaded:
            baked = UsdBakedPreview(self.prim)
            baked_data = baked.get_baked_preview_data()

        return baked_data

    def get_name(self):
        return "thumbnail"

    def delete(self) -> None:
        if self.thumbnail_path:
            try:
                # TODO: this works for local files ONLY! Improve this when it's time to do server files
                os.remove(self.thumbnail_path)
            except Exception as e:  # pragma: no cover
                carb.log_info(f"Unable to delete viewport waypoint's thumbnail file: {self.thumbnail_path} due to {e}")

    def recall(self, prim: Usd.Prim) -> None:
        pass

    async def save_to_usd_async(self, prim: Usd.Prim) -> None:
        await self.set_captured_data_async(THUMBNAIL_SIZE)

    def save_to_usd(self, prim: Usd.Prim) -> None:
        asyncio.ensure_future(self.set_captured_data_async(THUMBNAIL_SIZE, self.on_created_fn))

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        # TODO: old version save thumbnail to file but not usd attribute, we can remove it later
        thumbnail_attr = prim.GetAttribute(WAYPOINT_ATTR_THUMBNAIL_PATH)
        if thumbnail_attr:
            self.thumbnail_path = thumbnail_attr.Get()
        else:
            self.thumbnail_path = None

    async def get_raw_data_async(self) -> None:
        """
        Gets the framebuffer contents.

        It's async because the data becomes available the next frame.
        """
        schedule_capture = capture_viewport_to_buffer(self._viewport_api, self._on_viewport_captured)
        await schedule_capture.wait_for_result()

    def _on_viewport_captured(self, buffer, buffer_size, width, height, format):
        try:
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
        except Exception as e:  # pragma: no cover
            carb.log_error(f"[Waypoint] Failed to get capture buffer: {e}")
            if self.on_created_fn is not None:
                self.on_created_fn(False)
            return None

        # Constrcut Image object
        buffer = content.contents
        im = Image.frombytes("RGBA", (width, height), buffer)

        # Crop the center of the image if necessary
        # width, height = im.size  # Get dimensions
        original_aspect = float(width) / height
        thumbnail_aspect = float(THUMBNAIL_SIZE[0]) / THUMBNAIL_SIZE[1]
        if original_aspect != thumbnail_aspect:
            if original_aspect > thumbnail_aspect:
                left = (width - float(height) * thumbnail_aspect) / 2
                right = width - left
                top = 0
                bottom = height
            else:
                left = 0
                right = width
                top = (height - float(width) / thumbnail_aspect) / 2
                bottom = height - top
            im = im.crop((left, top, right, bottom))

        # Generate thumbnail
        im.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

        if self.thumbnail_path:
            im.save(self.thumbnail_path)
            if self.on_created_fn is not None:
                self.on_created_fn(True)
            return

        # Save to prim
        if self.prim:
            with self.edit_context:
                baked = UsdBakedPreview(self.prim)
                try:
                    baked.set_baked_preview_data(im.tobytes(), THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1], format)
                except AttributeError:  # pragma: no cover
                    # trying to update on an out-dated session
                    return

                if self.on_created_fn is not None:
                    self.on_created_fn(True)

    async def set_captured_data_async(self, size: Tuple[int, int] = (256, 256), on_captured_fn: callable = None):
        if not self.prim:
            if on_captured_fn is not None:
                on_captured_fn(None)
            return None

        await self.get_raw_data_async()

    def save_thumnail_path(self) -> None:
        """Assigns the thumbnail path"""
        if self.prim:
            attr = self.prim.GetAttribute(WAYPOINT_ATTR_THUMBNAIL_PATH)
            if not attr:
                attr = self.prim.CreateAttribute(WAYPOINT_ATTR_THUMBNAIL_PATH, Sdf.ValueTypeNames.String)
            attr.Set(self.thumbnail_path)
