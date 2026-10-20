# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import random
import shutil
import tempfile
from pathlib import Path

import omni.kit.test
from omni import ui
from omni.kit import ui_test
from omni.kit.test.async_unittest import AsyncTestCase

from ..omni_client_wrapper import OmniClientWrapper


class TestFileRename(AsyncTestCase):
    """Testing OmniClientWrapper behavior"""

    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    def _prepare_test_dir(self, temp_dir, temp_file):
        # make sure we start off clean
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        os.makedirs(temp_dir)

        with open(os.path.join(temp_dir, temp_file), "w") as _:
            pass

    async def test_client_wrapper(self):
        """Testing renaming a file."""
        temp_dir = os.path.join(tempfile.gettempdir(), f"tmp{random.randint(0, int('0xffff', 16))}")
        temp_dir = str(Path(temp_dir).resolve())
        filename = "temp.mdl"
        self._prepare_test_dir(temp_dir, filename)

        test_file = os.path.join(temp_dir, filename)
        test_folder = os.path.join(temp_dir, "test_folder")
        await OmniClientWrapper.create_folder(test_folder)
        self.assertTrue(OmniClientWrapper.exists_sync(test_folder))
        test_folder_exist = await OmniClientWrapper.exists(test_folder)
        self.assertTrue(test_folder_exist)
        await OmniClientWrapper.write(test_file, "test")
        read_res = await OmniClientWrapper.read(test_file)
        self.assertEqual(str(read_res.decode()), "test")
        await OmniClientWrapper.copy(test_file, os.path.join(test_folder, filename))
        self.assertTrue(OmniClientWrapper.exists_sync(os.path.join(test_folder, filename)))
        # Cleanup
        shutil.rmtree(temp_dir)
