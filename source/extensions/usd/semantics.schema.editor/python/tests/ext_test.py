import os
from pathlib import Path

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
import omni.kit.test
import omni.usd

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
import semantics.schema.editor
from pxr import Sdf, Semantics, Usd, UsdPhysics, UsdSemantics
from semantics.schema.editor import (
    LabelWriteType,
    PrimSemanticData,
    add_prim_semantics,
    clear_semantics,
    upgrade_prim_semantics,
    upgrade_stage_semantics,
)

TEST_DATA_DIR = Path(os.path.dirname(os.path.realpath(__file__))).joinpath("data")


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class TestSemanticsEditor(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()

    # After running each test
    async def tearDown(self):
        pass

    # Actual test, notice it is "async" function, so "await" can be used if needed
    async def test_single_old_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        sem = Semantics.SemanticsAPI.Apply(prim, "Semantics")
        typeAttr = sem.CreateSemanticTypeAttr()
        dataAttr = sem.CreateSemanticDataAttr()
        typeAttr.Set("semantic_type")
        dataAttr.Set("semantic_label")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 0, "There should be no SemanticsLabelsAPI entries!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 1)
        data = current_data[0]

        self.assertEqual(data["name"], "Semantics")
        self.assertEqual(data["type"], "semantic_type")
        self.assertEqual(data["data"], "semantic_label")
        self.assertEqual(data["ui_hide"], False)
        self.assertEqual(data["api"], "SemanticsAPI")

    async def test_single_new_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        prim.AddAppliedSchema("SemanticsLabelsAPI:semantics")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        labelsAttr = sem.CreateLabelsAttr()
        labelsAttr.Set(["label"])

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 0, "There should be no SemanticsAPI entries!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 1)
        data = current_data[0]

        self.assertEqual(data["name"], "semantics")
        self.assertEqual(data["labels"], ["label"])
        self.assertEqual(data["ui_hide"], False)
        self.assertEqual(data["api"], "SemanticsLabelsAPI")

    async def test_multiple_old_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        sem1 = Semantics.SemanticsAPI.Apply(prim, "Semantics0")
        typeAttr = sem1.CreateSemanticTypeAttr()
        dataAttr = sem1.CreateSemanticDataAttr()
        typeAttr.Set("semantic_type")
        dataAttr.Set("semantic_label")

        sem2 = Semantics.SemanticsAPI.Apply(prim, "Semantics1")
        typeAttr = sem2.CreateSemanticTypeAttr()
        dataAttr = sem2.CreateSemanticDataAttr()
        typeAttr.Set("semantic_type")
        dataAttr.Set("semantic_label")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 0, "There should be no SemanticsLabelsAPI entries!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 2)
        for i in range(len(current_data)):
            data = current_data[i]
            self.assertEqual(data["name"], "Semantics" + str(i))
            self.assertEqual(data["type"], "semantic_type")
            self.assertEqual(data["data"], "semantic_label")
            self.assertEqual(data["ui_hide"], False)

    async def test_multiple_new_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        prim.AddAppliedSchema("SemanticsLabelsAPI:class")
        prim.AddAppliedSchema("SemanticsLabelsAPI:subclass")
        prim.AddAppliedSchema("SemanticsLabelsAPI:category")

        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")
        sem_category = UsdSemantics.LabelsAPI(prim, "category")

        sem_class.GetLabelsAttr().Set(["test_class"])
        sem_subclass.GetLabelsAttr().Set(["sub_class1", "sub_class2"])
        sem_category.GetLabelsAttr().Set(["test_category1", "test_category2"])

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 0, "There should be no SemanticsAPI entries!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 3)
        data = current_data[0]
        self.assertEqual(data["name"], "class")
        self.assertEqual(data["labels"], ["test_class"])
        self.assertEqual(data["ui_hide"], False)
        self.assertEqual(data["api"], "SemanticsLabelsAPI")

        data = current_data[1]
        self.assertEqual(data["name"], "subclass")
        self.assertEqual(data["labels"], ["sub_class1", "sub_class2"])
        self.assertEqual(data["ui_hide"], False)
        self.assertEqual(data["api"], "SemanticsLabelsAPI")

        data = current_data[2]
        self.assertEqual(data["name"], "category")
        self.assertEqual(data["labels"], ["test_category1", "test_category2"])
        self.assertEqual(data["ui_hide"], False)
        self.assertEqual(data["api"], "SemanticsLabelsAPI")

    async def test_invalid_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        prim.CreateAttribute("semantic", Sdf.ValueTypeNames.Double, False).Set(1.0)
        prim.CreateAttribute("semanticSomething", Sdf.ValueTypeNames.Double, False).Set(1.0)
        prim.CreateAttribute("semantic:Something", Sdf.ValueTypeNames.Double, False).Set(1.0)
        prim.CreateAttribute("something:semantic", Sdf.ValueTypeNames.Double, False).Set(1.0)
        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 0, "There should be no SemanticsAPI entries for invalid data!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 0, "There should be no SemanticsLabelsAPI entries for invalid data!")

    async def test_remove_old_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")
        sem1 = Semantics.SemanticsAPI.Apply(prim, "Semantics0")
        typeAttr = sem1.CreateSemanticTypeAttr()
        dataAttr = sem1.CreateSemanticDataAttr()
        typeAttr.Set("semantic_type")
        dataAttr.Set("semantic_label")

        sem2 = Semantics.SemanticsAPI.Apply(prim, "Semantics1")
        typeAttr = sem2.CreateSemanticTypeAttr()
        dataAttr = sem2.CreateSemanticDataAttr()
        typeAttr.Set("semantic_type")
        dataAttr.Set("semantic_label")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 0, "There should be no SemanticsLabelsAPI entries!")

        semantic_data = semantics.schema.editor.PrimSemanticData(prim)
        current_data = semantic_data._current_data_v1
        self.assertEqual(len(current_data), 2)
        for i in range(len(current_data)):
            data = current_data[i]
            self.assertEqual(data["name"], "Semantics" + str(i))
            self.assertEqual(data["type"], "semantic_type")
            self.assertEqual(data["data"], "semantic_label")
            self.assertEqual(data["ui_hide"], False)

        # make sure this doesn't error
        with self.assertRaises(ValueError):
            semantic_data._remove_single_old_entry("INVALID_NAME")

        # check to make sure everything still exists
        self.assertTrue(prim.GetProperty("semantic:Semantics0:params:semanticData").IsDefined())
        self.assertTrue(prim.GetProperty("semantic:Semantics0:params:semanticType").IsDefined())
        self.assertTrue(prim.GetProperty("semantic:Semantics1:params:semanticData").IsDefined())
        self.assertTrue(prim.GetProperty("semantic:Semantics1:params:semanticType").IsDefined())
        # should remove properties so they return false when checked
        semantic_data._remove_single_old_entry("Semantics0")
        self.assertFalse(prim.GetProperty("semantic:Semantics0:params:semanticData").IsDefined())
        self.assertFalse(prim.GetProperty("semantic:Semantics0:params:semanticType").IsDefined())

    async def test_remove_new_semantic_data(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")

        # Add multiple semantic schemas with different instances
        prim.AddAppliedSchema("SemanticsLabelsAPI:class")
        prim.AddAppliedSchema("SemanticsLabelsAPI:subclass")
        prim.AddAppliedSchema("SemanticsLabelsAPI:category")

        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")
        sem_category = UsdSemantics.LabelsAPI(prim, "category")

        sem_class.GetLabelsAttr().Set(["test_class"])
        sem_subclass.GetLabelsAttr().Set(["sub_class1", "sub_class2"])
        sem_category.GetLabelsAttr().Set(["test_category1", "test_category2"])

        # Verify initial state
        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v1
        self.assertEqual(len(current_data), 0, "There should be no SemanticsAPI entries!")

        current_data = semantics.schema.editor.PrimSemanticData(prim)._current_data_v2
        self.assertEqual(len(current_data), 3, "There should be 3 SemanticsLabelsAPI entries!")

        # Make sure the data is correct
        semantic_data = semantics.schema.editor.PrimSemanticData(prim)
        current_data = semantic_data._current_data_v2
        data = current_data[0]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "class")
        self.assertEqual(data["labels"], ["test_class"])
        self.assertEqual(data["ui_hide"], False)

        data = current_data[1]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "subclass")
        self.assertEqual(data["labels"], ["sub_class1", "sub_class2"])
        self.assertEqual(data["ui_hide"], False)

        data = current_data[2]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "category")
        self.assertEqual(data["labels"], ["test_category1", "test_category2"])
        self.assertEqual(data["ui_hide"], False)

        # make sure this raises an error
        with self.assertRaises(ValueError):
            semantic_data._remove_single_entry("INVALID_NAME")

        # check to make sure everything still exists
        semantic_data = semantics.schema.editor.PrimSemanticData(prim)
        current_data = semantic_data._current_data_v2
        data = current_data[0]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "class")
        self.assertEqual(data["labels"], ["test_class"])
        self.assertEqual(data["ui_hide"], False)

        data = current_data[1]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "subclass")
        self.assertEqual(data["labels"], ["sub_class1", "sub_class2"])
        self.assertEqual(data["ui_hide"], False)

        data = current_data[2]
        self.assertEqual(data["api"], "SemanticsLabelsAPI")
        self.assertEqual(data["name"], "category")
        self.assertEqual(data["labels"], ["test_category1", "test_category2"])
        self.assertEqual(data["ui_hide"], False)

        # should remove properties so they return false when checked
        semantic_data._remove_single_entry("category")
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")

        self.assertFalse(prim.GetProperty("semantics:labels:category").IsDefined())

    async def test_get_prim_label(self):
        stage = omni.usd.get_context().get_stage()
        prim1 = stage.DefinePrim("/test_1/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim2 = stage.DefinePrim("/test_2/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim3 = stage.DefinePrim("/test_3/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim4 = stage.DefinePrim("/test_4/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim5 = stage.DefinePrim("/test_5/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim6 = stage.DefinePrim("/test_6/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")
        prim7 = stage.DefinePrim("/test_7/SM_Mat_Mesh_Xform_Example_M_Normal_01", "Xform")

        prim_types = ["Xform", "Mesh"]
        prefixes = ["Mat", "SM", "Mesh"]
        suffixes = ["M", "Normal"]

        label1 = semantics.schema.editor.get_prim_auto_label(
            prim1,
            prim_types=prim_types,
            remove_numerical_ending=True,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=True,
            remove_separators=True,
        )
        self.assertEqual(label1, "XformExample")

        # Numerical ending is not going to be removed
        label2 = semantics.schema.editor.get_prim_auto_label(
            prim2,
            prim_types=prim_types,
            remove_numerical_ending=False,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=True,
            remove_separators=True,
        )
        self.assertEqual(label2, "XformExampleMNormal01")

        # Prefixes and suffixes are not going to be removed cumulatively
        label3 = semantics.schema.editor.get_prim_auto_label(
            prim3,
            prim_types=prim_types,
            remove_numerical_ending=True,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=False,
            remove_separators=True,
        )
        self.assertEqual(label3, "MatMeshXformExampleM")

        # Separators ('_') are not going to be removed
        label4 = semantics.schema.editor.get_prim_auto_label(
            prim4,
            prim_types=prim_types,
            remove_numerical_ending=True,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=True,
            remove_separators=False,
        )
        self.assertEqual(label4, "Xform_Example")

        # Prim type is different so it will be skipped by returning an empty string
        label5 = semantics.schema.editor.get_prim_auto_label(
            prim5,
            prim_types=["Mesh"],
            remove_numerical_ending=True,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=True,
            remove_separators=True,
        )
        self.assertEqual(label5, "")

        # Prim types list is empty so all types are considered
        label6 = semantics.schema.editor.get_prim_auto_label(
            prim6,
            prim_types=[],
            remove_numerical_ending=True,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=True,
            remove_separators=True,
        )
        self.assertEqual(label6, "XformExample")

        # Prefixes and suffixes will end up removing the whole name, empty string is returned
        label7 = semantics.schema.editor.get_prim_auto_label(
            prim7,
            prim_types=prim_types,
            remove_numerical_ending=True,
            prefixes=["SM", "Mat", "Mesh", "Xform"],
            suffixes=["Example", "M", "Normal"],
            apply_cumulatively=True,
            remove_separators=True,
        )
        self.assertEqual(label7, "")

    async def test_add_and_remove_prim_semantics(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test", "Xform")

        # Add new entry ('class':'xform')
        add_prim_semantics(prim, data="xform", instance="class", write_type=LabelWriteType.NEW)

        # Check if the schema is applied
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))

        # Check if the instance exists and has correct labels
        sem = UsdSemantics.LabelsAPI(prim, "class")
        labels_attr = sem.GetLabelsAttr()
        self.assertIsNotNone(labels_attr, "The labels attribute should exist")
        self.assertEqual(labels_attr.Get(), ["xform"], "The labels should be set to ['xform']")

        # Add new class entry ('subclass':'sublcass_xform')
        add_prim_semantics(prim, data="sublcass_xform", instance="subclass", write_type=LabelWriteType.NEW)

        # Check if both instances exist and have correct labels
        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")

        self.assertEqual(sem_class.GetLabelsAttr().Get(), ["xform"])
        self.assertEqual(sem_subclass.GetLabelsAttr().Get(), ["sublcass_xform"])

        # Add duplicate entry ('class':'xform')
        add_prim_semantics(prim, data="xform", instance="class", write_type=LabelWriteType.NEW)

        # Verify labels haven't changed
        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")

        self.assertEqual(sem_class.GetLabelsAttr().Get(), ["xform"])
        self.assertEqual(sem_subclass.GetLabelsAttr().Get(), ["sublcass_xform"])

        # Overwrite existing class entry ('class':'new_xform')
        add_prim_semantics(prim, data="new_xform", instance="class", write_type=LabelWriteType.OVERWRITE)

        # Verify class was overwritten but subclass remains unchanged
        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")

        self.assertEqual(sem_class.GetLabelsAttr().Get(), ["new_xform"])
        self.assertEqual(sem_subclass.GetLabelsAttr().Get(), ["sublcass_xform"])

        # Skip writing the entry if 'class' entry already exits ('class':'skip_xform')
        add_prim_semantics(prim, data="skip_xform", instance="class", write_type=LabelWriteType.SKIP)

        # Verify no changes were made
        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")

        self.assertEqual(sem_class.GetLabelsAttr().Get(), ["new_xform"])
        self.assertEqual(sem_subclass.GetLabelsAttr().Get(), ["sublcass_xform"])

        # Set the writings as previews, no new data should be written ('class':'preview_xform')
        add_prim_semantics(prim, data="preview_xform_0", instance="class", write_type=LabelWriteType.NEW, preview=True)
        add_prim_semantics(
            prim, data="preview_xform_1", instance="class", write_type=LabelWriteType.OVERWRITE, preview=True
        )

        # Verify no changes were made in preview mode
        sem_class = UsdSemantics.LabelsAPI(prim, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim, "subclass")

        self.assertEqual(sem_class.GetLabelsAttr().Get(), ["new_xform"])
        self.assertEqual(sem_subclass.GetLabelsAttr().Get(), ["sublcass_xform"])

    async def test_reference_semantics(self):
        """Test to make sure correct semantics are populated (OM-96866)"""
        file_path = os.path.join(TEST_DATA_DIR, "test_reference_semantics.usda")

        # Open stage via USD File
        result, err = await omni.usd.get_context().open_stage_async(
            file_path, omni.usd.UsdContextInitialLoadSet.LOAD_ALL
        )
        await omni.kit.app.get_app().next_update_async()

        stage = omni.usd.get_context().get_stage()

        mat1 = stage.GetPrimAtPath("/World/material_root/Looks/OmniPBR")
        mat2 = stage.GetPrimAtPath("/World/material_root_01/Looks/OmniPBR")

        mat1_semantic_data = semantics.schema.editor.PrimSemanticData(mat1)
        mat1_current_data = mat1_semantic_data._current_data_v1
        mat2_semantic_data = semantics.schema.editor.PrimSemanticData(mat2)
        mat2_current_data = mat2_semantic_data._current_data_v1

        self.assertEqual(len(mat1_current_data), 1)
        self.assertEqual(len(mat2_current_data), 2)

        data1 = mat1_current_data[0]
        data2 = mat2_current_data[0]
        data3 = mat2_current_data[1]

        self.assertEqual(data1["name"], "Semantics_mdFo")
        self.assertEqual(data1["type"], "class")
        self.assertEqual(data1["data"], "blue")
        self.assertEqual(data1["ui_hide"], False)

        self.assertEqual(data2["name"], "Semantics_DC9t")
        self.assertEqual(data2["type"], "class")
        self.assertEqual(data2["data"], "bleu")
        self.assertEqual(data2["ui_hide"], False)

        self.assertEqual(data3["name"], "Semantics_mdFo")
        self.assertEqual(data3["type"], "class")
        self.assertEqual(data3["data"], "blue")
        self.assertEqual(data3["ui_hide"], False)

    async def test_upgrade_prim_semantics(self):
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_upgrade_prim", "Xform")
        sem_old = Semantics.SemanticsAPI.Apply(prim, "OldSemantics")
        sem_old.CreateSemanticTypeAttr().Set("class")
        sem_old.CreateSemanticDataAttr().Set("car")

        # Verify initial state (only old semantics)
        semantic_data = PrimSemanticData(prim)
        self.assertEqual(len(semantic_data._current_data_v1), 1)
        self.assertEqual(len(semantic_data._current_data_v2), 0)
        self.assertEqual(semantic_data._current_data_v1[0]["type"], "class")
        self.assertEqual(semantic_data._current_data_v1[0]["data"], "car")

        # Test with preview
        output_str, count = upgrade_prim_semantics(prim, preview=True)
        self.assertEqual(count, 1, "Should count one upgrade in preview mode")
        self.assertNotEqual(output_str, "", "Output string should not be empty in preview mode")
        self.assertIn("[PREVIEW]", output_str, "Output should contain preview flag")
        self.assertIn("[UPGRADE]", output_str, "Output should contain upgrade message in preview mode")
        self.assertIn("From:'OldSemantics'", output_str, "Output should mention old instance name")
        self.assertIn("To:'class'", output_str, "Output should mention new instance name")

        # Verify prim is unchanged in preview mode
        semantic_data = PrimSemanticData(prim)
        self.assertEqual(len(semantic_data._current_data_v1), 1, "Old semantics should remain after preview")
        self.assertEqual(len(semantic_data._current_data_v2), 0, "No new semantics should be created in preview")

        # Test actual upgrade
        output_str, count = upgrade_prim_semantics(prim)
        self.assertEqual(count, 1, "Should count one upgrade")
        self.assertIn("[UPGRADE]", output_str, "Output should contain upgrade message")
        self.assertIn("From:'OldSemantics'", output_str, "Output should mention old instance name")
        self.assertIn("To:'class'", output_str, "Output should mention new instance name")

        # Verify final state (only new semantics)
        semantic_data = PrimSemanticData(prim)
        self.assertEqual(len(semantic_data._current_data_v1), 0, "Old semantics should be removed")
        self.assertEqual(len(semantic_data._current_data_v2), 1, "New semantics should be created")

        new_data = semantic_data._current_data_v2[0]
        self.assertEqual(new_data["name"], "class", "Instance name should be the old type")
        self.assertEqual(new_data["labels"], ["car"], "Labels should contain the old data")
        self.assertEqual(new_data["api"], "SemanticsLabelsAPI")

        # Test upgrading a prim with no semantics
        prim_no_sem = stage.DefinePrim("/prim_no_sem", "Xform")
        output_str, count = upgrade_prim_semantics(prim_no_sem)
        self.assertEqual(count, 0, "Should count zero upgrades")
        self.assertEqual(output_str, "", "Output string should be empty for no-op upgrade")

        semantic_data_none = PrimSemanticData(prim_no_sem)
        self.assertEqual(len(semantic_data_none._current_data_v1), 0)
        self.assertEqual(len(semantic_data_none._current_data_v2), 0)

        # Test upgrading a prim with empty semantics
        prim_empty_sem = stage.DefinePrim("/prim_empty_sem", "Xform")
        sem_empty = Semantics.SemanticsAPI.Apply(prim_empty_sem, "EmptySem")
        sem_empty.CreateSemanticTypeAttr().Set("")  # Empty type
        sem_empty.CreateSemanticDataAttr().Set("")  # Empty data

        output_str, count = upgrade_prim_semantics(prim_empty_sem, preview=True)
        self.assertEqual(count, 0, "Should count zero upgrades for empty data in preview")
        self.assertNotEqual(output_str, "", "Output string should not be empty in preview mode")
        self.assertIn("[PREVIEW]", output_str, "Output should contain preview flag")
        self.assertIn("[SKIP - Empty Type/Data]", output_str, "Output should contain skip message in preview mode")

        output_str, count = upgrade_prim_semantics(prim_empty_sem)
        self.assertEqual(count, 0, "Should count zero upgrades for empty data")
        self.assertIn("[SKIP - Empty Type/Data]", output_str, "Output should contain skip message")

        # Test upgrading a prim that already has new semantics (should not change)
        prim_new_sem = stage.DefinePrim("/prim_new_sem", "Xform")
        sem_new = UsdSemantics.LabelsAPI.Apply(prim_new_sem, "category")
        sem_new.CreateLabelsAttr().Set(["vehicle"])
        output_str, count = upgrade_prim_semantics(prim_new_sem)
        self.assertEqual(count, 0, "Should count zero upgrades for prim with new semantics")
        self.assertEqual(output_str, "", "Output string should be empty for no-op upgrade")

        semantic_data_new = PrimSemanticData(prim_new_sem)
        self.assertEqual(len(semantic_data_new._current_data_v1), 0)
        self.assertEqual(len(semantic_data_new._current_data_v2), 1)
        self.assertEqual(semantic_data_new._current_data_v2[0]["name"], "category")
        self.assertEqual(semantic_data_new._current_data_v2[0]["labels"], ["vehicle"])

    async def test_upgrade_stage_semantics(self):
        stage = omni.usd.get_context().get_stage()

        # Prim 1: Old semantics
        prim1 = stage.DefinePrim("/prim1", "Xform")
        sem1_old = Semantics.SemanticsAPI.Apply(prim1, "OldSem1")
        sem1_old.CreateSemanticTypeAttr().Set("class")
        sem1_old.CreateSemanticDataAttr().Set("truck")

        # Prim 2: Old semantics with different type/data
        prim2 = stage.DefinePrim("/prim2", "Cube")
        sem2_old = Semantics.SemanticsAPI.Apply(prim2, "OldSem2")
        sem2_old.CreateSemanticTypeAttr().Set("category")
        sem2_old.CreateSemanticDataAttr().Set("prop")

        # Prim 3: Already has new semantics
        prim3 = stage.DefinePrim("/prim3", "Sphere")
        sem3_new = UsdSemantics.LabelsAPI.Apply(prim3, "material")
        sem3_new.CreateLabelsAttr().Set(["metal"])

        # Prim 4: No semantics
        prim4 = stage.DefinePrim("/prim4", "Cone")

        # Prim 5: Empty semantics
        prim5 = stage.DefinePrim("/prim5", "Cylinder")
        sem5_empty = Semantics.SemanticsAPI.Apply(prim5, "EmptySem")
        sem5_empty.CreateSemanticTypeAttr().Set("")  # Empty type
        sem5_empty.CreateSemanticDataAttr().Set("")  # Empty data

        # Test with preview
        output_str = upgrade_stage_semantics(preview=True)
        self.assertIn("[PREVIEW]", output_str, "Preview flag should be in summary")
        self.assertIn("Processed 2 old API instances", output_str, "Should find 2 valid instances")
        self.assertNotIn("Skipped", output_str, "Skipped count should not be in summary")

        # Verify no changes happened during preview
        semantic_data1 = PrimSemanticData(prim1)
        self.assertEqual(len(semantic_data1._current_data_v1), 1)
        self.assertEqual(len(semantic_data1._current_data_v2), 0)

        # Upgrade the entire stage
        output_str = upgrade_stage_semantics()
        self.assertIn("[UPGRADE]", output_str, "Output should contain upgrade messages")
        self.assertIn("Processed 2 old API instances", output_str, "Should process 2 valid instances")
        self.assertIn("[SKIP - Empty Type/Data]", output_str, "Should contain skip message for empty semantics")
        self.assertNotIn("Skipped", output_str, "Skipped count should not be in summary")

        # Verify Prim 1
        semantic_data1 = PrimSemanticData(prim1)
        self.assertEqual(len(semantic_data1._current_data_v1), 0)
        self.assertEqual(len(semantic_data1._current_data_v2), 1)
        self.assertEqual(semantic_data1._current_data_v2[0]["name"], "class")
        self.assertEqual(semantic_data1._current_data_v2[0]["labels"], ["truck"])

        # Verify Prim 2
        semantic_data2 = PrimSemanticData(prim2)
        self.assertEqual(len(semantic_data2._current_data_v1), 0)
        self.assertEqual(len(semantic_data2._current_data_v2), 1)
        self.assertEqual(semantic_data2._current_data_v2[0]["name"], "category")
        self.assertEqual(semantic_data2._current_data_v2[0]["labels"], ["prop"])

        # Verify Prim 3 (should be unchanged)
        semantic_data3 = PrimSemanticData(prim3)
        self.assertEqual(len(semantic_data3._current_data_v1), 0)
        self.assertEqual(len(semantic_data3._current_data_v2), 1)
        self.assertEqual(semantic_data3._current_data_v2[0]["name"], "material")
        self.assertEqual(semantic_data3._current_data_v2[0]["labels"], ["metal"])

        # Verify Prim 4 (should remain without semantics)
        semantic_data4 = PrimSemanticData(prim4)
        self.assertEqual(len(semantic_data4._current_data_v1), 0)
        self.assertEqual(len(semantic_data4._current_data_v2), 0)

        # Verify Prim 5 (should have empty semantics removed)
        semantic_data5 = PrimSemanticData(prim5)
        self.assertEqual(
            len(semantic_data5._current_data_v1), 1
        )  # Empty semantics remains since we only skip, not remove
        self.assertEqual(len(semantic_data5._current_data_v2), 0)

    async def test_clear_semantics(self):
        stage = omni.usd.get_context().get_stage()

        # Case 1: Clear multiple semantic label instances and ensure they're removed
        prim1 = stage.DefinePrim("/prim_clear_1", "Xform")
        prim1.AddAppliedSchema("SemanticsLabelsAPI:class")
        prim1.AddAppliedSchema("SemanticsLabelsAPI:subclass")

        sem_class = UsdSemantics.LabelsAPI(prim1, "class")
        sem_subclass = UsdSemantics.LabelsAPI(prim1, "subclass")
        sem_class.CreateLabelsAttr().Set(["label_a"])
        sem_subclass.CreateLabelsAttr().Set(["label_b1", "label_b2"])

        self.assertTrue(prim1.GetProperty("semantics:labels:class").IsDefined())
        self.assertTrue(prim1.GetProperty("semantics:labels:subclass").IsDefined())
        self.assertTrue(prim1.HasAPI(UsdSemantics.LabelsAPI))

        semantics.schema.editor.clear_semantics(prim1)
        prim1 = stage.GetPrimAtPath("/prim_clear_1")

        self.assertFalse(prim1.GetProperty("semantics:labels:class").IsDefined())
        self.assertFalse(prim1.GetProperty("semantics:labels:subclass").IsDefined())
        self.assertFalse(prim1.HasAPI(UsdSemantics.LabelsAPI))

        # Case 2: Preserve non-semantic API schemas while clearing semantics
        prim2 = stage.DefinePrim("/prim_clear_2", "Xform")
        Usd.CollectionAPI.Apply(prim2, "keepMe")  # Non-semantic applied API schema
        prim2.AddAppliedSchema("SemanticsLabelsAPI:category")

        UsdSemantics.LabelsAPI(prim2, "category").CreateLabelsAttr().Set(["label_c"])

        self.assertTrue(prim2.HasAPI(Usd.CollectionAPI))
        self.assertTrue(prim2.GetProperty("semantics:labels:category").IsDefined())

        semantics.schema.editor.clear_semantics(prim2)
        prim2 = stage.GetPrimAtPath("/prim_clear_2")

        self.assertFalse(prim2.GetProperty("semantics:labels:category").IsDefined())
        self.assertTrue(prim2.HasAPI(Usd.CollectionAPI))

    async def test_semantics_with_existing_api_schemas(self):
        """Test that adding semantic labels preserves existing API schemas"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_cube", "Cube")

        # Apply various API schemas
        UsdPhysics.CollisionAPI.Apply(prim)
        UsdPhysics.RigidBodyAPI.Apply(prim)
        # Multi-apply schema with instance names
        Usd.CollectionAPI.Apply(prim, "testCollection")

        # Verify initial state
        self.assertTrue(prim.HasAPI(UsdPhysics.CollisionAPI))
        self.assertTrue(prim.HasAPI(UsdPhysics.RigidBodyAPI))
        self.assertTrue(prim.HasAPI(Usd.CollectionAPI))

        initial_schemas = prim.GetAppliedSchemas()
        self.assertIn("PhysicsCollisionAPI", initial_schemas)
        self.assertIn("PhysicsRigidBodyAPI", initial_schemas)
        self.assertIn("CollectionAPI:testCollection", initial_schemas)

        # Add semantic labels
        add_prim_semantics(prim, ["cube"], "class")
        prim = stage.GetPrimAtPath("/test_cube")

        # Verify semantic labels were added
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))
        self.assertTrue(prim.GetProperty("semantics:labels:class").IsDefined())
        sem_attr = prim.GetAttribute("semantics:labels:class")
        self.assertEqual(sem_attr.Get(), ["cube"])

        # Verify existing schemas are preserved
        final_schemas = prim.GetAppliedSchemas()
        self.assertTrue(prim.HasAPI(UsdPhysics.CollisionAPI))
        self.assertTrue(prim.HasAPI(UsdPhysics.RigidBodyAPI))
        self.assertTrue(prim.HasAPI(Usd.CollectionAPI))
        self.assertIn("PhysicsCollisionAPI", final_schemas)
        self.assertIn("PhysicsRigidBodyAPI", final_schemas)
        self.assertIn("CollectionAPI:testCollection", final_schemas)
        self.assertIn("SemanticsLabelsAPI:class", final_schemas)

        # Add additional semantic instance
        add_prim_semantics(prim, ["geometry"], "type")
        prim = stage.GetPrimAtPath("/test_cube")

        # Verify all schemas still exist
        final_schemas_2 = prim.GetAppliedSchemas()
        self.assertTrue(prim.HasAPI(UsdPhysics.CollisionAPI))
        self.assertTrue(prim.HasAPI(UsdPhysics.RigidBodyAPI))
        self.assertTrue(prim.HasAPI(Usd.CollectionAPI))
        self.assertIn("SemanticsLabelsAPI:class", final_schemas_2)
        self.assertIn("SemanticsLabelsAPI:type", final_schemas_2)

        # Verify semantic values
        class_attr = prim.GetAttribute("semantics:labels:class")
        type_attr = prim.GetAttribute("semantics:labels:type")
        self.assertEqual(class_attr.Get(), ["cube"])
        self.assertEqual(type_attr.Get(), ["geometry"])

    async def test_add_multiple_labels_to_same_instance(self):
        """Test that adding labels to an existing semantic instance merges them correctly"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_merge", "Cube")

        # Add initial semantic labels
        add_prim_semantics(prim, ["vehicle"], "class")
        prim = stage.GetPrimAtPath("/test_merge")

        # Verify initial state
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))
        sem_attr = prim.GetAttribute("semantics:labels:class")
        self.assertEqual(sem_attr.Get(), ["vehicle"])

        # Add more labels to the same instance
        add_prim_semantics(prim, ["car"], "class")
        prim = stage.GetPrimAtPath("/test_merge")

        # Verify labels were merged (no duplicates)
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"vehicle", "car"})
        self.assertEqual(len(labels), 2)

        # Try adding a duplicate label
        add_prim_semantics(prim, ["vehicle"], "class")
        prim = stage.GetPrimAtPath("/test_merge")

        # Verify no duplicate was added
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"vehicle", "car"})
        self.assertEqual(len(labels), 2)

        # Add multiple labels at once
        add_prim_semantics(prim, ["truck", "automobile"], "class")
        prim = stage.GetPrimAtPath("/test_merge")

        # Verify all labels are present
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"vehicle", "car", "truck", "automobile"})
        self.assertEqual(len(labels), 4)

    async def test_ui_add_entry_merges_labels(self):
        """Test that the UI's add_entry method correctly merges labels for existing instances"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_ui_merge", "Sphere")

        # Create semantic data object
        semantic_data = PrimSemanticData(prim)

        # Add initial entry
        semantic_data.add_entry("class", "furniture")
        prim = stage.GetPrimAtPath("/test_ui_merge")

        # Verify initial state
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))
        sem_attr = prim.GetAttribute("semantics:labels:class")
        self.assertEqual(sem_attr.Get(), ["furniture"])

        # Add more labels to the same instance using UI method
        semantic_data.add_entry("class", "chair,wooden")
        prim = stage.GetPrimAtPath("/test_ui_merge")

        # Verify labels were merged correctly
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"furniture", "chair", "wooden"})
        self.assertEqual(len(labels), 3)

        # Try adding duplicates
        semantic_data.add_entry("class", "chair,table")
        prim = stage.GetPrimAtPath("/test_ui_merge")

        # Verify no duplicates were added but new label was
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"furniture", "chair", "wooden", "table"})
        self.assertEqual(len(labels), 4)

    async def test_remove_single_label(self):
        """Test that removing a single label from an instance works correctly"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_remove_label", "Cube")

        # Add multiple labels to the same instance
        add_prim_semantics(prim, ["vehicle", "car", "automobile"], "class")
        prim = stage.GetPrimAtPath("/test_remove_label")

        # Verify initial state
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))
        sem_attr = prim.GetAttribute("semantics:labels:class")
        initial_labels = sem_attr.Get()
        self.assertEqual(set(initial_labels), {"vehicle", "car", "automobile"})
        self.assertEqual(len(initial_labels), 3)

        # Create semantic data object and remove one label
        semantic_data = PrimSemanticData(prim)
        semantic_data._remove_single_label("class", "car")
        prim = stage.GetPrimAtPath("/test_remove_label")

        # Verify one label was removed
        sem_attr = prim.GetAttribute("semantics:labels:class")
        remaining_labels = sem_attr.Get()
        self.assertEqual(set(remaining_labels), {"vehicle", "automobile"})
        self.assertEqual(len(remaining_labels), 2)

        # Remove another label
        semantic_data._remove_single_label("class", "vehicle")
        prim = stage.GetPrimAtPath("/test_remove_label")

        # Verify only one label remains
        sem_attr = prim.GetAttribute("semantics:labels:class")
        remaining_labels = sem_attr.Get()
        self.assertEqual(remaining_labels, ["automobile"])

        # Remove the last label
        semantic_data._remove_single_label("class", "automobile")
        prim = stage.GetPrimAtPath("/test_remove_label")

        # Verify the instance was completely removed
        self.assertFalse(prim.GetProperty("semantics:labels:class").IsDefined())
        applied_schemas = prim.GetAppliedSchemas()
        self.assertNotIn("SemanticsLabelsAPI:class", applied_schemas)

    async def test_remove_nonexistent_label(self):
        """Test that removing a non-existent label handles gracefully"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_remove_nonexistent", "Sphere")

        # Add one label
        add_prim_semantics(prim, ["vehicle"], "class")
        prim = stage.GetPrimAtPath("/test_remove_nonexistent")

        # Try to remove a label that doesn't exist
        semantic_data = PrimSemanticData(prim)
        semantic_data._remove_single_label("class", "nonexistent")
        prim = stage.GetPrimAtPath("/test_remove_nonexistent")

        # Verify original label is still there
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(labels, ["vehicle"])

    async def test_batch_processing_multiple_prims(self):
        """Test that add_prim_semantics can handle multiple prims at once"""
        stage = omni.usd.get_context().get_stage()
        prim1 = stage.DefinePrim("/test_batch_1", "Cube")
        prim2 = stage.DefinePrim("/test_batch_2", "Sphere")
        prim3 = stage.DefinePrim("/test_batch_3", "Cylinder")

        # Test batch processing with multiple prims
        prims = [prim1, prim2, prim3]
        add_prim_semantics(prims, ["vehicle"], "class")

        # Verify all prims got the semantic labels
        for i, prim_path in enumerate(["/test_batch_1", "/test_batch_2", "/test_batch_3"]):
            prim = stage.GetPrimAtPath(prim_path)
            self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))
            sem_attr = prim.GetAttribute("semantics:labels:class")
            self.assertEqual(sem_attr.Get(), ["vehicle"], f"Prim {i+1} should have vehicle label")

    async def test_legacy_conversion_automatic(self):
        """Test automatic conversion of legacy SemanticsAPI to new format"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_legacy_auto", "Cube")

        # Add old-style semantics
        sem_old = Semantics.SemanticsAPI.Apply(prim, "OldSemantics")
        sem_old.CreateSemanticTypeAttr().Set("class")
        sem_old.CreateSemanticDataAttr().Set("vehicle")

        # Verify old schema exists
        self.assertTrue(prim.HasAPI(Semantics.SemanticsAPI))
        self.assertFalse(prim.HasAPI(UsdSemantics.LabelsAPI))

        # Add new semantics with auto conversion
        add_prim_semantics(prim, ["car"], "class", auto_convert_legacy=True)
        prim = stage.GetPrimAtPath("/test_legacy_auto")

        # Verify conversion happened
        self.assertFalse(prim.HasAPI(Semantics.SemanticsAPI))
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))

        # Verify merged labels (legacy + new)
        sem_attr = prim.GetAttribute("semantics:labels:class")
        labels = sem_attr.Get()
        self.assertEqual(set(labels), {"vehicle", "car"})

    async def test_dictionary_input_format(self):
        """Test using dictionary format for multiple semantic instances"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_dict_input", "Mesh")

        # Use dictionary format
        semantic_data = {"class": ["vehicle", "automobile"], "type": "transportation", "color": ["red", "blue"]}

        add_prim_semantics(prim, semantic_data)
        prim = stage.GetPrimAtPath("/test_dict_input")

        # Verify all instances were created
        self.assertTrue(prim.HasAPI(UsdSemantics.LabelsAPI))

        class_attr = prim.GetAttribute("semantics:labels:class")
        type_attr = prim.GetAttribute("semantics:labels:type")
        color_attr = prim.GetAttribute("semantics:labels:color")

        self.assertEqual(set(class_attr.Get()), {"vehicle", "automobile"})
        self.assertEqual(type_attr.Get(), ["transportation"])
        self.assertEqual(set(color_attr.Get()), {"red", "blue"})

    async def test_semantics_appended_listop_preservation(self):
        """Test that semantic labels preserve appended ListOp structure"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_appended", "Capsule")
        layer = stage.GetEditTarget().GetLayer()
        prim_spec = layer.GetPrimAtPath("/test_appended")

        # Set up existing appended apiSchemas
        appended_schemas = Sdf.TokenListOp()
        appended_schemas.appendedItems = ["PhysicsRigidBodyAPI"]
        prim_spec.SetInfo("apiSchemas", appended_schemas)

        # Add semantic label
        add_prim_semantics(prim, ["label1"], "category")

        # Verify appended structure is preserved
        updated_schemas = prim_spec.GetInfo("apiSchemas")
        self.assertIsNotNone(updated_schemas.appendedItems)
        self.assertIn("SemanticsLabelsAPI:category", updated_schemas.appendedItems)
        self.assertIn("PhysicsRigidBodyAPI", updated_schemas.appendedItems)
        self.assertFalse(updated_schemas.explicitItems)

    async def test_semantics_explicit_listop_preservation(self):
        """Test that semantic labels preserve explicit ListOp structure"""
        stage = omni.usd.get_context().get_stage()
        prim = stage.DefinePrim("/test_explicit", "Sphere")
        layer = stage.GetEditTarget().GetLayer()
        prim_spec = layer.GetPrimAtPath("/test_explicit")

        # Set up existing explicit apiSchemas
        existing_schemas = Sdf.TokenListOp.CreateExplicit(["PhysicsRigidBodyAPI", "CollectionAPI:test"])
        prim_spec.SetInfo("apiSchemas", existing_schemas)

        # Add semantic label
        add_prim_semantics(prim, ["label1"], "class")

        # Verify explicit structure is preserved
        updated_schemas = prim_spec.GetInfo("apiSchemas")
        self.assertIsNotNone(updated_schemas.explicitItems)
        self.assertIn("SemanticsLabelsAPI:class", updated_schemas.explicitItems)
        self.assertIn("PhysicsRigidBodyAPI", updated_schemas.explicitItems)
        self.assertIn("CollectionAPI:test", updated_schemas.explicitItems)
        self.assertFalse(updated_schemas.appendedItems)
