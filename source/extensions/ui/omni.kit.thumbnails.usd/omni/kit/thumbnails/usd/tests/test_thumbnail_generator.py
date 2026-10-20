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
import platform
import shutil
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

import carb
import omni.kit.app
import omni.usd
from omni import usd
from omni.kit import test
from omni.kit.thumbnails.usd import main
from PIL import Image

from ..thumbnail_manager import ThumbnailManager
from ..usd_thumbnail_generator import UsdThumbnailGenerator

_RESOURCES = os.path.join(os.path.dirname(__file__), "data")


class _MockEditor:
    def capture_next_frame(self, output_file):
        im = Image.new(mode="RGB", size=(600, 600), color=(0, 0, 0))
        im.save(output_file, "PNG")


class ImageResizeTestCase(test.AsyncTestCase):
    async def test_thumbnail_resize(self):
        im = Image.new(mode="RGB", size=(600, 600), color=(0, 0, 0))
        inst = main.ThumbnailGenerator()
        resolution = 256

        expected_path = "{tmpdir}/.thumbs/256x256/foo.png"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "foo.png")
            im.save(output_file, "PNG")
            inst._crop_and_resize_image(output_file, [resolution, resolution])
            self.assertTrue(os.path.exists(expected_path.format(tmpdir=tmpdir)))

            new_image = Image.open(expected_path.format(tmpdir=tmpdir))
            self.assertEquals(new_image.size, (resolution, resolution))
            new_image = None


class GenerateUsdThumbnailTestCase(test.AsyncTestCase):
    async def setUp(self):
        self._inst = main.ThumbnailGenerator()
        self._inst.on_startup()
        self._inst._editor = _MockEditor()

        self._tmpdir = tempfile.TemporaryDirectory()
        self._expected_path = f"{self._tmpdir.name}/.thumbs/256x256/World2.usda.png"
        usd_file = os.path.join(self._tmpdir.name, "World2.usda")
        shutil.copyfile(os.path.join(_RESOURCES, "World2.usda"), usd_file)

        success, error = await usd.get_context().open_stage_async(usd_file)
        if not success:
            raise Exception(f"Failed to open usd file: {error}")

        context = usd.get_context()
        self._filename = context.get_stage_url() + ".png"

    async def tearDown(self):
        # Close stage otherwise we won't receive events for next test
        await usd.get_context().close_stage_async()
        self._inst.on_shutdown()

    @unittest.skipUnless(platform.system().lower() == "windows", "Times out on Linux while compiling shaders")
    async def test_generate_usd(self):
        await self._inst._generate_thumbnail_async_usd(self._filename)

        self.assertTrue(os.path.exists(self._expected_path))


# Workaround, ASSETS_LOADED event is never triggered for this stage.
# Instead we start the capture from the generator's own open callback. Kit 111 sends OPENED before
# that callback runs, so translating OPENED (as before) found the generator not yet waiting.
class _MockThumbnailGenerator(UsdThumbnailGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_result = None  # (result, error) once the open callback has run
        self.opened = asyncio.Event()  # set once the open callback has run and the capture was started

    def _on_stage_event(self, event):
        return

    def _on_stage_opened(self, result, error):
        self.open_result = (result, error)
        super()._on_stage_opened(result, error)
        if self._waiting_for_asset_loaded:
            mock_event = MagicMock()
            mock_event.type = int(omni.usd.StageEventType.ASSETS_LOADED)
            super()._on_stage_event(mock_event)
        self.opened.set()


_OPEN_DEADLINE_SECONDS = 60


async def _wait_for_capture_start(test_case, gen):
    try:
        await asyncio.wait_for(gen.opened.wait(), _OPEN_DEADLINE_SECONDS)
    except asyncio.TimeoutError:
        test_case.fail(
            f"Open callback not called within {_OPEN_DEADLINE_SECONDS} s "
            f"(open result: {gen.open_result}, waiting for assets: {gen._waiting_for_asset_loaded})"
        )
    test_case.assertIsNotNone(
        gen._generate_thumbnail_future, f"Capture not started after the open callback (open result: {gen.open_result})"
    )


class ThumbnailGeneratorTestCase(test.AsyncTestCase):
    async def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._usd_file = os.path.join(self._tmpdir.name, "World2.usda")
        self._output_file = os.path.join(self._tmpdir.name, tempfile.gettempprefix())
        shutil.copyfile(os.path.join(_RESOURCES, "World2.usda"), self._usd_file)
        # In omni.kit.widget.viewport.impl.utility we expect the context to have a stage
        await omni.usd.get_context().new_stage_async()

    async def tearDown(self):
        # Close the current stage otherwise events won't be triggered for the next test
        await omni.usd.get_context().close_stage_async()
        self._tmpdir.cleanup()

    @unittest.skipUnless(platform.system().lower() == "windows", "Times out on Linux while downloading dependencies")
    async def test_thumbnail_generator(self):
        # setup timer to wait for 30 seconds or until omni.usd.StageEventType.OPENED received
        future_test = asyncio.Future()

        def on_timeout():
            nonlocal future_test
            future_test.set_result(False)
            carb.log_error("stage event omni.usd.StageEventType.OPENED hasn't been received")

        def on_stage_event(event):
            if event.type == int(omni.usd.StageEventType.OPENED):
                nonlocal timeout_timer
                timeout_timer.cancel()
                nonlocal future_test
                future_test.set_result(True)
                carb.log_info("stage event omni.usd.StageEventType.OPENED received")

        timeout_timer = threading.Timer(30.0, on_timeout)
        stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(on_stage_event, name="omni.kit.thumbnails.usd.test_thumbnail_generator")
        )

        # setup thumbnain generator
        mock_thumbnail_done = Mock()
        gen = _MockThumbnailGenerator(
            self._usd_file, self._output_file, template_url=self._usd_file, on_thumbnail_done_fn=mock_thumbnail_done
        )
        gen.generate()

        # wait for stage to load or timeout
        timeout_timer.start()

        await _wait_for_capture_start(self, gen)
        await gen._generate_thumbnail_future

        mock_thumbnail_done.assert_called_once_with(True, self._output_file)

    @unittest.skipUnless(platform.system().lower() == "windows", "Times out on Linux while downloading dependencies")
    async def test_manager(self):
        mgr = ThumbnailManager()

        mock_thumbnail_done = Mock()
        gen = _MockThumbnailGenerator(self._usd_file, self._output_file, on_thumbnail_done_fn=mock_thumbnail_done)

        mgr.put(gen)
        await _wait_for_capture_start(self, gen)
