# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import carb.settings
import omni.kit.test

from omni.kit.window.movie_capture.render_settings_widget import (
    DEFAULT_RENDER_PRESET_SETTING_PATH,
    RenderModel,
)

RENDERER_ENABLED_PATH = "/renderer/enabled"
PT_MODE_PATH = "/persistent/rtx/modes/pt/enabled"
RT2_MODE_PATH = "/persistent/rtx/modes/rt2/enabled"
MINIMAL_MODE_PATH = "/persistent/rtx/modes/minimal/enabled"


class TestRenderModelEngines(omni.kit.test.AsyncTestCase):
    """Regression tests for OMPE-112504.

    Two defects on the ovrtx runtime renderer:
      1. ``ovrtx`` was not in ``RenderModel.enabled_engines``' supported list, so no preset
         was ever built and capture failed with "no render preset selected".
      2. ``default_render_preset`` named a mode ovrtx does not have (``RaytracedLighting``),
         so it silently fell back to the active render -- indistinguishable from unset.

    The engine is forced via ``/renderer/enabled`` so these run identically on an rtx host
    and an ovrtx host.
    """

    async def setUp(self) -> None:
        super().setUp()
        self._settings = carb.settings.get_settings()
        self._saved = {
            path: self._settings.get(path)
            for path in (
                RENDERER_ENABLED_PATH,
                DEFAULT_RENDER_PRESET_SETTING_PATH,
                PT_MODE_PATH,
                RT2_MODE_PATH,
                MINIMAL_MODE_PATH,
            )
        }
        self._models = []
        # Keep the preset list to the two ovrtx modes; "Minimal" is an independent
        # opt-in that would otherwise vary by host.
        self._settings.set(MINIMAL_MODE_PATH, False)

    async def tearDown(self) -> None:
        # Models subscribe to carb.settings; a leaked observer outlives the test.
        for model in self._models:
            model.destroy()
        self._models = []
        for path, value in self._saved.items():
            if value is None:
                continue
            self._settings.set(path, value)
        super().tearDown()

    def _build_model(self, engine: str, default_preset: str) -> RenderModel:
        # Settings must be in place before construction: RenderModel reads them in __init__.
        self._settings.set(RENDERER_ENABLED_PATH, engine)
        self._settings.set(DEFAULT_RENDER_PRESET_SETTING_PATH, default_preset)
        model = RenderModel(None, lambda render_info: None)
        self._models.append(model)
        return model

    async def test_ovrtx_engine_yields_presets(self):
        """Finding 1: ovrtx was filtered out entirely, leaving an empty dropdown."""
        model = self._build_model("ovrtx", "")

        self.assertIn("ovrtx", model.enabled_engines)
        modes = [render.mode for render in model._renders]
        self.assertTrue(modes, msg="No render preset built for ovrtx (OMPE-112504 finding 1).")
        self.assertIn("PathTracing", modes)
        self.assertIn("RealTimePathTracing", modes)
        # ovrtx has no raster+RT "Real-Time" equivalent, so this mode must not be offered.
        self.assertNotIn("RaytracedLighting", modes)
        self.assertIsNotNone(model.selected_render)

    async def test_rtx_engine_still_yields_raytraced_lighting(self):
        """The ovrtx branch must not disturb the classic rtx preset list."""
        model = self._build_model("rtx", "")

        self.assertIn("rtx", model.enabled_engines)
        self.assertIn("RaytracedLighting", [render.mode for render in model._renders])

    async def test_default_preset_list_skips_unavailable_mode(self):
        """Finding 2: the first available mode in the list wins.

        ``PathTracing`` is the discriminator -- it is not the active render, so landing on
        it can only happen by resolving the list, never by the fallback the bug exhibited.
        """
        model = self._build_model("ovrtx", "RaytracedLighting, PathTracing")

        self.assertEqual(model.selected_render.mode, "PathTracing")

    async def test_default_preset_tolerates_whitespace_and_empty_entries(self):
        model = self._build_model("ovrtx", " , RaytracedLighting ,, PathTracing , ")

        self.assertEqual(model.selected_render.mode, "PathTracing")

    async def test_unavailable_single_mode_falls_back_to_active(self):
        """The pre-fix shipped default. It cannot resolve on ovrtx, so it must fall back
        rather than leave the selection empty."""
        model = self._build_model("ovrtx", "RaytracedLighting")

        self.assertIsNotNone(model.selected_render)
        self.assertNotEqual(model.selected_render.mode, "RaytracedLighting")
        self.assertEqual(model.selected_render, model._active_render)

    async def test_set_render_mode_accepts_a_list(self):
        """set_render_mode is the public entry point and takes the same syntax as the
        setting, so a value copied from one to the other cannot fail."""
        model = self._build_model("ovrtx", "")

        self.assertTrue(model.set_render_mode("RaytracedLighting, PathTracing"))
        self.assertEqual(model.selected_render.mode, "PathTracing")

    async def test_set_render_mode_rejects_only_unavailable_modes(self):
        model = self._build_model("ovrtx", "")

        self.assertFalse(model.set_render_mode("RaytracedLighting"))
        self.assertFalse(model.set_render_mode(""))
