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
import ctypes
import io
import time
from typing import Tuple

import carb.settings
import omni.kit.app
import omni.usd
from PIL import Image

from .capture import _viewport_capture_bytes

RENDERER_RESOLUTION_WIDTH = "/app/renderer/resolution/width"
RENDERER_RESOLUTION_HEIGHT = "/app/renderer/resolution/height"
RENDERER_MODE = "/rtx/rendermode"
CAPTURE_VIEWPORT_ONLY = "/persistent/app/captureFrame/viewport"
CAPTURE_ALPHA = "/app/captureFrame/setAlphaTo1"
VIEWPORT_DISPLAY_OPTIONS = "/persistent/app/viewport/displayOptions"
POST_BACKGROUND_ZERO_APLHA_ENABLED = "/rtx/post/backgroundZeroAlpha/enabled"
POST_BACKGROUND_ZERO_APLHA_COMPISITED = "/rtx/post/backgroundZeroAlpha/backgroundComposite"


class ViewportThumbnailGenerator:
    """
    Generate thumbnail with viewport

    Args:
        url (str): Url of stage to generate thumbnail
        output_url (str): Url of generated thumbnail

    Keyword args:
        width (int): Width of generated thumbnail, in pixels. Default 256.
        height (int): Height of generate thumbnail, in pixels. Default 256.
        render_mode (str): Render mode when generating thumbnail. Default RayTracing.
        iterations (int): Frames to wait for renderer settings take effect. Default 4.
        startup_time_threshold (int): Time threshold after stage loaded to make sure assets loaded, in seconds. Default 2.
        on_thumbnail_done_fn (callable): Function called when thumbnail generation is done. Function signture:
            void on_thumbnail_done_fn(result: bool, url: str)

    Overridden functions:
        bool prepare_thumbnail(): Function called to prepare before thumbnail generation. Return True if all right.
            Otherwise return False to stop.
        void push_pop_renderer_settings(push: bool): Function called to push/pop renderer settings before/after thunbnail generated.
            Default will set viewport resolution, renderer mode and capture viewport only.
    """

    def __init__(
        self,
        url: str,
        output_url: str,
        width: int = 256,
        height: int = 256,
        render_mode: str = "RayTracing",
        iterations: int = 8,
        startup_time_threshold: int = 2,
        on_thumbnail_done_fn: callable = None,
    ):
        self._settings = carb.settings.get_settings()
        self._usd_context = omni.usd.get_context()

        self._width = width
        self._height = height
        self._url = url
        self.output_url = output_url
        self._iterations = iterations
        self._startup_time_threshold = startup_time_threshold
        self._render_model = render_mode
        self._on_thumbnail_done_fn = on_thumbnail_done_fn

        self._generate_thumbnail_future = None
        self._stage_event_sub = None
        self._waiting_for_asset_loaded = False

    def generate(self) -> None:
        """
        Generate an thumbnail in the correct location
        """
        carb.log_info(f"[Thumbnail] Generate to {self.output_url}")

        # It is very strange that must delete old thumbnail earlier, otherwise the ASSERT_LOADED stage event will not be triggered
        if omni.client.stat(self.output_url)[0] == omni.client.Result.OK:
            if omni.client.delete(self.output_url) != omni.client.Result.OK:
                carb.log_error(f"[Thumbnail] Failed to delete thumbanil: {self.output_url}")
                self._on_thumbnail_done(False)
                return

        # Use stage event to monitor necessary asset loaded
        if self._stage_event_sub is None:
            self._stage_event_sub = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event, name="thumbnail_generation stage update"
            )

        # let's check if we need to reload the stage
        carb.log_info(f"[Thumbnail] Open stage: {self._url}")
        current_stage = self._usd_context.get_stage_url()
        # TODO: Issue here, when the stage is already opened we won't receive events
        if current_stage == self._url:
            # the stage is already loaded, simple continue the flow.
            self._on_stage_opened(True, "")
        else:
            self._usd_context.open_stage_with_callback(self._url, self._on_stage_opened)

    def stop(self) -> None:
        """
        Stop thumbnail generation
        """
        if self._generate_thumbnail_future is not None:
            if not self._generate_thumbnail_future.done():
                self._generate_thumbnail_future.cancel()
            self._generate_thumbnail_future = None

        # remove any stage subscription
        self._stage_event_sub = None

    def prepare_thumbnail(self) -> bool:
        """
        Prepare before thumbnail generation.
        Return True if all right. Otherwise return False to stop.
        """
        return True

    def push_pop_renderer_settings(self, push: bool) -> None:
        """
        Push/pop renderer settings before/after thumbnail generation.
        Args:
            push (bool): True to push renderer settings. False to pop renderder settings.
        """
        if push:
            # Save current renderer settings
            self._current_resolution_width = self._settings.get(RENDERER_RESOLUTION_WIDTH)
            self._current_resolution_height = self._settings.get(RENDERER_RESOLUTION_HEIGHT)
            self._current_capture_only_viewport = self._settings.get(CAPTURE_VIEWPORT_ONLY)
            self._current_display_options = self._settings.get(VIEWPORT_DISPLAY_OPTIONS)
            self._current_render_mode = self._settings.get(RENDERER_MODE)
            self._current_capture_alpha = self._settings.get(CAPTURE_ALPHA)
            self._current_background_zero_alpha_enabled = self._settings.get(POST_BACKGROUND_ZERO_APLHA_ENABLED)
            self._current_background_zero_alpha_composited = self._settings.get(POST_BACKGROUND_ZERO_APLHA_COMPISITED)

            # Set the renderer settings

            # Here we use higher resolution when capturing viewport and down sampling later for better edge quality
            self._settings.set(RENDERER_RESOLUTION_WIDTH, 512)
            self._settings.set(RENDERER_RESOLUTION_HEIGHT, 512)
            self._settings.set(RENDERER_MODE, self._render_model)
            self._settings.set(CAPTURE_VIEWPORT_ONLY, True)
            self._settings.set(VIEWPORT_DISPLAY_OPTIONS, 0)

            self._settings.set(CAPTURE_ALPHA, False)
            self._settings.set(POST_BACKGROUND_ZERO_APLHA_ENABLED, True)
            self._settings.set(POST_BACKGROUND_ZERO_APLHA_COMPISITED, False)
        else:
            # Restore the renderer settings
            self._settings.set(RENDERER_RESOLUTION_WIDTH, self._current_resolution_width)
            self._settings.set(RENDERER_RESOLUTION_HEIGHT, self._current_resolution_height)
            self._settings.set(RENDERER_MODE, self._current_render_mode)
            self._settings.set(CAPTURE_VIEWPORT_ONLY, self._current_capture_only_viewport)
            self._settings.set(VIEWPORT_DISPLAY_OPTIONS, self._current_display_options)
            self._settings.set(CAPTURE_ALPHA, self._current_capture_alpha)
            self._settings.set(POST_BACKGROUND_ZERO_APLHA_ENABLED, self._current_background_zero_alpha_enabled)
            self._settings.set(POST_BACKGROUND_ZERO_APLHA_COMPISITED, self._current_background_zero_alpha_composited)

    def _on_stage_opened(self, result: bool, error: str) -> None:
        """
        Start the generating process when the stage is loaded
        """
        if not result:
            carb.log_error("[Thumbnail] Failed to open stage {self._url}, error: {error}")
            self._on_thumbnail_done(False)
            return

        self._generation_start_time = time.time()
        self._waiting_for_asset_loaded = True

        if not self.prepare_thumbnail():
            self._on_thumbnail_done(False)

    def _on_stage_event(self, event) -> None:
        """
        Stage Event responder
        We leverage this to be able to insert some logic once the Stage is fully loaded
        There are some case where this get called multiple times for the scenes and the material
        We introduce a small time to make sure we don't pick up on any early call back
        TODO: Ultimately we will need to have some way to find out what ASSETS trigger this callback

        Args:
            event (StageEvent): the stage event that happend
        """
        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            # This pin is setup when we are waiting for an MDL file to load
            if self._waiting_for_asset_loaded:

                async def generate_thumbnail_async():
                    self._waiting_for_asset_loaded = False
                    # om-11538
                    if time.time() - self._generation_start_time < self._startup_time_threshold:
                        time.sleep(self._startup_time_threshold)
                    result = await self._capture_viewport_async()

                    self._on_thumbnail_done(result)

                self._generate_thumbnail_future = asyncio.ensure_future(generate_thumbnail_async())

    async def _capture_viewport_async(self) -> bool:
        """
        Setup the viewport in the desired state and capture the viewport
        Always capture to local and down sampling for better edge queality
        """
        self.push_pop_renderer_settings(True)

        # we are gonna resets the view so we need to wait render_iterations
        for iteration in range(self._iterations):
            await omni.kit.app.get_app().next_update_async()

        await _viewport_capture_bytes(self.on_viewport_captured)

        self.push_pop_renderer_settings(False)

        return await self._is_url_exists_async(self.output_url)

    def on_viewport_captured(self, buffer, buffer_size, width, height, format) -> None:
        """
        Function called when capturing viewport
        """
        try:
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
        except Exception as e:
            carb.log_error(f"[Thumbnail] Failed to get capture buffer: {e}")
            return

        # Crop and down sample
        data = self._generate_thumbnail_data(content.contents, (width, height))

        # Save to output url
        result = omni.client.write_file(self.output_url, data)
        if result != omni.client.Result.OK:
            carb.log_error(f"[Thumbnail] Cannot write {self.output_url}, error code: {result}.")
        else:
            carb.log_info(f"[Thumbnail] Exported to {self.output_url}")

    def _generate_thumbnail_data(self, raw_data, size: Tuple[int, int]) -> bytes:
        """
        Generate desired thumbnail data from raw data
        """
        # Constrcut Image object
        im = Image.frombytes("RGBA", size, raw_data)

        # Crop the center of the image if necessary
        width, height = im.size  # Get dimensions
        if width != height:
            if width > height:
                left = (width - height) / 2
                right = width - left
                top = 0
                bottom = height
            else:
                left = 0
                right = width
                top = (height - width) / 2
                bottom = height - top
            im = im.crop((left, top, right, bottom))

        im.thumbnail((self._width, self._height), Image.LANCZOS)

        # Save to buffer
        buffer = io.BytesIO()
        im.save(buffer, "png")
        return buffer.getvalue()

    async def _is_url_exists_async(self, url) -> bool:
        """
        Check if the url exists
        Args:
            url (str): Url to check

        Returns:
            bool: return true if the url exists. Otherwise return false.
        """
        result, entries = await omni.client.stat_async(url)
        return result == omni.client.Result.OK

    def _on_thumbnail_done(self, result: bool) -> None:
        carb.log_info(f"[Thumbnail] {self.output_url} generated: {result}")
        self._stage_event_sub = None
        if self._on_thumbnail_done_fn:
            self._on_thumbnail_done_fn(result, self.output_url)
