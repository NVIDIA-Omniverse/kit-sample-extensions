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
import io
import time
from typing import List, Tuple

import carb.settings
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import capture_viewport_to_buffer
from PIL import Image
from pxr import Usd, UsdShade


# Safety net only: with nothing loading the capture starts a few updates after the bind.
_NOTHING_LOADS_DEADLINE_SECONDS = 30


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
        iterations (int): Frames to wait for renderer settings take effect. Default 8.
        on_thumbnail_done_fn (callable): Function called when thumbnail generation is done. Function signture:
            void on_thumbnail_done_fn(result: bool, url: str)

    Overridden functions:
        bool prepare_thumbnail(): Function called to prepare before thumbnail generation. Return True if all right.
            Otherwise return False to stop.
    """

    def __init__(
        self,
        url: str,
        output_url: str,
        width: int = 256,
        height: int = 256,
        render_mode: str = "RayTracing",
        iterations: int = 8,
        on_thumbnail_done_fn: callable = None,
    ):
        self._usd_context = None
        self._viewport_api = None

        self._width = width
        self._height = height
        self._url = url
        self.output_url = output_url
        self._iterations = iterations
        self._render_mode = render_mode
        self._on_thumbnail_done_fn = on_thumbnail_done_fn

        self._generate_thumbnail_future = None
        self._stage_event_sub = None
        self._waiting_for_asset_loaded = False
        self._capture_fallback_future = None
        self._assets_loading_seen = False
        self._target_prim = None
        self._material_path = None

        self.done = False

    def generate(self, usd_context_name, viewport_api) -> None:
        """
        Generate an thumbnail in the correct location
        """
        carb.log_info(f"[Thumbnail] Generate to {self.output_url}")

        self._usd_context = omni.usd.get_context(usd_context_name)
        self._viewport_api = viewport_api

        # It is very strange that must delete old thumbnail earlier, otherwise the ASSERT_LOADED stage event will not be triggered
        if (
            omni.client.stat(self.output_url)[0] == omni.client.Result.OK
            and omni.client.delete(self.output_url) != omni.client.Result.OK
        ):
            carb.log_error(f"[Thumbnail] Failed to delete thumbanil: {self.output_url}")
            self._on_thumbnail_done(False)
            return

        self._sub_commands()

        # let's check if we need to reload the stage
        carb.log_info(f"[Thumbnail] Open stage: {self._url}")
        current_stage = self._usd_context.get_stage_url()
        # For local template, we need to make sure "/" used and compare in lower case - the drive letter often different
        template_url = self._url.replace("\\", "/")
        if current_stage.lower() == template_url.lower():
            # the stage is already loaded, simple continue the flow.
            self._on_stage_opened(True, "")
        else:
            self._usd_context.open_stage_with_callback(self._url, self._on_stage_opened)

    def stop(self) -> None:
        """
        Stop thumbnail generation
        """
        if self._capture_fallback_future is not None:
            if not self._capture_fallback_future.done():
                self._capture_fallback_future.cancel()
            self._capture_fallback_future = None
        if self._generate_thumbnail_future is not None:
            if not self._generate_thumbnail_future.done():
                self._generate_thumbnail_future.cancel()
            self._generate_thumbnail_future = None

        # remove any stage subscription
        self._stage_event_sub = None
        self._unsub_commands()

    def prepare_thumbnail(self) -> Tuple[str]:
        """
        Prepare before thumbnail generation.
        Return Tuple[target prim path, material path] if succeed, otherwise return Tuple[None, None]
        """
        return (None, None)

    def _on_stage_opened(self, result: bool, error: str) -> None:
        """
        Start the generating process when the stage is loaded
        """
        if not result:
            carb.log_error("[Thumbnail] Failed to open stage {self._url}, error: {error}")
            self._on_thumbnail_done(False)
            return

        self._waiting_for_asset_loaded = True
        self._assets_loading_seen = False

        self._target_prim, self._material_path = self.prepare_thumbnail()
        if not self._target_prim:
            self._on_thumbnail_done(False)
            return

        # Kit sends ASSETS_LOADING when a load starts and ASSETS_LOADED 7 frames after it ends, and nothing at
        # all when the material is already loaded (every thumbnail after the first from the same MDL module).
        # Decide from that state: if no load started and nothing is loading, capture now.
        self._capture_fallback_future = asyncio.ensure_future(self._capture_if_nothing_loads_async())

    async def _capture_if_nothing_loads_async(self) -> None:
        for _ in range(8):  # Kit's own gate: ASSETS_LOADED comes 7 frames after a load ends
            await omni.kit.app.get_app().next_update_async()
            if not self._waiting_for_asset_loaded:
                return
        start = time.time()
        while self._waiting_for_asset_loaded:
            _, loaded, total = self._usd_context.get_stage_loading_status()
            if not self._assets_loading_seen and loaded >= total:
                if self._is_material_binded(self._material_path, self._target_prim):
                    self._start_capture()
                    return
            if time.time() - start > _NOTHING_LOADS_DEADLINE_SECONDS:
                carb.log_error(
                    f"[Thumbnail] {self.output_url}: no ASSETS_LOADED {_NOTHING_LOADS_DEADLINE_SECONDS} s after the bind "
                    f"(ASSETS_LOADING seen: {self._assets_loading_seen}, loading status {loaded}/{total}, "
                    f"material bound: {self._is_material_binded(self._material_path, self._target_prim)})"
                )
                self._waiting_for_asset_loaded = False
                self._on_thumbnail_done(False)
                return
            await omni.kit.app.get_app().next_update_async()

    def _on_stage_event(self, event) -> None:
        """
        Stage Event responder.
        We leverage this to be able to insert some logic once the Stage is fully loaded.
        There are some cases where this gets called multiple times for the scenes and the material.
        TODO: Ultimately we will need to have some way to find out what ASSETS trigger this callback.
        """
        if event.type == int(omni.usd.StageEventType.ASSETS_LOADING):
            self._assets_loading_seen = True
            return
        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            if not self._waiting_for_asset_loaded:
                return

            binded = self._is_material_binded(self._material_path, self._target_prim)
            if binded:
                self._start_capture()

    def _start_capture(self) -> None:
        if not self._waiting_for_asset_loaded:
            return
        self._waiting_for_asset_loaded = False

        async def generate_thumbnail_async():
            for _ in range(5):
                # Wait a few frames to make sure material fully loaded
                await omni.kit.app.get_app().next_update_async()
            result = await self._capture_viewport_async()

            self._on_thumbnail_done(result)

        self._generate_thumbnail_future = asyncio.ensure_future(generate_thumbnail_async())

    async def _capture_viewport_async(self) -> bool:
        """
        Setup the viewport in the desired state and capture the viewport
        """
        self._viewport_api.set_hd_engine("rtx", self._render_mode)
        self._viewport_api.resolution = (self._width, self._height)
        # We try to minimize global settings use to maintain isolation, but we need to set these to capture alpha
        settings = carb.settings.get_settings()
        alphaTo1 = settings.get("/app/captureFrame/setAlphaTo1")
        zeroAlpha = settings.get("/rtx/post/backgroundZeroAlpha/enabled")
        composite = settings.get("/rtx/post/backgroundZeroAlpha/backgroundComposite")
        alphaInComposite = settings.get("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite")
        grid = settings.get("/app/viewport/grid/enabled")

        settings.set("/app/captureFrame/setAlphaTo1", False)
        settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
        settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
        settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
        settings.set("/app/viewport/grid/enabled", False)

        # we are gonna resets the view so we need to wait render_iterations
        for _ in range(self._iterations):
            await omni.kit.app.get_app().next_update_async()

        # Capture viewport
        capture = capture_viewport_to_buffer(self._viewport_api, self.on_viewport_captured)
        await omni.kit.app.get_app().next_update_async()
        await capture.wait_for_result()

        settings.set("/app/captureFrame/setAlphaTo1", alphaTo1)
        settings.set("/rtx/post/backgroundZeroAlpha/enabled", zeroAlpha)
        settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", composite)
        settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", alphaInComposite)
        settings.set("/app/viewport/grid/enabled", grid)

        return await self._is_url_exists_async(self.output_url)

    def on_viewport_captured(self, buffer, buffer_size, width, height, fmt) -> None:
        """
        Function called when capturing viewport
        """
        try:
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
        except Exception as e:  # pylint: disable=broad-except
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
        result, _ = await omni.client.stat_async(url)
        return result == omni.client.Result.OK

    def _on_thumbnail_done(self, result: bool) -> None:
        carb.log_info(f"[Thumbnail] {self.output_url} generated: {result}")
        self._target_prim = None
        self._material_path = None
        self._stage_event_sub = None
        self._unsub_commands()
        self.done = True
        if self._on_thumbnail_done_fn:
            self._on_thumbnail_done_fn(result, self.output_url)

    def _sub_commands(self) -> None:
        # Subscribe commands to track material bind changing
        omni.kit.undo.subscribe_on_change(self._on_material_commands)

    def _unsub_commands(self) -> None:
        omni.kit.undo.unsubscribe_on_change(self._on_material_commands)

    def _on_material_commands(self, cmds: List[str]) -> None:
        if any(item in ["BindMaterial", "BindMaterialCommand"] for item in cmds) and self._stage_event_sub is None:
            # Use stage event to monitor necessary asset loaded
            self._stage_event_sub = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event, name="thumbnail_generation stage update"
            )

    def _is_material_binded(self, material_path: str, target_prim: str) -> bool:
        if not material_path or not target_prim:
            return False

        stage = self._usd_context.get_stage()
        prims = stage.Traverse(Usd.TraverseInstanceProxies(Usd.PrimIsActive and Usd.PrimIsDefined and Usd.PrimIsLoaded))
        for prim in prims:
            if prim.GetPath().pathString == target_prim:
                material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                if material and material.GetPath().pathString == material_path:
                    return True
        return False
