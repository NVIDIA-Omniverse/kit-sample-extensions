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
import os
import shutil
import time

import carb
import carb.settings
import carb.tokens
import omni.kit.app
import omni.ui as _ui
from omni import client as _client
from omni import ext
from omni import usd as _usd
from omni.kit import app as _app
from PIL import Image

from .capture import _viewport_capture_file

PERSISTENT_SETTINGS_PREFIX = "/persistent"


class ThumbnailGenerator(ext.IExt):
    """Generate thumbnails for USD and MDL files."""

    def __init__(self):
        self._standin_selection_window = None
        self._standin_combo = None
        self._settings = None
        self._content_window = None
        self._menu_id = None

        super().__init__()

    def on_startup(self):
        self._settings = carb.settings.get_settings()
        self._frame_capture_delay = self._settings.get_as_int("exts/omni.kit.thumbnails.usd/frame_capture_delay")

        self._standin_variants = []

        self._resolutions = [256]

        self._context = _usd.get_context()

        self._subscription = self._context.get_stage_event_stream().create_subscription_to_pop(
            self._on_save_event, name="[ext: thumbnail_generator] generate_thumbnail"
        )

        self._context_menu_name = f'{_ui.get_custom_glyph_code("${glyphs}/materials.svg")} '
        self._menus = []
        self._hooks = []

        try:
            # Content browser is optional. Ignore if not able to import.
            import omni.kit.window.content_browser as content

            self._content_window = content.get_content_window()
            self._menu_id = self._content_window.add_context_menu(
                "Save thumbnail", "materials.svg", self._save_thumbnail_for_file, None
            )
        except ImportError:
            pass

        manager = omni.kit.app.get_app().get_extension_manager()
        self._preferences_page = None
        self._hooks.append(
            manager.subscribe_to_extension_enable(
                on_enable_fn=lambda _: self._register_page(),
                on_disable_fn=lambda _: self._unregister_page(),
                ext_name="omni.kit.window.preferences",
                hook_name="omni.kit.thumbnails.usd omni.kit.window.preferences listener",
            )
        )

    def on_shutdown(self):
        self._unregister_page()
        if self._content_window:
            self._content_window.delete_context_menu(self._menu_id)
            self._content_window = None

        if self._menu_id:
            self._menu_id = None

        del self._standin_selection_window
        del self._standin_combo
        self._standin_selection_window = None
        self._standin_combo = None

        self._subscription = None

    def _register_page(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        prefs = manager.get_extension_dict(
            manager.get_extension_id_by_module("omni.kit.window.preferences")
        ).get_dict()["package"]
        version = tuple([int(v) for v in prefs["version"].split(".")])
        if version >= (1, 4, 0):
            try:
                from omni.kit.window.preferences import register_page

                from .thumbnail_generation_page import ThumbnailGenerationPreferences

                self._preferences_page = register_page(ThumbnailGenerationPreferences())
            except ModuleNotFoundError:
                pass

    def _unregister_page(self):
        if self._preferences_page:
            try:
                import omni.kit.window.preferences

                omni.kit.window.preferences.unregister_page(self._preferences_page)
                self._preferences_page = None
            except ModuleNotFoundError:
                pass

    def _get_standins(self):
        if not self._standin_variants:
            # services = _services_client.Client(self._mdl_server)
            # self._standin_variants = await services.get_standins(__method__="get")
            # TODO: replace this with the service request above once service is deployed.
            self._standin_variants = [
                "Fabric",
                "Leather",
                "Metal_can",
                "Metals",
                "Origami",
                "Painted_paper",
                "Rock",
                "Wooden",
            ]

        return self._standin_variants

    def _save_thumbnail_for_file(self, menu, content_url: str):
        """Start watching for the layer and run the editor"""
        self._settings.set("/app/captureFrame/setAlphaTo1", True)
        asyncio.ensure_future(self._generate_thumbnail_async_usd(content_url + ".png"))
        self._settings.set("/app/captureFrame/setAlphaTo1", False)

    def _on_save_event(self, event):
        if event.type == int(_usd.StageEventType.SAVED) and self._settings.get_as_bool(
            PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/thumbnail_on_save"
        ):
            self._generate_thumbnail_usd(self._context)

    def _generate_thumbnail_usd(self, context):
        file_path = context.get_stage_url() + ".png"
        asyncio.ensure_future(self._generate_thumbnail_async_usd(file_path))

    async def _generate_thumbnail_async_usd(self, file_path: str):
        """Generate a thumbnail for the currently active USD file.

        Rendering is done by taking a screen capture of the current viewport.
        Data is stored locally or on omniverse depending on url of the USD file
        """
        # check loading status and wait for any marterials to load
        # OM-94687: generate the thumbnail when load finished
        if self._settings.get_as_bool(PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load"):
            timeout = time.time() + self._settings.get_as_int(
                PERSISTENT_SETTINGS_PREFIX + "/exts/omni.kit.thumbnails.usd/wait_stage_load_timeout"
            )
            frame_out_setting_value = self._settings.get_as_int(
                "/exts/omni.kit.thumbnails.usd/wait_stage_load_frameout"
            )
            frame_count = 0
            while time.time() < timeout:
                _, files_loaded, total_files = omni.usd.get_context().get_stage_loading_status()
                if files_loaded or total_files:
                    await omni.kit.app.get_app().next_update_async()
                    frame_count = 0
                    continue
                frame_count += 1
                if frame_count >= frame_out_setting_value:
                    break
                await omni.kit.app.get_app().next_update_async()
            else:
                carb.log_warn(f"Generate thumbnail in stage loading status.")

        settings = carb.settings.get_settings()
        only_viewport = settings.get_as_bool(PERSISTENT_SETTINGS_PREFIX + "/app/captureFrame/viewport")
        settings.set_bool(PERSISTENT_SETTINGS_PREFIX + "/app/captureFrame/viewport", True)
        tmpdir = carb.tokens.get_tokens_interface().resolve("${temp}")
        temp_thumb_folder = os.path.join(tmpdir, ".thumbs")
        screen_capture_path = os.path.join(tmpdir, os.path.basename(file_path))

        await _viewport_capture_file(screen_capture_path)

        delay = self._frame_capture_delay
        timeout = time.time() + delay
        while time.time() < timeout:
            if os.path.exists(screen_capture_path):
                break
            await _app.get_app_interface().next_update_async()
        else:
            raise Exception(f"Unable to capture frame within {delay} seconds. {screen_capture_path}")

        output_folder = os.path.join(os.path.dirname(file_path), ".thumbs")

        for resolution in self._resolutions:
            error = None
            limit = 5
            # Windows can be slow when capturing image causing access and permission denied errors
            for _ in range(limit):
                try:
                    self._crop_and_resize_image(screen_capture_path, [resolution, resolution])
                    break
                except Exception as exc:
                    error = exc
                    await _app.get_app().next_update_async()
            else:
                carb.log_error(f"Cannot create thumbnail for {screen_capture_path}: {error}")

        # if context.is_omni_stage():
        await self._store_omniverse(temp_thumb_folder, output_folder)
        carb.log_info(f"Thumbnails generated for {file_path}")

        settings.set_bool(PERSISTENT_SETTINGS_PREFIX + "/app/captureFrame/viewport", only_viewport)
        self._clean_up_temp_files(temp_thumb_folder)
        self._clean_up_temp_files(screen_capture_path)

    def _clean_up_temp_files(self, path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as exc:
            carb.log_warn(f"Unable to clean up temporary files: {path}: {exc}")

    async def _store_omniverse(self, src_folder, dest_folder):
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                src_path = os.path.join(root, file)
                dest_path = src_path.replace(src_folder, dest_folder)
                dest_path = dest_path.replace("\\", "/")
                result = await _client.delete_async(dest_path)
                if result not in (_client.Result.OK, _client.Result.ERROR_NOT_FOUND):
                    carb.log_error(f"Error updating thumbnail: {result}")

                result = await self._create_folder(os.path.dirname(dest_path))

                result = await _client.copy_async(src_path, dest_path)
                if result != _client.Result.OK:
                    carb.log_error(f"Copy to omniverse failed: {result}")

    async def _create_folder(self, folder, raise_if_exists=False):
        result = await _client.create_folder_async(folder)
        acceptable_results = [_client.Result.OK]
        if not raise_if_exists:
            acceptable_results.append(_client.Result.ERROR_ALREADY_EXISTS)

        if result not in acceptable_results:
            raise Exception(f"{folder} could not be created: {result}")

    def _crop_and_resize_image(self, image_path, resolution):
        """For a given image and resolution image is resized and stored under a .thumbs directory along the current path."""
        base_path = os.path.dirname(image_path)
        output_dir = os.path.join(base_path, ".thumbs", f"{resolution[0]}x{resolution[1]}")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, os.path.basename(image_path))

        # Crop the center of the image
        im = Image.open(image_path)
        os.stat(output_dir)
        width, height = im.size  # Get dimensions
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
        im.thumbnail(resolution, Image.LANCZOS)
        im.save(output_path, "png")

        return output_path
