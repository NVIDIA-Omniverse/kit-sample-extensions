# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import carb.settings
import omni.kit.app
import omni.kit.test
from omni.kit.actions.core import get_action_registry

EXT = "omni.kit.viewport.menubar.framerate"
CURRENT = f"/exts/{EXT}/currentPreset"
SHOW_DLSSG = f"/exts/{EXT}/showDLSSG"


class TestCyclePresets(omni.kit.test.AsyncTestCase):
    """The "cycle frame-pacing presets" action (SHIFT+ALT+P) ends whatever the current preset is."""

    async def setUp(self):
        try:
            import omni.kit.window.preferences.scripts.pages.developer_page as presets_module
        except ImportError:
            import omni.kit.window.preferences.scripts.pages.rendering_page as presets_module
        self._settings = carb.settings.get_settings()
        # Applying a preset writes run-loop settings: restore every key a preset can write, and the menu's own.
        keys = {key for _, values in getattr(presets_module, "THREAD_SYNC_PRESETS", []) for key in values}
        self._saved = {key: self._settings.get(key) for key in keys | {CURRENT, SHOW_DLSSG}}
        self._action = get_action_registry().get_action(EXT, "FramePacingCyclePresets")
        self.assertIsNotNone(self._action)
        # Without the DLSS-G "x2" presets the menu offers "No Pacing" and "60" on any GPU.
        self._settings.set(SHOW_DLSSG, False)
        await self._updates()

    async def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                self._settings.destroy_item(key)
            else:
                self._settings.set(key, value)
        await self._updates()

    async def _updates(self, n: int = 3):
        for _ in range(n):
            await omni.kit.app.get_app().next_update_async()

    async def _cycle_from(self, current: str) -> str:
        self._settings.set(CURRENT, current)
        await self._updates(1)
        self._action.execute()
        await self._updates(1)
        return self._settings.get(CURRENT)

    async def test_cycle_wraps_through_offered_presets(self):
        self.assertEqual(await self._cycle_from("No Pacing"), "60")
        self.assertEqual(await self._cycle_from("60"), "No Pacing")

    async def test_cycle_from_preset_not_offered_goes_to_nearest_rate(self):
        # QA's freeze: "60x2" (DLSS-G) current without DLSS-G presets. Its render rate is 60.
        self.assertEqual(await self._cycle_from("60x2"), "60")

    async def test_cycle_from_custom_or_empty_goes_to_first(self):
        self.assertEqual(await self._cycle_from("Custom"), "No Pacing")
        self.assertEqual(await self._cycle_from(""), "No Pacing")
