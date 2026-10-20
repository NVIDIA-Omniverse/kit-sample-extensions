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


class TestMaterialWidget(OmniUiTest):
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
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()
        return get_window()

    async def test_material_widget(self):
        await self.bootstrap_stage("test_material.usda")
        stage: Usd.Stage = self._core._stage

        window = await self.open_variant_window()

        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant'")
        self.assertIsNotNone(variant_widget)
        await variant_widget.click()
        for _ in range(6):
            await omni.kit.app.get_app().next_update_async()
        vsets_api = stage.GetPrimAtPath(Sdf.Path("/World")).GetVariantSets()
        self.assertEqual("Variant", vsets_api.GetVariantSelection("Variant_Set"))

        add_prim_widget = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Prim'")
        self.assertIsNotNone(add_prim_widget)
        await add_prim_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        cube_prim_item = ui_test.find("Select Prims//Frame/**/Label[*].text=='Cube'")
        self.assertIsNotNone(cube_prim_item)
        await cube_prim_item.click()
        await omni.kit.app.get_app().next_update_async()

        add_prim_widget = ui_test.find("Select Prims//Frame/**/Button[*].text=='Select'")
        await add_prim_widget.click()

        add_property_widget = ui_test.find("Variant Editor//Frame/**/Button[*].text=='Add Property'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        search_properties_widget = ui_test.find("Select Properties//Frame/**/StringField[*]")
        self.assertIsNotNone(search_properties_widget)
        await search_properties_widget.click()
        await ui_test.emulate_char_press("material:binding")
        await omni.kit.app.get_app().next_update_async()

        item_widget = ui_test.find("Select Properties//Frame/**/Label[*].text=='material:binding'")
        self.assertIsNotNone(item_widget)
        await item_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        add_property_widget = ui_test.find("Select Properties//Frame/**/Button[*].text=='Add'")
        self.assertIsNotNone(add_property_widget)
        await add_property_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        strength_label_widget = ui_test.find(
            "Variant Editor//Frame/**/ScrollingFrame[0]/TreeView[0]/**/Label[0].text=='Strength'"
        )
        self.assertIsNotNone(strength_label_widget)
        strength_combobox_widget = ui_test.find("Variant Editor//Frame/**/ScrollingFrame[0]/TreeView[0]/**/ComboBox[*]")
        self.assertIsNotNone(strength_combobox_widget)
        options = strength_combobox_widget.model.get_item_children(None)
        self.assertEqual(2, len(options))
        self.assertEqual(
            "Weaker than Descendants",
            strength_combobox_widget.model.get_item_value_model(options[0]).get_value_as_string(),
        )
        self.assertEqual(
            "Stronger than Descendants",
            strength_combobox_widget.model.get_item_value_model(options[1]).get_value_as_string(),
        )

        property_watch_button = ui_test.find("Variant Editor//Frame/**/PropertyWatchButton[*]")
        self.assertIsNotNone(property_watch_button)
        await property_watch_button.click()
        await omni.kit.app.get_app().next_update_async()

        material_combo_widget = ui_test.find("Variant Editor//Frame/**/combo_drop_target")
        self.assertIsNotNone(material_combo_widget)
        self.assertEqual("/World/Looks/OmniPBR", material_combo_widget.model.get_value_as_string())

        # The property watch toggle above rebuilt the tree, so re-query the combo box.
        strength_combobox_widget = ui_test.find("Variant Editor//Frame/**/ScrollingFrame[0]/TreeView[0]/**/ComboBox[*]")
        self.assertIsNotNone(strength_combobox_widget)
        strength_combobox_widget.model.get_item_value_model(None).set_value(1)

        prim_path = Sdf.Path("/World").AppendVariantSelection("Variant_Set", "Variant").AppendPath("Cube")
        sdf_prim: Sdf.VariantSpec = stage.GetRootLayer().GetObjectAtPath(prim_path)
        self.assertIsNotNone(sdf_prim)
        mat_binding: Sdf.RelationshipSpec = sdf_prim.GetRelationshipAtPath(".material:binding")
        self.assertIsNotNone(mat_binding)
        self.assertEqual(
            UsdShade.Tokens.strongerThanDescendants,
            mat_binding.GetInfo("bindMaterialAs"),
        )

        # Setting the strength above rebuilt the tree. Re-query, and capture the centre
        # now because clicking turns the drop target into an edit field.
        material_combo_widget = ui_test.find("Variant Editor//Frame/**/combo_drop_target")
        self.assertIsNotNone(material_combo_widget)
        material_combo_pos = material_combo_widget.center
        await material_combo_widget.click()
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        await ui_test.emulate_char_press("/World/Looks/OmniPBRTest")
        await ui_test.emulate_mouse_move_and_click(material_combo_pos + ui_test.Vec2(0, 45))
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(1, len(mat_binding.targetPathList.explicitItems))
        self.assertEqual("/World/Looks/OmniPBRTest", mat_binding.targetPathList.explicitItems[0])

        window.hide()

    async def test_material_inherited(self):
        await self.bootstrap_stage("test_material_inherited.usda")
        stage: Usd.Stage = self._core._stage

        window = await self.open_variant_window()

        variant_widget = ui_test.find("Variant Editor//Frame/**/Label[*].text=='Variant'")
        self.assertIsNotNone(variant_widget)
        await variant_widget.click()
        await omni.kit.app.get_app().next_update_async()
        vsets_api = stage.GetPrimAtPath(Sdf.Path("/World")).GetVariantSets()
        self.assertEqual("Variant", vsets_api.GetVariantSelection("Variant_Set"))

        material_combo_widget = ui_test.find("Variant Editor//Frame/**/combo_drop_target")
        self.assertIsNotNone(material_combo_widget)
        self.assertEqual(
            "/World/Looks/OmniPBR (inherited)",
            material_combo_widget.model.get_value_as_string(),
        )

        window.hide()
