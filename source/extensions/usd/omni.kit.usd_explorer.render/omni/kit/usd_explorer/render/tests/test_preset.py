import asyncio
import copy
import os
import shutil
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.test
import omni.ui as ui

from ..preset import get_instance

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("_testoutput")


class TestRenderPreset(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._test_dir = str(TEST_DATA_PATH.absolute().joinpath("test_render_preset").absolute())

    # After running each test
    async def tearDown(self):
        # shutil.rmtree(self._test_dir)
        return

    async def test_render_preset(self):
        preset = get_instance()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self._settings = carb.settings.get_settings()
        # "Draft" is the initial preset, so setting it here would be a no-op. It is
        # asserted at the end instead, where switching back to it is a real transition.
        self.assertEqual(preset.get_current_render(), "Draft")

        preset.set_value("Preview")
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(preset.get_current_render(), "Preview")

        self.assertEqual(self._settings.get("/rtx/pathtracing/maxBounces"), 4)
        self.assertEqual(self._settings.get("/rtx/pathtracing/maxSpecularAndTransmissionBounces"), 6)
        self.assertEqual(self._settings.get("/rtx/pathtracing/totalSpp"), 100)
        self.assertEqual(self._settings.get("/rtx/rendermode"), "PathTracing")
        self.assertEqual(self._settings.get("/rtx/renderpreset"), "Preview")

        preset.set_value("Photo")
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(preset.get_current_render(), "Photo")

        self.assertEqual(self._settings.get("/rtx/pathtracing/maxBounces"), 12)
        self.assertEqual(self._settings.get("/rtx/pathtracing/maxSpecularAndTransmissionBounces"), 6)
        self.assertEqual(self._settings.get("/rtx/pathtracing/totalSpp"), 600)
        self.assertEqual(self._settings.get("/rtx/rendermode"), "PathTracing")
        self.assertEqual(self._settings.get("/rtx/renderpreset"), "Photo")

        preset.set_value("Draft")
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(preset.get_current_render(), "Draft")

        self.assertEqual(self._settings.get("/rtx/rendermode"), "RaytracedLighting")
        self.assertEqual(self._settings.get("/rtx/renderpreset"), "Draft")
