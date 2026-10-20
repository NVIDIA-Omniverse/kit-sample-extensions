# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb
import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd
from omni.ui.tests.test_base import OmniUiTest

from ..extension import TEST_DATA_PATH, get_window
from .test_cleanup import reset_variant_editor_test_state

WINDOW_SIZE = 1024

LAYER_PATH_FIELD = "Variant Editor//Frame/**/StringField[*].name=='layer_path'"


async def string_field_confirmed_input(widget, input: str):
    # there seems to some bug in ui.StringField.input(). It does not always change as expected.
    # here is the workaround by experience.
    count = 100
    while True:
        await ui_test.human_delay(10)
        await widget.input(input)

        if widget.model.get_value_as_string() == input:
            break

        count -= 1
        if count == 0:
            carb.log_error("Unexpected code path for string_field_confirmed_input()")
            break

    # do not delay too long otherwise the tooltip may pop out
    await ui_test.human_delay(10)


async def file_picker_confirmed_input(widget, input: str):
    # like string_field_confirmed_input, overcome uncertain behavior of StringField by trying again and again
    count = 100
    while True:
        # emulate input the data file in the StringField
        dir_widget = ui_test.find("Select Reference//Frame/**/StringField[*].identifier=='filepicker_directory_path'")
        test_usda_dir = TEST_DATA_PATH
        await dir_widget.input(str(test_usda_dir) + "/" + input)
        await ui_test.human_delay(10)

        # In some circumstances, dir_widget.input() appears to not commit the file path.  This provides a backup
        select_button = ui_test.find("Select Reference//Frame/**/Button[*].text=='Select'")
        if select_button:
            await select_button.click()

        remove_widgets = ui_test.find_all("Variant Editor//Frame/**/Button[*].identifier=='Variant Remove PayRef'")
        if len(remove_widgets) == 2:
            # The Asset path is absolute and can not compare image directly.
            # as a workaround, check there are 2 payref items to remove
            break

        count -= 1
        if count == 0:
            carb.log_error("Unexpected code path for file_picker_confirmed_input()")
            break


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test


class UITestPayRef(OmniUiTest):
    # SET-UP AND UTILITY
    async def setUp(self):
        self._usd_path = TEST_DATA_PATH.absolute()

    async def tearDown(self):
        await reset_variant_editor_test_state()
        await super().tearDown()

    async def bootstrap_stage(self, stage_path):
        test_file_path = self._usd_path.joinpath(stage_path).absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))
        await omni.kit.app.get_app().next_update_async()

    # TESTS

    async def test_payload_widget(self):
        # do some preparation like in the beginning of test_variant_tree()
        await self.bootstrap_stage("test_payload.usda")
        get_window().hide()
        get_window().show()
        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )
        await ui_test.human_delay(10)

        # Select variant
        await ui_test.human_delay(10)
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant'")
        await variant_widget.click()
        await ui_test.human_delay(10)

        # verify the payloads UI is expanded
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "./test_be_used.usda")

        # Edit the <Asset Path>
        asset_path_widget.model.set_value("./do_not_exist.usda")
        await ui_test.human_delay(10)
        # Setting the value rebuilds the payload UI, so re-query instead of reading
        # back through the now-stale widget.
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "./do_not_exist.usda")

        # Remove the variant payload
        remove_widget = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Remove PayRef'")
        await remove_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertFalse(asset_path_widget)

        # Select variant
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant_1'")
        await variant_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "")

        prim_path_widget = ui_test.find("Variant Editor//Frame/**/StringField[*].identifier=='payref_prim_path'")
        self.assertTrue(prim_path_widget)
        self.assertEqual(prim_path_widget.model.get_value_as_string(), "/World")

        # Add payload from existing variant payload widget
        add_widget = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Add Payload'")
        await add_widget.click()
        await ui_test.human_delay(10)
        await file_picker_confirmed_input(add_widget, "test_reference.usda")

        # Remove all the variant payloads
        remove_widget = ui_test.find("Variant Editor//Frame/**/VStack[*].identifier=='remove_prop_widget vstack'")
        await remove_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertFalse(asset_path_widget)

    async def test_reference_widget(self):
        # do some preparation like in the beginning of test_variant_tree()
        await self.bootstrap_stage("test_reference.usda")
        get_window().hide()
        get_window().show()
        await self.docked_test_window(
            window=get_window()._window,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            block_devices=False,
        )
        await ui_test.human_delay(10)

        # Select variant
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant'")
        await variant_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "./test_be_used.usda")

        # Edit the <Asset Path>
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        asset_path_widget.model.set_value("./do_not_exist.usda")
        await ui_test.human_delay(10)
        # Setting the value rebuilds the reference UI, so re-query instead of reading
        # back through the now-stale widget.
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "./do_not_exist.usda")

        # Remove the variant reference
        remove_widget = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Remove PayRef'")
        await remove_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertFalse(asset_path_widget)

        # Select variant
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant_1'")
        await variant_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertEqual(asset_path_widget.model.get_value_as_string(), "")

        # Add reference from existing variant reference widget
        add_widget = ui_test.find("Variant Editor//Frame/**/Button[*].identifier=='Variant Add Reference'")
        await add_widget.click()
        await ui_test.human_delay(10)
        await file_picker_confirmed_input(add_widget, "test_payload.usda")

        # Remove all the variant references
        remove_widget = ui_test.find("Variant Editor//Frame/**/VStack[*].identifier=='remove_prop_widget vstack'")
        await remove_widget.click()
        await ui_test.human_delay(10)
        asset_path_widget = ui_test.find(LAYER_PATH_FIELD)
        self.assertFalse(asset_path_widget)

        # todo, add a reference from the Add Property button.
