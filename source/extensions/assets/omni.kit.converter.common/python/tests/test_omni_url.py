# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os

import omni.kit.test

from ..omni_client_wrapper import OmniClientWrapper
from ..omni_url import OmniUrl
from ..test_utils.utils import get_ext_root_path, make_output_dir


class TestOmniUrl(omni.kit.test.AsyncTestCase):
    async def test_omniurl_with_spaces(self):
        """
        Test that OmniUrl can handle spaces in paths
        """
        file_url = None
        if os.name == "nt":
            file_url = OmniUrl("file:/C:/foo%20spaces")
        else:
            file_url = OmniUrl("file:/home/USERNAME/foo%20spaces")
        local_file_path = file_url.get_local_file().as_posix()
        if os.name == "nt":
            self.assertTrue(local_file_path == "C:/foo spaces")
        else:
            self.assertTrue(local_file_path == "/home/USERNAME/foo spaces")

    async def test_get_local_file(self):
        """
        Test OmniUrl get_local_file feature
        """
        # create test file
        test_dir = make_output_dir("test_url_functions")
        test_file = test_dir / "test.txt"
        test_file_path = None
        if os.name == "nt":
            test_file_path = f"file:/{str(test_file)}"
        else:
            test_file_path = f"file:{str(test_file)}"
        file_url = OmniUrl(test_file_path)
        await OmniClientWrapper.write(str(test_file), b"")

        # test sync and async get_local_file calls
        self.assertEqual(str(file_url.get_local_file()), str(test_file))
        self.assertEqual(str(await file_url.get_local_file_async()), str(test_file))

    async def test_url_with_funcs(self):
        test_dir = get_ext_root_path()
        test_file = test_dir / "test.txt"
        file_url = OmniUrl(str(test_file))

        # test url_with_suffix
        file_url = file_url.url_with_suffix(".tmp2.txt")
        self.assertEqual(file_url.full_suffix, ".tmp2.txt")

        # test url_with_name
        file_url = file_url.url_with_name("test.tmp3.txt")
        self.assertEqual(file_url.full_suffix, ".tmp3.txt")

        # test url_with_path
        identical_file_url = file_url.url_with_path(file_url.path)
        self.assertEqual(identical_file_url.path, file_url.path)

    async def test_url_properties(self):
        test_dir = make_output_dir("test_url_properties")

        # test writable / exists properties
        url = OmniUrl(str(test_dir))
        self.assertFalse(url.writeable)
        self.assertTrue(url.exists)

        invalid_file = test_dir / "nonexisting.txt"
        invalid_file_url = OmniUrl(invalid_file)
        self.assertFalse(invalid_file_url.exists)
        self.assertFalse(invalid_file_url.writeable)

        # test suffix, full_suffix, stem, name, path properties
        file_name = "test.tmp.txt"
        dir_url = OmniUrl(test_dir)
        valid_file_url = dir_url / file_name
        await OmniClientWrapper.write(str(valid_file_url.path), b"")
        self.assertTrue(valid_file_url.writeable)
        self.assertEqual(valid_file_url.suffix, ".txt")
        self.assertEqual(valid_file_url.full_suffix, ".tmp.txt")
        self.assertEqual(valid_file_url.stem, "test.tmp")
        self.assertEqual(valid_file_url.name, file_name)

        parent_url = valid_file_url.parent_url
        self.assertEqual(parent_url.name, "test_url_properties")
