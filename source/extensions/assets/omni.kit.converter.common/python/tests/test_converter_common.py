# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import omni.kit.test
from pxr import Usd, UsdGeom

from .. import ProgressLogConsumer, ProgressStepType
from ..common import (
    config_path_to_args,
    dict_to_args,
    extract_zip_archive,
    is_asset_supported,
    run_scene_opt,
    strip_file_regex,
    validate_file_path,
)


class TestConverterCommon(omni.kit.test.AsyncTestCase):
    async def test_validate_file_path(self):
        test_output_path = Path(omni.kit.test.get_test_output_path()) / "validate_file_path"
        os.makedirs(test_output_path, exist_ok=True)

        if os.name == "nt":
            does_not_exist = "C:/foo/bar/__with%20spaces__"
        else:
            does_not_exist = "/foo/bar/__with%20spaces__"

        with_p20_1 = str(test_output_path / "with%20spaces%201.tmp")
        with open(with_p20_1, "w"):
            pass

        with_p20_2 = str(test_output_path / "with%20spaces%202.tmp")
        with_spaces_2 = str(test_output_path / "with spaces 2.tmp")
        with open(with_spaces_2, "w"):
            pass

        # does not exist should return None
        self.assertIsNone(validate_file_path(does_not_exist))

        # with_p20_1 should return with_p20_1 because it exists
        self.assertEqual(validate_file_path(with_p20_1), with_p20_1)

        # with_p20_2 should return with_spaces_2
        self.assertEqual(validate_file_path(with_p20_2), with_spaces_2)

        # omniverse url should return unchanged.
        omniverse_url = "omniverse://kit-test-content.ov.nvidia.com/Projects/Converters_Test_Models/STL/ASS%20crane.stl"
        self.assertEqual(validate_file_path(omniverse_url), omniverse_url)

    async def test_extract_zip_archive(self):
        """Test the extract_zip_archive function with valid and invalid zip files."""

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with valid zip file
            zip_path = temp_path / "test_archive.zip"
            test_content = "test content"

            # Create a zip file
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.writestr("test_file.txt", test_content)
                zip_file.writestr("subfolder/nested_file.txt", "nested content")

            # Test extraction
            result = extract_zip_archive(str(zip_path))
            self.assertTrue(result)

            # Verify files were extracted
            extracted_file = temp_path / "test_file.txt"
            nested_file = temp_path / "subfolder" / "nested_file.txt"
            self.assertTrue(extracted_file.exists())
            self.assertTrue(nested_file.exists())

            # Verify content
            with open(extracted_file, "r") as f:
                self.assertEqual(f.read(), test_content)

            # Test with non-existent zip file
            non_existent_path = temp_path / "non_existent.zip"
            result = extract_zip_archive(str(non_existent_path))
            self.assertFalse(result)

            # Test with corrupted zip file
            corrupted_zip_path = temp_path / "corrupted.zip"
            with open(corrupted_zip_path, "w") as f:
                f.write("This is not a zip file")

            result = extract_zip_archive(str(corrupted_zip_path))
            self.assertFalse(result)

            # Test with empty zip file
            empty_zip_path = temp_path / "empty.zip"
            with zipfile.ZipFile(empty_zip_path, "w") as zip_file:
                pass

            result = extract_zip_archive(str(empty_zip_path))
            self.assertTrue(result)

    async def test_config_path_to_args(self):
        """Test the config_path_to_args function with various config files."""

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with valid JSON config file
            config_path = temp_path / "test_config.json"
            config_data = {
                "optimize": True,
                "convert_hidden": False,
                "meters_per_unit": 1.0,
                "up_axis": 1,
                "string_param": "test_value",
            }

            with open(config_path, "w") as f:
                json.dump(config_data, f)

            result = config_path_to_args(str(config_path))

            # Verify boolean values are converted to lowercase strings
            self.assertEqual(result["optimize"], "true")
            self.assertEqual(result["convert_hidden"], "false")

            # Verify numeric values are converted to strings
            self.assertEqual(result["meters_per_unit"], "1.0")
            self.assertEqual(result["up_axis"], "1")

            # Verify string values are converted to strings
            self.assertEqual(result["string_param"], "test_value")

            # Test with non-existent config file
            non_existent_path = temp_path / "non_existent.json"
            result = config_path_to_args(str(non_existent_path))
            self.assertEqual(result, {})

            # Test with empty config file
            empty_config_path = temp_path / "empty_config.json"
            with open(empty_config_path, "w") as f:
                f.write("{}")

            result = config_path_to_args(str(empty_config_path))
            self.assertEqual(result, {})

            # Test with None config path
            result = config_path_to_args(None)
            self.assertEqual(result, {})

            # Test with empty string config path
            result = config_path_to_args("")
            self.assertEqual(result, {})

            # Test with config file containing special characters
            special_config_path = temp_path / "special_config.json"
            special_data = {
                "path_with_spaces": "C:/Program Files/Test",
                "quoted_string": "value with 'quotes'",
                "boolean_true": True,
                "boolean_false": False,
            }

            with open(special_config_path, "w") as f:
                json.dump(special_data, f)

            result = config_path_to_args(str(special_config_path))
            self.assertEqual(result["path_with_spaces"], "C:/Program Files/Test")
            self.assertEqual(result["quoted_string"], 'value with "quotes"')
            self.assertEqual(result["boolean_true"], "true")
            self.assertEqual(result["boolean_false"], "false")

    async def test_dict_to_args(self):
        """Test the dict_to_args function with various dictionary inputs."""

        # Test with basic data types
        config_data = {
            "optimize": True,
            "convert_hidden": False,
            "meters_per_unit": 1.0,
            "up_axis": 1,
            "string_param": "test_value",
            "integer_param": 42,
            "float_param": 3.14159,
        }

        result = dict_to_args(config_data)

        # Verify boolean values are converted to lowercase strings
        self.assertEqual(result["optimize"], "true")
        self.assertEqual(result["convert_hidden"], "false")

        # Verify numeric values are converted to strings
        self.assertEqual(result["meters_per_unit"], "1.0")
        self.assertEqual(result["up_axis"], "1")
        self.assertEqual(result["integer_param"], "42")
        self.assertEqual(result["float_param"], "3.14159")

        # Verify string values are converted to strings
        self.assertEqual(result["string_param"], "test_value")

        # Test with empty dictionary
        result = dict_to_args({})
        self.assertEqual(result, {})

        # Test with None dictionary
        result = dict_to_args(None)
        self.assertEqual(result, {})

        # Test with dictionary containing special characters
        special_data = {
            "path_with_spaces": "C:/Program Files/Test",
            "quoted_string": "value with 'quotes'",
            "boolean_true": True,
            "boolean_false": False,
            "null_value": None,
        }

        result = dict_to_args(special_data)
        self.assertEqual(result["path_with_spaces"], "C:/Program Files/Test")
        self.assertEqual(result["quoted_string"], 'value with "quotes"')
        self.assertEqual(result["boolean_true"], "true")
        self.assertEqual(result["boolean_false"], "false")
        self.assertEqual(result["null_value"], "None")

        # Test with nested dictionary (should flatten to string)
        nested_data = {"simple": "value", "list": [1, 2, 3], "boolean": True}

        result = dict_to_args(nested_data)
        self.assertEqual(result["simple"], "value")
        self.assertEqual(result["list"], "[1, 2, 3]")
        self.assertEqual(result["boolean"], "true")

    async def test_progress_log_consumer(self):
        log_prefix = "[omni.converter.test]"
        consumer = ProgressLogConsumer(log_prefix)

        # Unknown due to wrong prefix
        result = consumer.extract_line("[other]step*prog*50*Importing Geometry")
        self.assertEqual(result, [ProgressStepType.UNKNOWN])

        # Begin step
        result = consumer.extract_line(f"{log_prefix}step*prog*0*Begin Reading CAD")
        self.assertEqual(result[0], ProgressStepType.BEGIN)
        self.assertEqual(result[1], "Begin Reading CAD")

        # Progress update
        result = consumer.extract_line(f"{log_prefix}step*prog*75*Exporting to USD")
        self.assertEqual(result[0], ProgressStepType.PROGRESS)
        self.assertEqual(result[1], "Exporting to USD")
        self.assertAlmostEqual(result[2], 0.75)

        # End/result message
        result = consumer.extract_line(f"{log_prefix}end*0*Success")
        self.assertEqual(result[0], ProgressStepType.END)
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], "Success")

        # DGN structured diagnostics can include wildcard patterns and empty messages.
        for code, message in ((2, "Error [25]: model *part*"), (0, ""), (1, "Failure [2]: C:/a*b.dgn")):
            self.assertEqual(
                consumer.extract_line(f"{log_prefix}*end*{code}*{message}\r\n"),
                [ProgressStepType.END, code, message],
            )

        # Unknown due to unrecognized content
        result = consumer.extract_line(f"{log_prefix}foo*bar*baz")
        self.assertEqual(result, [ProgressStepType.UNKNOWN])

    async def test_run_scene_opt_applies_stage_metrics_with_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "stage.usda"
            config_path = temp_path / "optimizer.json"

            stage = Usd.Stage.CreateNew(str(output_path))
            UsdGeom.SetStageMetersPerUnit(stage, 0.001)
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
            stage.GetRootLayer().Save()
            stage = None

            with open(config_path, "w") as config_file:
                json.dump([{"operation": "pruneLeaves", "paths": [], "pruneMode": 1}], config_file)

            run_scene_opt(
                str(output_path),
                sceneOpGenerateUVs=False,
                convertHidden=True,
                sceneOpConfig=str(config_path),
                sceneOpMetersPerUnit=1.0,
                sceneOpUpAxis=2,
            )

            stage = Usd.Stage.Open(str(output_path))
            self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage), 1.0)
            self.assertEqual(UsdGeom.GetStageUpAxis(stage), UsdGeom.Tokens.z)

    async def test_run_scene_opt_skips_stage_when_no_operations_requested(self):
        with patch("omni.kit.converter.common.common._do_run_scene_opt") as do_run_scene_opt:
            run_scene_opt(
                "unused.usda",
                sceneOpGenerateUVs=False,
                convertHidden=True,
                sceneOpMetersPerUnit=0.0,
                sceneOpUpAxis=0,
            )

        do_run_scene_opt.assert_not_called()

    async def test_run_scene_opt_forwards_requested_operations(self):
        default_args = {
            "sceneOpGenerateUVs": False,
            "convertHidden": True,
            "sceneOpConfig": "",
            "sceneOpMetersPerUnit": 0.0,
            "sceneOpUpAxis": 0,
        }
        requested_operations = {
            "config": {"sceneOpConfig": "optimizer.json"},
            "generate_uvs": {"sceneOpGenerateUVs": True},
            "remove_hidden": {"convertHidden": False},
            "meters_per_unit": {"sceneOpMetersPerUnit": 1.0},
            "up_axis": {"sceneOpUpAxis": 2},
            "multiple": {
                "sceneOpGenerateUVs": True,
                "convertHidden": False,
                "sceneOpMetersPerUnit": 0.01,
                "sceneOpUpAxis": 1,
            },
        }

        for operation, overrides in requested_operations.items():
            with self.subTest(operation=operation):
                args = default_args | overrides
                with patch("omni.kit.converter.common.common._do_run_scene_opt") as do_run_scene_opt:
                    run_scene_opt("output.usda", **args)

                do_run_scene_opt.assert_called_once_with(output_path="output.usda", **args)
