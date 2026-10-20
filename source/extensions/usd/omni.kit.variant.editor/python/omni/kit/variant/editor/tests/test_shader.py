import os
from unittest.mock import patch

import carb
import omni.client
import omni.kit.commands
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui
import omni.usd
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, Sdf, Tf, Usd, UsdShade, Vt

from ..core import VariantEditorCore
from ..extension import get_window
from .test_cleanup import reset_variant_editor_test_state

WINDOW_SIZE = 1024


class TestShaderWidget(OmniUiTest):
    async def setUp(self):
        await super().setUp()
        from omni.kit.variant.editor.extension import TEST_DATA_PATH

        self._usd_path = TEST_DATA_PATH.absolute()
        self._core = VariantEditorCore.get_instance()

    async def tearDown(self):
        await reset_variant_editor_test_state()
        await super().tearDown()

    async def bootstrap_stage(self, stage_path):
        test_file_path = self._usd_path.joinpath(stage_path).absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))
        await omni.kit.app.get_app().next_update_async()

    async def open_variant_window(self):
        get_window().show()
        for _ in range(30):
            await omni.kit.app.get_app().next_update_async()
        return get_window()

    async def _setup_test_prim(self, stage):
        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant'")
        self.assertIsNotNone(variant_widget)
        await variant_widget.click()
        for _ in range(6):
            await omni.kit.app.get_app().next_update_async()
        vsets_api = stage.GetPrimAtPath(Sdf.Path("/Looks")).GetVariantSets()
        self.assertEqual("Variant", vsets_api.GetVariantSelection("Variant_Set"))

        add_prim_widget = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Prim'")
        self.assertIsNotNone(add_prim_widget)
        await add_prim_widget.click()
        for _ in range(6):
            await omni.kit.app.get_app().next_update_async()

        shader_prim_item = ui_test.find(
            "Select Prims//Frame/**/ScrollingFrame[0]/ZStack[0]/TreeView[0]/Frame[4]/**/Label[0].text=='Shader'"
        )
        self.assertIsNotNone(shader_prim_item)
        await shader_prim_item.click()
        await omni.kit.app.get_app().next_update_async()

    async def _test_widget_custom_name_case(self, property_name):
        await self.bootstrap_stage("test_shader.usda")
        stage: Usd.Stage = self._core._stage

        window = await self.open_variant_window()
        window._on_prim_picked(["/Looks"])

        await self._setup_test_prim(stage)

        add_prim_widget = ui_test.find("Select Prims//Frame/**/Button[*].text=='Select'")
        await add_prim_widget.click()

        add_property_widget = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Property'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        path = Sdf.Path("/Looks/OmniPBR/Shader").AppendProperty(property_name)
        sdf_prop: Sdf.PropertySpec = stage.GetRootLayer().GetPropertyAtPath(path)
        display_name = sdf_prop.GetInfo(Sdf.PropertySpec.DisplayNameKey)

        search_properties_widget = ui_test.find("Select Properties//Frame/**/StringField[*]")
        self.assertIsNotNone(search_properties_widget)
        await search_properties_widget.click()
        await ui_test.emulate_char_press(display_name)
        await omni.kit.app.get_app().next_update_async()

        item_widget = ui_test.find(f"Select Properties//Frame/**/Label[*].text=='{display_name}'")
        self.assertIsNotNone(item_widget)
        await item_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        add_property_widget = ui_test.find("Select Properties//Frame/**/Button[*].text=='Add'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        property_watch_button = ui_test.find("Variant Editor//Frame/**/PropertyWatchButton[*]")
        self.assertIsNotNone(property_watch_button)

        label_widget = ui_test.find(f"Variant Editor//Frame/**/Label[*].text=='{display_name}'")
        self.assertIsNotNone(label_widget)

        prim_path = Sdf.Path("/Looks").AppendVariantSelection("Variant_Set", "Variant").AppendPath("OmniPBR/Shader")
        sdf_prim: Sdf.VariantSpec = stage.GetRootLayer().GetObjectAtPath(prim_path)
        self.assertIsNotNone(sdf_prim)
        sdf_prop: Sdf.PropertySpec = sdf_prim.GetPropertyAtPath(f".{property_name}")
        self.assertIsNotNone(sdf_prop)
        self.assertEqual(display_name, sdf_prop.GetInfo(Sdf.PropertySpec.DisplayNameKey))

        window.hide()

    async def test_shader_widget_albedo_add(self):
        await self._test_widget_custom_name_case("inputs:albedo_add")

    async def test_shader_widget_opacity_texture(self):
        await self._test_widget_custom_name_case("inputs:opacity_texture")

    async def test_shader_widget_opacity_mode(self):
        await self._test_widget_custom_name_case("inputs:opacity_mode")

    async def test_shader_widget_texture_rotate(self):
        await self._test_widget_custom_name_case("inputs:texture_rotate")

    async def test_shader_widget_source_asset(self):
        await self.bootstrap_stage("test_shader.usda")
        stage: Usd.Stage = self._core._stage

        window = await self.open_variant_window()
        window._on_prim_picked(["/Looks"])

        await self._setup_test_prim(stage)

        add_prim_widget = ui_test.find("Select Prims//Frame/**/Button[*].text=='Select'")
        await add_prim_widget.click()

        add_property_widget = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Property'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        CUSTOM_PROPERTY_NAME = "MDL Source Asset/SubID"
        search_properties_widget = ui_test.find("Select Properties//Frame/**/StringField[*]")
        self.assertIsNotNone(search_properties_widget)
        await search_properties_widget.click()
        await ui_test.emulate_char_press(CUSTOM_PROPERTY_NAME)
        await omni.kit.app.get_app().next_update_async()

        item_widget = ui_test.find(f"Select Properties//Frame/**/Label[*].text=='{CUSTOM_PROPERTY_NAME}'")
        self.assertIsNotNone(item_widget)
        await item_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        add_property_widget = ui_test.find("Select Properties//Frame/**/Button[*].text=='Add'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        local_opinion_buttons_path = "Variant Editor//Frame/**/TreeView[*]/HStack[*]/**/PropertyWatchButton[*]"
        self.assertEquals(len(ui_test.find_all(local_opinion_buttons_path)), 2)
        for index in range(2):
            # Each toggle rebuilds the tree, so re-query rather than reusing the refs
            # collected before the first click.
            local_opinion_buttons = ui_test.find_all(local_opinion_buttons_path)
            self.assertEquals(len(local_opinion_buttons), 2)
            await local_opinion_buttons[index].click()
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()

        sourceasset_widget = ui_test.find("Variant Editor//Frame/**/sdf_asset_info:mdl:sourceAsset")
        sourceasset_widget.model.set_value("OmniHair.mdl")

        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        prim_path = Sdf.Path("/Looks").AppendVariantSelection("Variant_Set", "Variant").AppendPath("OmniPBR/Shader")
        sdf_prim: Sdf.VariantSpec = stage.GetRootLayer().GetObjectAtPath(prim_path)
        self.assertIsNotNone(sdf_prim)

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        src_asset_attr: Sdf.AttributeSpec = sdf_prim.GetAttributeAtPath(f".info:mdl:sourceAsset")
        self.assertIsNotNone(src_asset_attr)
        self.assertIn("OmniHair", src_asset_attr.GetAsText())

        sub_ident_attr: Sdf.AttributeSpec = sdf_prim.GetAttributeAtPath(f".info:mdl:sourceAsset:subIdentifier")
        self.assertIsNotNone(sub_ident_attr)

        window.hide()
