# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import List

import carb.tokens
import omni.kit.ui_test as ui_test
from omni import ui
from omni.ui.tests.test_base import OmniUiTest

from ..test_utils.ui_utils import expand_advanced_convert_option_frame
from ..ui import CadConverterOptionsBuilder, OptionDef, OptionType, SimpleDoubleModel
from ..ui.confirm_dialog_helper import ConfirmDialogHelper
from ..ui.progress_popup import ProgressDialog

OPTIONS_TEST_WINDOW_NAME = "Options Test"

# Test bool, float, and combo box options
OPTION_DEFINITIONS: List[OptionDef] = [
    OptionDef(
        "convertHidden",
        "Convert Visible Only",
        "Convert Visible Only -\nIf true, skip hidden elements;\nelse, convert hidden elements but set to invisible.",
        OptionType.BOOL_INVERTED,
        section="main",
    ),
    OptionDef(
        "mergeMeshes",
        "Merge Meshes",
        "If true, then meshes are merged for optimization",
        OptionType.BOOL,
        section="advanced",
    ),
    OptionDef(
        "tessLOD",
        "Tessellation Level",
        "",
        OptionType.COMBO,
        combo_items=["ExtraLow", "Low", "Medium", "High", "ExtraHigh"],
        section="tessellation",
    ),
    OptionDef(
        "surfaceTolerance",
        "Surface Tolerance",
        "Surface Tolerance - maximum distance between tessellated mesh and surface. \nIf a value of 0 is provided, then surface tolerance of an object is calculated as the diagonal its extents multiplied by 0.025.",
        OptionType.DOUBLE,
        section="tessellation",
        min_value=0.0,
    ),
    OptionDef(
        "unitScale",
        "Unit Scale",
        "Known unit scale",
        OptionType.COMBO,
        combo_items=["Native Units", "meter", "millimeter"],
        combo_values=[0.0, 1.0, 0.001],
        section="tessellation",
    ),
]


class TestCommonConverterUI(OmniUiTest):
    async def test_progress_dialog_setup(self):
        """Test state of progress dialog."""
        dialog = ProgressDialog()
        dialog._build_ui()
        self.assertIsNotNone(dialog.window)
        dialog.set_progress_info("test", 10.0)
        self.assertEqual(dialog._progress_label.text, "test")
        self.assertAlmostEqual(dialog._progress_bar.model.get_value_as_float(), 10.0)
        dialog.set_step_info("Content Update")
        self.assertEqual(dialog._step_label.text, "Content Update")
        dialog.show()
        cancel_btn = ui_test.find("CAD Converter Progress//Frame/**/Button[*].identifier=='cancel_btn'")
        await cancel_btn.click()
        await ui_test.wait_n_updates(3)
        dialog.clear()
        self.assertEqual(dialog._progress_label.text, "")
        self.assertEqual(dialog._progress_bar.model.get_value_as_float(), 0.0)
        self.assertEqual(dialog._step_label.text, "")
        dialog.destroy()
        self.assertIsNone(dialog._window)
        self.assertIsNone(dialog._progress_label)
        self.assertIsNone(dialog._progress_bar)
        self.assertIsNone(dialog._step_label)

    async def test_confirm_dialog_location(self):
        """Test output path doesn't contain URL encoding when using Nucleus path with special characters"""
        helper = ConfirmDialogHelper()
        file_path = "omniverse://localhost/Projects/test-{3D}.SLDPRT"
        export_folder = "omniverse://localhost/Projects"
        confirm_write, output_path, file_url = await helper.confirm_write_location(
            file_path, export_folder, True, "", ""
        )
        self.assertEqual("omniverse://localhost/Projects/test-{3D}.usd", output_path)

    async def test_cad_converter_options_builder_updates_model(self):
        """Test that CadConverterOptionsBuilder updates the provided options model via UI interactions."""

        class OptionsModel:
            def __init__(self):
                self.convertHidden = False
                self.mergeMeshes = True
                self.tessLOD = 2
                self.surfaceTolerance = 0.0
                self.unitScale = 0.001

        options = OptionsModel()
        builder = CadConverterOptionsBuilder(options, OPTION_DEFINITIONS)

        window = ui.Window(OPTIONS_TEST_WINDOW_NAME, width=320, height=240)
        with window.frame:
            builder.build_pane([])

        # expand advanced options frame
        await expand_advanced_convert_option_frame()

        # Toggle Convert Visible Only
        chk_visible = ui_test.find(
            f"{OPTIONS_TEST_WINDOW_NAME}//Frame/**/CheckBox[*].identifier=='check_convertHidden'"
        )
        await chk_visible.click()
        await ui_test.wait_n_updates(3)
        self.assertTrue(options.convertHidden)

        # Toggle Merge Meshes
        chk_merge = ui_test.find(f"{OPTIONS_TEST_WINDOW_NAME}//Frame/**/CheckBox[*].identifier=='check_mergeMeshes'")
        await chk_merge.click()
        await ui_test.wait_n_updates(3)
        self.assertFalse(options.mergeMeshes)

        # tessLOD should be set to desired value
        tess_lod_combo = ui_test.find(f"{OPTIONS_TEST_WINDOW_NAME}//Frame/**/ComboBox[*].identifier=='combo_tessLOD'")
        tess_lod_combo.model.get_item_value_model(None, 0).set_value(1)
        await ui_test.wait_n_updates(3)
        self.assertEqual(options.tessLOD, 1)

        # Combo values can map display rows to non-integer model values.
        unit_scale_combo = ui_test.find(
            f"{OPTIONS_TEST_WINDOW_NAME}//Frame/**/ComboBox[*].identifier=='combo_unitScale'"
        )
        self.assertEqual(unit_scale_combo.model.current_index, 2)
        unit_scale_combo.model.get_item_value_model(None, 0).set_value(1)
        await ui_test.wait_n_updates(3)
        self.assertEqual(options.unitScale, 1.0)

        # Surface tolerance should be set to desired value
        tol_field = ui_test.find(
            f"{OPTIONS_TEST_WINDOW_NAME}//Frame/**/FloatField[*].identifier=='field_surfaceTolerance'"
        )
        tol_field.model.set_value(500.5)
        await ui_test.wait_n_updates(3)
        self.assertEqual(options.surfaceTolerance, 500.5)

        # DOUBLE options keep their source text until Python parses it as
        # binary64, avoiding SimpleFloatModel's binary32 conversion.
        self.assertIsInstance(tol_field.model, SimpleDoubleModel)
        tol_field.model.set_value("0.374")
        await ui_test.wait_n_updates(3)
        self.assertEqual(tol_field.model.as_string, "0.374")
        self.assertEqual(options.surfaceTolerance, 0.374)

        # Test negative surface tolerance should be clamped to zero
        tol_field.model.set_value(-0.5)
        await ui_test.wait_n_updates(3)
        self.assertEqual(options.surfaceTolerance, 0.0)

        # Test the destroy function
        builder.destroy()
        # Verify that the subscriptions and models are cleared
        self.assertFalse(builder._subscriptions)
        self.assertFalse(builder._models)

        window.destroy()
