# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
from tempfile import TemporaryDirectory

import carb.settings
import omni.kit.test
from omni.services.render.file_tasks import BaseFileTask, FileCopyError, OmniClientFileTask


class TestTaskTracker(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._settings = carb.settings.get_settings_interface()

    async def tearDown(self) -> None:
        self._settings.destroy_item("exts/omni.services.render/append_task_id")
        self._settings.destroy_item("exts/omni.services.farm.agent.runner/assigned_task")

    def _create_task(self) -> BaseFileTask:
        return OmniClientFileTask("dummy", "/foo/bar")

    async def test_append_task_id(self):
        self._settings.set_bool("exts/omni.services.render/append_task_id", True)
        self._settings.set("exts/omni.services.farm.agent.runner/assigned_task", "1234-5678-910")

        task = self._create_task()

        res = task._calculate_output_path("/foo/bar")
        self.assertEquals("/foo/bar/1234-5678-910", res)

    async def test_append_task_id_no_id(self):
        self._settings.set_bool("exts/omni.services.render/append_task_id", True)

        task = self._create_task()

        res = task._calculate_output_path("/foo/bar")
        self.assertEquals("/foo/bar", res)

    async def test_append_task_id_not_append(self):
        self._settings.set_bool("exts/omni.services.render/append_task_id", False)
        self._settings.set("exts/omni.services.farm.agent.runner/assigned_task", "1234-5678-910")

        task = self._create_task()

        res = task._calculate_output_path("/foo/bar")
        self.assertEquals("/foo/bar", res)

    async def test_append_task_id_separator(self):
        self._settings.set_bool("exts/omni.services.render/append_task_id", True)
        self._settings.set("exts/omni.services.farm.agent.runner/assigned_task", "1234-5678-910")

        task = self._create_task()

        res = task._calculate_output_path("/foo/bar", separator="\\")
        self.assertEquals("/foo/bar\\1234-5678-910", res)


class TestOmniFileTask(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._tmp_dir = TemporaryDirectory()
        self._tmp_output_dir = TemporaryDirectory()

    async def tearDown(self) -> None:
        self._tmp_dir.cleanup()
        self._tmp_output_dir.cleanup()

    async def test_copy_new_file(self):
        filename = "test_file.txt"
        path = os.path.join(self._tmp_dir.name, filename)
        Path(path).touch()

        task = OmniClientFileTask(path, self._tmp_output_dir.name)
        await task.run()

        output_file = os.path.join(self._tmp_output_dir.name, filename)
        self.assertTrue(os.path.exists(output_file))

    async def test_overwrite_file(self):
        filename = "test_file.txt"
        path = os.path.join(self._tmp_dir.name, filename)
        Path(path).touch()

        output_file = os.path.join(self._tmp_output_dir.name, filename)
        Path(output_file).touch()

        task = OmniClientFileTask(path, self._tmp_output_dir.name)
        await task.run()

        self.assertTrue(os.path.exists(output_file))


class TestOmniFileTask_Error(omni.kit.test.AsyncTestCase):

    async def test_copy_non_existant_file(self):
        filename = "test_file.txt"
        path = os.path.join("/foo/bar", filename)
        task = OmniClientFileTask(path, "/foo/bar")

        with self.assertRaises(FileCopyError):
            await task.run()
