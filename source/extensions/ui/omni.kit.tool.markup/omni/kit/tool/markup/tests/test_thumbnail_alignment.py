# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
import ctypes
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.renderer.capture
import omni.ui as ui
import omni.usd
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest
from PIL import Image

HERE = Path(__file__).parent
DATA = HERE.parent.parent.parent.parent.parent / "data" / "tests"
STAGE = DATA / "scenes" / "markup_alignment_test.usda"
ROOT = "/persistent/exts/omni.kit.tool.markup/"
VIEWPORT_RECT = ROOT + "viewport_rect"
TOOL_HIDE = ROOT + "tool_hide"
UI_HIDE = "/app/window/hideUi"
SIZE = (160, 90)
EDIT_VIEWPORT_SIZE = (920, 540)
CAPTURE_VIEWPORT_SIZE = (1280, 720)

# Markup strokes draw themselves on over several seconds, so both captures have to
# settle until that animation completes: a half-drawn stroke reads as a smaller
# bounding box and is indistinguishable from a misalignment. Measured convergence
# is well under this value -- the bounds are already identical and stable by 150
# updates, whereas at 60 the reference is still growing.
SETTLE_UPDATES = 150
CAPTURE_UPDATES = 1


class TestThumbnailAlignment(OmniUiTest):
    """Verify thumbnail markup alignment after the viewport grows for capture."""

    async def setUp(self):
        await super().setUp()
        self.settings = carb.settings.get_settings()
        self.stashed = {TOOL_HIDE: self.settings.get(TOOL_HIDE), UI_HIDE: self.settings.get(UI_HIDE)}
        self.context = omni.usd.get_context()
        await self.context.open_stage_async(str(STAGE.absolute()))
        await self.wait_updates(10)
        self.markups = get_markup_instance()
        self.assertIsNotNone(self.markups)
        # Imported here rather than at module scope on purpose: test_markup_tools
        # disables and re-enables omni.kit.tool.markup, which replaces the extension
        # module. A module-scope import would keep reading the dead module's
        # g_singleton (left as None by on_shutdown) and always see None here.
        from omni.kit.tool.markup import get_instance as get_markup_tool_instance

        self.markup_tool = get_markup_tool_instance()
        self.assertIsNotNone(self.markup_tool)
        self.markups.load_markups()
        self.markup = self.markups.get_markup("Markup_00")
        self.assertIsNotNone(self.markup)

        # Start fullscreen so the first capture is a known-good control. The
        # thumbnail capture subsequently forces the authoring-to-capture resize.
        self.viewport_window = get_active_viewport_window()
        self.assertIsNotNone(self.viewport_window)
        self.original_viewport_size = (self.viewport_window.width, self.viewport_window.height)
        self.viewport_window.width, self.viewport_window.height = CAPTURE_VIEWPORT_SIZE
        self.viewport_window.visible = True
        await self.wait_updates(5)

    async def tearDown(self):
        for path, value in self.stashed.items():
            self.settings.set(path, value)
        self.viewport_window.width, self.viewport_window.height = self.original_viewport_size
        await self.context.new_stage_async()
        await super().tearDown()

    async def wait_updates(self, count):
        for _ in range(count):
            await omni.kit.app.get_app().next_update_async()

    def rect(self):
        value = self.settings.get(VIEWPORT_RECT)
        return list(value) if value is not None else None

    async def reset(self):
        self.settings.set(TOOL_HIDE, False)
        self.settings.set(UI_HIDE, False)
        self.viewport_window.width, self.viewport_window.height = EDIT_VIEWPORT_SIZE
        self.markups.recall_markup(None)
        await self.wait_updates(1)
        self.markups.recall_markup(self.markup)
        await self.wait_updates(5)
        self.assertTrue(self.markups.begin_edit_markup(self.markup))
        await self.wait_updates(5)

    def thumbnail(self, image):
        rect = self.rect()
        if rect is None:
            left, top, right, bottom = 0.0, 0.0, float(image.width), float(image.height)
        else:
            scale = ui.Workspace.get_dpi_scale()
            left, top, right, bottom = (float(value) * scale for value in rect)
        width, height = right - left, bottom - top
        aspect = SIZE[0] / SIZE[1]
        if width / height > aspect:
            inset = (width - height * aspect) / 2
            left, right = left + inset, right - inset
        elif width / height < aspect:
            inset = (height - width / aspect) / 2
            top, bottom = top + inset, bottom - inset
        image = image.crop((left, top, right, bottom))
        image.thumbnail(SIZE, Image.Resampling.LANCZOS)
        self.assertEqual(image.size, SIZE)
        return image

    @staticmethod
    def markup_bounds(image):
        """Return bounds for the highly saturated markup pixels, excluding the neutral scene."""
        pixels = [
            (x, y)
            for y in range(image.height)
            for x in range(image.width)
            if max(image.getpixel((x, y))[:3]) - min(image.getpixel((x, y))[:3]) > 90
            and max(image.getpixel((x, y))[:3]) > 140
        ]
        if not pixels:
            return None
        xs, ys = zip(*pixels)
        return [min(xs), min(ys), max(xs), max(ys), len(pixels)]

    async def capture_frame(self):
        result = None

        def callback(buffer, buffer_size, width, height, _format):
            nonlocal result
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
            result = Image.frombytes("RGBA", (width, height), content.contents)

        capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()
        capture.capture_next_frame_swapchain_callback(callback)
        await self.wait_updates(CAPTURE_UPDATES)
        capture.wait_async_capture()
        self.assertIsNotNone(result)
        return self.thumbnail(result)

    async def capture_fullscreen_control(self):
        """Capture without ever shrinking the viewport: the known-good alignment reference."""
        self.settings.set(TOOL_HIDE, False)
        self.settings.set(UI_HIDE, False)
        self.viewport_window.width, self.viewport_window.height = CAPTURE_VIEWPORT_SIZE
        self.markups.recall_markup(None)
        await self.wait_updates(1)
        self.markups.recall_markup(self.markup)
        await self.wait_updates(5)
        self.settings.set(UI_HIDE, True)
        await self.wait_updates(SETTLE_UPDATES)
        self.settings.set(TOOL_HIDE, True)
        return await self.capture_frame()

    async def capture_thumbnail(self):
        """Capture the way the thumbnail pipeline does: author small, then grow to capture."""
        await self.reset()
        before = self.rect()
        self.markups.end_edit_markup(self.markup, save=True, update_thumbnail=False)
        self.settings.set(UI_HIDE, True)
        self.viewport_window.width, self.viewport_window.height = CAPTURE_VIEWPORT_SIZE
        await self.wait_updates(SETTLE_UPDATES)
        self.settings.set(TOOL_HIDE, True)
        image = await self.capture_frame()

        # Guard: if the viewport rect never changed, the authoring-to-capture
        # resize did not happen and the assertions below would prove nothing.
        self.assertNotEqual(before, self.rect())
        return image

    async def test_thumbnail_alignment_after_viewport_grows(self):
        control = self.markup_bounds(await self.capture_fullscreen_control())
        thumbnail = self.markup_bounds(await self.capture_thumbnail())
        self.assertIsNotNone(control)
        self.assertIsNotNone(thumbnail)

        # The markup must occupy the same box it does in a viewport that was never
        # resized -- that alignment is the whole point of the canvas offset/size
        # bookkeeping. Both captures are fully settled, so any difference here is a
        # real misalignment rather than a stroke that has not finished drawing.
        for edge, expected, actual in zip(("left", "top", "right", "bottom"), control, thumbnail):
            self.assertAlmostEqual(actual, expected, delta=1, msg=f"{edge} edge misaligned")

        # The underlying cause: a grown gesture stack whose computed size never
        # caught up with the size that was requested.
        stack = self.markup_tool._gesture_stack
        self.assertAlmostEqual(stack.computed_width, float(stack.width), delta=0.1)
        self.assertAlmostEqual(stack.computed_height, float(stack.height), delta=0.1)
