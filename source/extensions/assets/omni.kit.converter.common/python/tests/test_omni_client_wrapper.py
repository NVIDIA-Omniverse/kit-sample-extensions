# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.test

from ..omni_client_wrapper import OmniClientWrapper
from ..test_utils.utils import make_output_dir


class TestOmniClientWrapper(omni.kit.test.AsyncTestCase):
    async def test_omni_client_wrapper_create_folder(self):
        test_dir = make_output_dir("test_omni_client_wrapper_create_folder")
        # check sync calls
        new_dir = test_dir / "new_dir"
        success = OmniClientWrapper.create_folder_sync(str(new_dir))
        exists = OmniClientWrapper.exists_sync(str(new_dir))
        self.assertTrue(exists and success)

        # check async calls
        new_dir2 = test_dir / "new_dir2"
        success = await OmniClientWrapper.create_folder(str(new_dir2))
        exists = await OmniClientWrapper.exists(str(new_dir2))
        self.assertTrue(exists and success)

    async def test_omni_client_wrapper_copy_folder(self):
        test_dir = make_output_dir("test_omni_client_wrapper_copy_folder")
        new_dir = test_dir / "new_dir"
        success = OmniClientWrapper.create_folder_sync(str(new_dir))
        self.assertTrue(success)
        # check sync calls
        new_dir2 = test_dir / "new_dir2"
        success = OmniClientWrapper.copy_sync(str(new_dir), str(new_dir2))
        exists = OmniClientWrapper.exists_sync(str(new_dir2))
        self.assertTrue(exists and success)

        # check async calls
        new_dir3 = test_dir / "new_dir3"
        success = await OmniClientWrapper.copy(str(new_dir), str(new_dir3))
        exists = await OmniClientWrapper.exists(str(new_dir3))
        self.assertTrue(exists and success)

        # test error handling
        nonexisting_dir = test_dir / "nonexistingfolder"
        success = await OmniClientWrapper.copy(str(nonexisting_dir), str(nonexisting_dir))
        self.assertFalse(success)

    async def test_omni_client_wrapper_read_write(self):
        test_dir = make_output_dir("test_omni_client_wrapper_read_write")
        file_path = test_dir / "test.txt"
        success = await OmniClientWrapper.write(str(file_path), "file_content")
        self.assertTrue(success)
        content = await OmniClientWrapper.read(str(file_path))
        self.assertEqual(content, b"file_content")

        await OmniClientWrapper.write(str(file_path), b"1")
        content = await OmniClientWrapper.read(str(file_path))
        self.assertEqual(content, b"1")

        await OmniClientWrapper.write(str(file_path), None)
        content = await OmniClientWrapper.read(str(file_path))
        self.assertEqual(content, b"")

        # test error handling
        nonexistingfile = test_dir / "nonexistingfile.txt"
        content = await OmniClientWrapper.read(str(nonexistingfile))
        self.assertEqual(content, None)

        success = await OmniClientWrapper.write(str(test_dir), "file_content")
        self.assertFalse(success)
