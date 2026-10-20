# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
from pathlib import Path

import aiohttp
import carb.tokens
import omni.kit.test
from omni.kit.converter.common.test_utils.utils import cleanup_file, get_repo_root_path

# TODO: expand file type tests.
TEST_DATA_PATH = (Path(get_repo_root_path() / "test_data" / "asset-converter-service")).as_posix()
TEST_FILE_PATH = (Path(os.path.join(TEST_DATA_PATH, "cube.gltf"))).as_posix()
OUTPUT_FILE_PATH = (Path(os.path.join(TEST_DATA_PATH, "cube.usd"))).as_posix()


def get_ext_root_path() -> Path:
    return Path(carb.tokens.get_tokens_interface().resolve("${omni.services.convert.asset}"))


class TestBaseProcess(omni.kit.test.AsyncTestCase):

    async def test_convert(self):
        """Test conversion service endpoint"""

        job_body = {
            "import_path": TEST_FILE_PATH,
            "output_path": OUTPUT_FILE_PATH,
            "converter_settings": {
                "bake_mdl_material": False,
                "baking_scales": False,
                "convert_fbx_to_y_up": False,
                "convert_fbx_to_z_up": False,
                "create_world_as_default_root_prim": True,
                "disabling_instancing": False,
                "embed_mdl_in_usd": True,
                "embed_textures": True,
                "export_hidden_props": False,
                "export_mdl_gltf_extension": False,
                "export_preview_surface": False,
                "export_separate_gltf": False,
                "ignore_animations": False,
                "ignore_camera": False,
                "ignore_flip_rotations": False,
                "ignore_light": False,
                "ignore_materials": False,
                "ignore_pivots": False,
                "ignore_unbound_bones": False,
                "keep_all_materials": False,
                "merge_all_meshes": False,
                "single_mesh": False,
                "smooth_normals": True,
                "support_point_instancer": False,
                "use_double_precision_to_usd_transform_op": False,
                "use_meter_as_world_unit": False,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 200)

        cleanup_file(OUTPUT_FILE_PATH)  # TODO: [OMPE-25573]: does not remove output file

    async def test_converter_service_non_existent_input_file(self):
        """Test service extension with an input file that does not exist."""

        test_output_path = Path(omni.kit.test.get_test_output_path()) / "test_converter_service_non_existent_input"
        test_file = Path(os.path.join(TEST_DATA_PATH, "foo.fbx"))
        test_output_file = test_output_path / (test_file.stem + ".usd")

        input_path = test_file.as_posix()
        output_path = test_output_file.as_posix()

        job_body = {"import_path": input_path, "output_path": output_path, "converter_settings": {}}

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 422)
            self.assertFalse(test_output_file.is_file())

    async def test_converter_service_invalid_type(self):
        """Test service returns 415 for unsupported extension type."""

        self.fail_on_log_error = False
        test_output_path = Path(omni.kit.test.get_test_output_path()) / "test_converter_service_invalid_type"
        test_file = Path(os.path.join(TEST_DATA_PATH, "cube.bar"))
        test_output_file = test_output_path / (test_file.stem + ".usd")

        job_body = {
            "import_path": test_file.as_posix(),
            "output_path": test_output_file.as_posix(),
            "converter_settings": {},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 415)

    async def test_converter_service_invalid_output(self):
        """Test service returns 415 for unsupported output type."""

        self.fail_on_log_error = False
        test_output_path = Path(omni.kit.test.get_test_output_path()) / "test_converter_service_invalid_type"
        test_output_file = os.path.join(test_output_path, "cube.foo")

        job_body = {"import_path": TEST_FILE_PATH, "output_path": test_output_file, "converter_settings": {}}

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 415)

    async def test_converter_service_bogus_key(self):
        """Test service returns 422: Unprocessable Content when payload key is incorrect."""

        self.fail_on_log_error = False

        job_body = {"bogus_path": TEST_FILE_PATH, "output_path": OUTPUT_FILE_PATH, "converter_settings": {}}

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 422)

    async def test_converter_service_missing_key(self):
        """Test service returns 422: Unprocessable Content when payload key is incorrect."""

        self.fail_on_log_error = False

        job_body = {"import_path": TEST_FILE_PATH, "output_path": OUTPUT_FILE_PATH}

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 422)

    async def test_convert_zip(self):
        """Test conversion with a zip file"""
        test_zip_path = Path(os.path.join(TEST_DATA_PATH, "cube.zip"))

        job_body = {
            "import_path": TEST_FILE_PATH,
            "output_path": OUTPUT_FILE_PATH,
            "converter_settings": {},
            "archive_path": test_zip_path.as_posix(),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 200)

    async def test_convert_tar(self):
        """Test conversion with a tar file"""
        test_tar_path = Path(os.path.join(TEST_DATA_PATH, "cube.tar"))

        job_body = {
            "import_path": TEST_FILE_PATH,
            "output_path": OUTPUT_FILE_PATH,
            "converter_settings": {},
            "archive_path": test_tar_path.as_posix(),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 200)

    async def test_convert_tar_gz(self):
        """Test conversion with a tar.gz file"""
        test_targz_path = Path(os.path.join(TEST_DATA_PATH, "cube.tar.gz"))

        job_body = {
            "import_path": TEST_FILE_PATH,
            "output_path": OUTPUT_FILE_PATH,
            "converter_settings": {},
            "archive_path": test_targz_path.as_posix(),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8011/convert/asset/process", json=job_body) as resp:
                self.assertEqual(resp.status, 200)
