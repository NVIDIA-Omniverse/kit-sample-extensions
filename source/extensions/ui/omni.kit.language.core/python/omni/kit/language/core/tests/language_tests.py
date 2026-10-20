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


class TestLanguageAPI(OmniUiTest):
    # Before running each test
    async def setUp(self):
        omni.kit.window.preferences.show_preferences_window()

    # After running each test
    async def tearDown(self):
        omni.kit.window.preferences.hide_preferences_window()

    async def test_language_api(self):
        # verify language te_ST is unknown
        info = omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id())
        self.assertEqual(info, None)

        pages = omni.kit.window.preferences.get_page_list()
        for page in pages:
            if page.get_title() == "Language":
                omni.kit.window.preferences.select_page(page)
                await ui_test.human_delay(50)

        # bad calls
        result = omni.kit.language.core.register_language(None, None, None, None, None)
        self.assertFalse(result)
        info = omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id())
        self.assertEqual(info, None)
        result = omni.kit.language.core.register_language(("te_ST", "Test1", "Test2"), None, None, None, None)
        self.assertTrue(result)
        info = omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id())
        self.assertEqual(
            info,
            {
                "language_name": "Test1",
                "language_name_localized": "Test2",
                "pangram": None,
                "font_path": None,
                "font_scale": None,
                "regions": None,
                "font_overresolution_size": None,
            },
        )

        await ui_test.human_delay(10)
        omni.kit.window.preferences.rebuild_pages()
        await ui_test.human_delay(10)
        omni.kit.language.core.unregister_language("te_ST")

        # valid
        result = omni.kit.language.core.register_language(
            ("te_ST", "Test1", "Test2"),
            f"TestFont.ttf",
            1.0,
            ["regions_test1.txt", "regions_test2.txt", "regions_test3.txt"],
            "My hovercraft is full of eels",
            font_overresolution_size=66,
        )
        self.assertTrue(result)

        info = omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id())
        expected_info = {
            "language_name": "Test1",
            "language_name_localized": "Test2",
            "pangram": "My hovercraft is full of eels",
            "font_path": "TestFont.ttf",
            "font_scale": 1.0,
            "regions": ["regions_test1.txt", "regions_test2.txt", "regions_test3.txt"],
            "font_overresolution_size": 66,
        }
        self.assertEqual(info, expected_info)

        # show preferences
        await ui_test.human_delay(10)
        omni.kit.window.preferences.rebuild_pages()
        await ui_test.human_delay(10)

        # register an already used language
        result = omni.kit.language.core.register_language(
            ("te_ST", "Test1", "Test2"),
            f"TestFont.ttf",
            1.0,
            ["regions_test1.txt", "regions_test2.txt", "regions_test3.txt"],
            "My hovercraft is full of eels",
        )
        self.assertFalse(result)

        self.assertTrue(omni.kit.language.core.unregister_language("te_ST"))
        self.assertFalse(omni.kit.language.core.unregister_language("che_ESE"))

        await ui_test.human_delay(10)
        omni.kit.window.preferences.rebuild_pages()

        # verify language te_ST is unknown
        self.assertEqual(omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id()), None)

    async def test_language_ui(self):
        # verify language te_ST is unknown
        self.assertEqual(omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id()), None)

        pages = omni.kit.window.preferences.get_page_list()

        for page in pages:
            if page.get_title() == "Language":
                omni.kit.window.preferences.select_page(page)
                await ui_test.human_delay(50)

        result = omni.kit.language.core.register_language(
            ("te_ST", "Test", "Test"), None, 1.0, None, "My hovercraft is full of eels"
        )
        self.assertTrue(result)

        result = omni.kit.language.core.register_language(
            ("en_UK", "Test", "Test"), None, 1.0, None, "My hovercraft is full of eels"
        )
        self.assertTrue(result)

        await ui_test.human_delay(10)
        omni.kit.window.preferences.rebuild_pages()
        await ui_test.human_delay(10)

        combo_box = ui_test.find("Preferences//Frame/**/ComboBox[*]")
        lang_list = combo_box.model.get_item_children()
        for index, item in enumerate(lang_list):
            combo_box.model.set_value(item)
            await ui_test.human_delay(10)

        # locale_id could be on en_US which is the default, so switch back to te_ST
        carb.settings.get_settings().set("/persistent/app/locale_id", "te_ST")

        self.assertTrue(omni.kit.language.core.unregister_language("te_ST"))
        self.assertTrue(omni.kit.language.core.unregister_language("en_UK"))
        self.assertFalse(omni.kit.language.core.unregister_language("che_ESE"))
        await ui_test.human_delay(10)
        omni.kit.window.preferences.rebuild_pages()

        # verify language te_ST is unknown
        self.assertEqual(omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id()), None)
