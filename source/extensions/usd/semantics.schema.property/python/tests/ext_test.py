import os
from pathlib import Path

import omni.kit
import omni.kit.commands
import omni.kit.test
import omni.kit.ui_test as uitest
import omni.usd

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
from carb.input import KeyboardInput
from omni.kit.test_suite.helpers import arrange_windows, wait_stage_loading
from omni.ui.tests.test_base import OmniUiTest

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from pxr import Sdf, Semantics, Usd, UsdSemantics

TEST_DATA_DIR = Path(os.path.dirname(os.path.realpath(__file__))).joinpath("data")


class TestSemanticsPropertyWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        await omni.usd.get_context().new_stage_async()

        # Create a test objects
        stage = omni.usd.get_context().get_stage()

        # Object with no semantics
        omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cone")

        # Object with single semantics
        omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Sphere")
        prim = stage.GetPrimAtPath("/Sphere")
        prim.AddAppliedSchema("SemanticsLabelsAPI:semantics")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        labelsAttr = sem.CreateLabelsAttr()
        labelsAttr.Set(["label"])

        # Object with multiple semantics
        omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
        prim = stage.GetPrimAtPath("/Cube")
        prim.AddAppliedSchema("SemanticsLabelsAPI:semantics1")
        sem = UsdSemantics.LabelsAPI(prim, "semantics1")
        labelsAttr = sem.CreateLabelsAttr()
        labelsAttr.Set(["label1"])
        prim.AddAppliedSchema("SemanticsLabelsAPI:semantics2")
        sem = UsdSemantics.LabelsAPI(prim, "semantics2")
        labelsAttr = sem.CreateLabelsAttr()
        labelsAttr.Set(["label2"])

        # Object with deprecated semantics
        omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cylinder")
        prim = stage.GetPrimAtPath("/Cylinder")
        prim.AddAppliedSchema("SemanticsLabelsAPI:new")
        sem = UsdSemantics.LabelsAPI(prim, "new")
        labelsAttr = sem.CreateLabelsAttr()
        labelsAttr.Set(["label"])
        sem = Semantics.SemanticsAPI.Apply(prim, "test")
        sem.CreateSemanticTypeAttr()
        sem.CreateSemanticDataAttr()
        typeAttr = sem.GetSemanticTypeAttr()
        dataAttr = sem.GetSemanticDataAttr()
        typeAttr.Set("class")
        dataAttr.Set("cyclinder")

        import omni.kit.window.property as p

        self._w = p.get_window()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_modify_with_invalid_label_input(self):
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Sphere"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Get the initial semantic type
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Sphere")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        init_semantic_label = sem.GetLabelsAttr().Get()

        # Test trying to modify with blank entry
        semantic_label_input = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                semantic_label_input = True
                await w.double_click()
                await uitest.emulate_keyboard_press(KeyboardInput.BACKSPACE)
                await uitest.emulate_keyboard_press(KeyboardInput.ENTER)

                self.assertEqual(
                    uitest.find(
                        "Property//Frame/**/StringField[*].identifier=='txt_semantic_label'"
                    ).widget.model.as_string,
                    "label",
                )
        self.assertTrue(semantic_label_input, "Label input not present!")

        # Make sure the semantic type didn't change
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Sphere")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        self.assertEqual(sem.GetLabelsAttr().Get(), init_semantic_label)

        # Test trying to modify with entry containing ':'
        semantic_label_input = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                semantic_label_input = True
                await w.double_click()
                await uitest.emulate_char_press("te:st")
                await uitest.emulate_keyboard_press(KeyboardInput.ENTER)

                self.assertEqual(
                    uitest.find(
                        "Property//Frame/**/StringField[*].identifier=='txt_semantic_label'"
                    ).widget.model.as_string,
                    "label",
                )
        self.assertTrue(semantic_label_input, "Label input not present!")

        # Make sure the semantic type didn't change
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Sphere")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        self.assertEqual(sem.GetLabelsAttr().Get(), init_semantic_label)

    async def test_modify_with_valid_input(self):
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Sphere"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Get the initial semantic label
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Sphere")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        init_semantic_label = sem.GetLabelsAttr().Get()

        # Test modify label entry
        semantic_label_input = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                semantic_label_input = True
                await w.double_click()
                await uitest.emulate_char_press("test_label")
                await uitest.emulate_keyboard_press(KeyboardInput.ENTER)

                self.assertEqual(
                    uitest.find(
                        "Property//Frame/**/StringField[*].identifier=='txt_semantic_label'"
                    ).widget.model.as_string,
                    "test_label",
                )
        self.assertTrue(semantic_label_input, "Label input not present!")

        # Make sure the semantic label changed on the prim properly
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Sphere")
        sem = UsdSemantics.LabelsAPI(prim, "semantics")
        self.assertNotEqual(sem.GetLabelsAttr().Get(), init_semantic_label)
        self.assertEqual(sem.GetLabelsAttr().Get(), ["test_label"])

    async def test_display_no_semantics(self):
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Cone"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Check that no semantic label UI elements are present
        contains_semantic_label = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                contains_semantic_label = True

        self.assertFalse(
            contains_semantic_label, "Semantic label UI elements should not be present for a prim with no semantics"
        )

    async def test_display_single_semantics(self):
        """Test to see if the correct UI elements are present when a prim with a single semantics label is selected"""
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Sphere"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Get the semantic label text box and make sure its text box contains "label"
        contains_semantic_label = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                contains_semantic_label = True
                self.assertEqual(
                    uitest.find(
                        "Property//Frame/**/StringField[*].identifier=='txt_semantic_label'"
                    ).widget.model.as_string,
                    "label",
                )
                break

        self.assertTrue(
            contains_semantic_label, "Semantic label UI element should be present for a prim with semantics"
        )

    async def test_display_multiple_semantics(self):
        """Test to see if the correct UI elements are present when a prim with multiple semantics labels is selected"""
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Cube"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Get the semantic label text boxes and make sure they contain the expected values
        golden_label_results = ["label1", "label2"]
        contains_semantic_label = []
        idx = 0
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                contains_semantic_label.append(True)
                self.assertEqual(
                    uitest.find_all("Property//Frame/**/StringField[*].identifier=='txt_semantic_label'")[
                        idx
                    ].widget.model.as_string,
                    golden_label_results[idx],
                )
                idx += 1

        self.assertEqual(sum(contains_semantic_label), 2, "Should find exactly 2 semantic label UI elements")

    async def test_display_multiple_selection_mixed(self):
        """Test to see if the correct UI elements are present when a mix of all the prims are selected"""
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Cone", "/Sphere", "/Cube"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Check that there are 3 header labels that separate the different selected prims
        golden_prim_path_results = ["/Cone", "/Sphere", "/Cube"]
        contains_semantic_prim_path = []
        idx = 0
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "lbl_semantic_prim_path":
                contains_semantic_prim_path.append(True)
                self.assertEqual(
                    uitest.find_all("Property//Frame/**/Label[*].identifier=='lbl_semantic_prim_path'")[
                        idx
                    ].widget.text,
                    golden_prim_path_results[idx],
                )
                idx += 1

        self.assertEqual(sum(contains_semantic_prim_path), 3, "Should find exactly 3 prim path labels")

        # Get the semantic label text boxes and make sure they contain the expected values
        # Note: Cone has no semantics, Sphere has one label, Cube has two labels
        golden_label_results = ["label", "label1", "label2"]
        contains_semantic_label = []
        idx = 0
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "txt_semantic_label":
                contains_semantic_label.append(True)
                self.assertEqual(
                    uitest.find_all("Property//Frame/**/StringField[*].identifier=='txt_semantic_label'")[
                        idx
                    ].widget.model.as_string,
                    golden_label_results[idx],
                )
                idx += 1

        self.assertEqual(sum(contains_semantic_label), 3, "Should find exactly 3 semantic label UI elements")

    async def test_display_deprecated_semantics(self):
        usd_context = omni.usd.get_context()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Cylinder"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await uitest.human_delay(10)

        # Check that the deprecated semantics UI elements are present
        contains_deprecated_semantics = False
        for w in uitest.find_all("Property//Frame/**/*.identifier!=''"):
            if w.widget.identifier == "lbl_deprecated_semantics":
                contains_deprecated_semantics = True
                break

        self.assertTrue(
            contains_deprecated_semantics,
            "Deprecated semantics UI element should be present for a prim with deprecated semantics",
        )
