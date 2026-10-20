# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os

import omni.client
import omni.client.utils as clientutils


class PathUtils:
    @staticmethod
    def get_filename_from_url(url):
        u = omni.client.break_url(url)
        return os.path.basename(u.path)

    @staticmethod
    def get_directory_from_url(url):
        u = omni.client.break_url(url)
        return os.path.dirname(u.path)

    @staticmethod
    def get_extension_from_url(url):
        u = omni.client.break_url(url)
        _, ext = os.path.splitext(u.path)

        return ext

    @staticmethod
    async def list_folder_async(folder_path):
        def compute_absolute_path(base_path, is_base_path_folder, path, is_path_folder):
            base_path = clientutils.normalize_url(base_path)
            path = clientutils.normalize_url(path)

            if is_base_path_folder and not base_path.endswith("/"):
                base_path += "/"

            if is_path_folder and not path.endswith("/"):
                path += "/"

            return clientutils.make_absolute_url_if_possible(base_path, path)

        absolute_paths = []
        relative_paths = []
        result, entry = await omni.client.stat_async(folder_path)
        if result == omni.client.Result.OK and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
            is_folder = True
        else:
            is_folder = False

        if not is_folder:
            absolute_paths = [folder_path]
            relative_paths = [os.path.basename(folder_path)]
        else:
            if not folder_path.endswith("/"):
                folder_path += "/"

            folder_queue = [folder_path]
            while len(folder_queue) > 0:
                folder = folder_queue.pop(0)
                result, entries = await omni.client.list_async(folder)
                if result != omni.client.Result.OK:
                    break
                folders = set((e.relative_path for e in entries if e.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN))
                for f in folders:
                    folder_queue.append(compute_absolute_path(folder, True, f, False))
                files = set((e.relative_path for e in entries if not e.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN))
                for file in files:
                    absolute_path = compute_absolute_path(folder, True, file, False)
                    absolute_paths.append(absolute_path)
                    relative_path = clientutils.make_relative_url_if_possible(folder_path, absolute_path)
                    relative_paths.append(relative_path)

        return absolute_paths, relative_paths
