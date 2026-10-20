## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import asyncio
import os
from logging import raiseExceptions
from unittest.mock import patch

from carb.tokens import get_tokens_interface
from omni.kit.asset_converter import OmniClientWrapper
from omni.kit.test import AsyncTestCase


class TestClientWrapper(AsyncTestCase):
    async def test_omni_client_wrapper(self):
        # we need replace at the end because ${omni_data} resolves to <repo_dir>/_build/linux-x86_64/release//data
        # with two slashes before data for some reason
        root = get_tokens_interface().resolve("${omni_data}").replace("//", "/")
        test_path = f"{root}/_testoutput/test"
        fake_folder_path = f"{root}/_testoutput/fake"
        self.assertTrue(await OmniClientWrapper.create_folder(test_path))

        self.assertTrue(await OmniClientWrapper.exists(test_path))
        self.assertTrue(OmniClientWrapper.exists_sync(test_path))

        self.assertEqual(OmniClientWrapper.parent(test_path).lower(), f"{root}/_testoutput".lower())

        self.assertTrue(OmniClientWrapper.writeable(test_path))
        self.assertFalse(OmniClientWrapper.writeable(f"{fake_folder_path}/test"))
        self.assertTrue(await OmniClientWrapper.writeable_async(test_path))
        self.assertFalse(await OmniClientWrapper.writeable_async(f"{fake_folder_path}/test"))

        self.assertTrue(await OmniClientWrapper.write(f"{test_path}/test_file.txt", "This is a test"))

        self.assertTrue(await OmniClientWrapper.copy(f"{test_path}/test_file.txt", f"{test_path}/test_file_copy.txt"))

        self.assertIsNotNone(await OmniClientWrapper.read(f"{test_path}/test_file_copy.txt"))
        with patch("carb.log_error"), patch("omni.client.stat_async") as mock_exception:
            mock_exception.side_effect = IOError()
            self.assertFalse(await OmniClientWrapper.exists(fake_folder_path))
        with patch("carb.log_error"), patch("omni.client.stat") as mock_exception:
            mock_exception.side_effect = IOError()
            self.assertFalse(OmniClientWrapper.exists_sync(fake_folder_path))
        with patch("carb.log_error"), patch("omni.client.copy_async") as mock_exception:
            mock_exception.side_effect = IOError()
            # self.assertFalse(await OmniClientWrapper.write(f"{fake_folder_path}/test_file.txt", "This is a test"))
            self.assertFalse(
                await OmniClientWrapper.copy(f"{fake_folder_path}/test_file.txt", f"{test_path}/test_file_copy.txt")
            )
        with patch("carb.log_error"), patch("omni.client.read_file_async") as mock_exception:
            mock_exception.side_effect = IOError()
            self.assertIsNone(await OmniClientWrapper.read(f"{fake_folder_path}/test_file_copy.txt"))
        with patch("carb.log_error"), patch("omni.client.write_file_async") as mock_exception:
            mock_exception.side_effect = IOError()
            self.assertFalse(await OmniClientWrapper.write(f"{fake_folder_path}/test_file.txt", "This is a test"))
