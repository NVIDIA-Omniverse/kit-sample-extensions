## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import carb
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.ui.tests.test_base import OmniUiTest


class TestKitFile(OmniUiTest):
    # Before running each test
    async def setUp(self):
        omni.kit.window.preferences.show_preferences_window()

    # After running each test
    async def tearDown(self):
        omni.kit.window.preferences.hide_preferences_window()

    async def test_kitfile(self):
        self.assertEqual(omni.kit.language.core.get_locale_id(), "te_ST")
        info = omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id())
        expected_info = {
            "language_name": "Test1",
            "language_name_localized": "Test2",
            "pangram": "My hovercraft is full of eels",
            "font_path": "TestFont.ttf",
            "font_scale": 1.0,
            "regions": ("regions_test.txt",),
            "font_overresolution_size": 66,
        }
        self.assertEqual(info, expected_info)
