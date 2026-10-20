from unittest.mock import patch

import carb
import omni.kit.app
import omni.kit.language.core
import omni.kit.test
from omni.kit.language.core.scripts.language import LanguageExtension
from omni.kit.language.simplified_chinese.scripts.simplified_chinese import (
    SimplifiedChineseLanguageExtension,
)

_SETTING = "/exts/omni.kit.language.simplified_chinese/use_common_chinese"
_FONT_REGIONS_SETTING = "/app/font/customRegionFiles"
_LOCALE = "zh-CN"
_INACTIVE_LOCALE = "en_TEST"
_EXT_ID = "omni.kit.language.simplified_chinese"


def _basename(path):
    return path.replace("\\", "/").rsplit("/", 1)[-1]


class TestSimplifiedChineseRegionSelection(omni.kit.test.AsyncTestCase):
    """OMPE-101379: on_startup must honor use_common_chinese and default to the bounded set."""

    async def setUp(self):
        self._settings = carb.settings.get_settings()
        self._saved_setting = self._settings.get(_SETTING)
        self._saved_font_regions = list(self._settings.get(_FONT_REGIONS_SETTING) or [])
        # Keep zh-CN inactive while re-registering it so switch_language does not append font regions.
        self._locale_patch = patch.object(LanguageExtension, "get_locale_id", return_value=_INACTIVE_LOCALE)
        self._locale_patch.start()

    async def tearDown(self):
        try:
            if self._saved_setting is None:
                self._settings.destroy_item(_SETTING)
            else:
                self._settings.set(_SETTING, self._saved_setting)
            # Re-register zh-CN so other tests in the suite still see the registered language.
            omni.kit.language.core.unregister_language(_LOCALE)
            SimplifiedChineseLanguageExtension().on_startup(_EXT_ID)
        finally:
            self._locale_patch.stop()

    def _selected_region_files(self, use_common_chinese):
        if use_common_chinese is None:
            self._settings.destroy_item(_SETTING)
        else:
            self._settings.set(_SETTING, use_common_chinese)
        omni.kit.language.core.unregister_language(_LOCALE)
        SimplifiedChineseLanguageExtension().on_startup(_EXT_ID)
        self.assertEqual(
            list(self._settings.get(_FONT_REGIONS_SETTING) or []),
            self._saved_font_regions,
            "region selection must not mutate the active font region files",
        )
        info = omni.kit.language.core.get_language_info(_LOCALE)
        self.assertIsNotNone(info, "zh-CN language was not registered by on_startup")
        return [_basename(r) for r in info["regions"]]

    async def test_use_common_chinese_setting_selects_bounded_region_set(self):
        names = self._selected_region_files(True)
        self.assertEqual(len(names), 9, f"expected 9 region files, got {names}")
        self.assertTrue(
            all(n.startswith("Common_Chinese") for n in names),
            f"use_common_chinese=True must select the bounded Common_Chinese region set, got {names}",
        )

    async def test_default_does_not_select_unbounded_full_region_set(self):
        names = self._selected_region_files(None)
        self.assertEqual(len(names), 9, f"expected 9 region files, got {names}")
        self.assertTrue(
            all(n.startswith("Common_Chinese") for n in names),
            "default (setting unset) must select the bounded Common_Chinese region set so the "
            f"font atlas stays within the D3D12 16384px limit, got {names}",
        )

    async def test_full_region_set_only_when_explicitly_opted_out(self):
        names = self._selected_region_files(False)
        self.assertEqual(len(names), 9, f"expected 9 region files, got {names}")
        self.assertTrue(
            all(n.startswith("Chinese") for n in names),
            f"use_common_chinese=False must select the full Chinese region set, got {names}",
        )
