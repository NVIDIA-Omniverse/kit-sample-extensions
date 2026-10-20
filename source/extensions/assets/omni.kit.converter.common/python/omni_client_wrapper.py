# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import traceback

import carb
import omni.client


def _encode_content(content):
    if type(content) == str:
        payload = bytes(content.encode("utf-8"))
    elif type(content) != type(None):
        payload = bytes(content)
    else:
        payload = bytes()

    return payload


class OmniClientWrapper:
    """
    Helper class based on omni.client library
    """

    @staticmethod
    async def exists(path):
        """
        Asynchronously Retrieve information about a single item

        Args:
            path: file path

        Returns:
            boolean: true if the result is OK
        """
        try:
            result, entry = await omni.client.stat_async(path)
            return result == omni.client.Result.OK
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False

    @staticmethod
    def exists_sync(path):
        """
        Retrieve information about a single item and wait for the result

        Args:
            path: file path

        Returns:
            boolean: true if the result is OK
        """
        try:
            result, entry = omni.client.stat(path)
            return result == omni.client.Result.OK
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False

    @staticmethod
    async def write(path: str, content):
        """
        Asynchronously write a file

        Args:
            path: output file path

        Returns:
            boolean: true if file was written successfully
        """
        carb.log_info(f"Writing {path}...")
        try:
            result = await omni.client.write_file_async(path, _encode_content(content))
            if result != omni.client.Result.OK:
                carb.log_error(f"Cannot write {path}, error code: {result}.")
                return False
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
            return False
        finally:
            carb.log_info(f"Writing {path} done...")

        return True

    @staticmethod
    async def copy(src_path: str, dest_path: str):
        """
        Asynchronously copy an item from src_url to dst_url and wait for the result

        Args:
            src_path: input file to copy
            dest_path: destination path to copy to

        Returns:
            boolean: true if successfully copied to destination
        """
        carb.log_info(f"Coping from {src_path} to {dest_path}...")
        try:
            await omni.client.delete_async(dest_path)
            result = await omni.client.copy_async(src_path, dest_path)
            if result != omni.client.Result.OK:
                carb.log_error(f"Cannot copy from {src_path} to {dest_path}, error code: {result}.")
                return False
            else:
                return True
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))

        return False

    @staticmethod
    def copy_sync(src_path: str, dest_path: str):
        """
        Copy an item from src_url to dst_url and wait for the result

        Args:
            src_path: input file to copy
            dest_path: destination path to copy to

        Returns:
            boolean: true if successfully copied to destination
        """
        carb.log_info(f"Coping from {src_path} to {dest_path}...")
        result = omni.client.copy(src_path, dest_path)
        return result == omni.client.Result.OK or result == omni.client.Result.ERROR_ALREADY_EXISTS

    @staticmethod
    async def read(src_path: str):
        """
        Asynchronously read a file
        """
        carb.log_info(f"Reading {src_path}...")
        try:
            result, version, content = await omni.client.read_file_async(src_path)
            if result == omni.client.Result.OK:
                return memoryview(content).tobytes()
            else:
                carb.log_error(f"Cannot read {src_path}, error code: {result}.")
        except Exception as e:
            traceback.print_exc()
            carb.log_error(str(e))
        finally:
            carb.log_info(f"Reading {src_path} done...")

        return None

    @staticmethod
    async def create_folder(path):
        """
        Asynchronously create a folder
        """
        carb.log_info(f"Creating dir {path}...")
        result = await omni.client.create_folder_async(path)
        return result == omni.client.Result.OK or result == omni.client.Result.ERROR_ALREADY_EXISTS

    @staticmethod
    def create_folder_sync(path):
        """
        Create a folder
        """
        carb.log_info(f"Creating dir {path}...")
        result = omni.client.create_folder(path)
        return result == omni.client.Result.OK or result == omni.client.Result.ERROR_ALREADY_EXISTS
