# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import os
import platform
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import omni.kit.test
from omni.services.render.file_manager import FileManager, MaxBadFilesError
from omni.services.render.file_tasks import BaseFileTask


class DummyFileTask(BaseFileTask):

    async def run(self):
        return True


# Not checking for error logs as some tests are expected to raise.
class TestFileManager_FileSizeChecks(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._tmp_dir = TemporaryDirectory()

    async def tearDown(self) -> None:
        self._tmp_dir.cleanup()

    async def test_check_file_size_default_off(self):
        """Test that by default checks always pass"""
        path = os.path.join(self._tmp_dir.name, "zero-byte-file.txt")
        Path(path).touch()

        manager = FileManager(0.0, 0)
        manager._check_for_bad_frames([path])

        self.assertEqual(manager._bad_frames, [])

    async def test_check_file_size_too_small(self):
        """Test that a file too small is flagged"""
        path = os.path.join(self._tmp_dir.name, "zero-byte-file.txt")
        Path(path).touch()

        manager = FileManager(100.0, 5)
        manager._check_for_bad_frames([path])

        self.assertEqual(manager._bad_frames, [path])

    async def test_check_too_many_small_files(self):
        """Test that a file too small is flagged"""
        paths = []
        for idx in range(5):
            path = os.path.join(self._tmp_dir.name, f"zero-byte-file-{idx}.txt")
            Path(path).touch()
            paths.append(path)

        manager = FileManager(100.0, 1)
        with self.assertRaises(MaxBadFilesError):
            manager._check_for_bad_frames(paths)

    async def test_check_identical_file(self):
        """Test that adding the same invalid file does not trigger the threshold"""
        paths = []
        path = os.path.join(self._tmp_dir.name, "zero-byte-file.txt")
        Path(path).touch()
        paths.extend([path, path, path, path])

        manager = FileManager(100.0, 1)
        manager._check_for_bad_frames(paths)

        self.assertEqual(manager._bad_frames, [path])


class TestFileManager_TaskQueue(omni.kit.test.AsyncTestCase):

    async def test_process_tasks(self):
        """Validate that tasks are processed when taken from the work queue"""
        task_count = 3
        tasks = [
            DummyFileTask(input_path=f"dummy_file_{idx}", output_path="dummy_output_file") for idx in range(task_count)
        ]
        manager = FileManager(0, 0)
        manager.put_tasks(tasks)

        for _ in range(task_count):
            await manager._process_task()

        expected_files = [f"dummy_file_{idx}" for idx in range(task_count)]

        self.assertEqual(expected_files, manager._processed_frames)

    async def test_capture_complete_event(self):
        """Validate that all tasks are processed at the end and notify completion event"""
        task_count = 3
        tasks = [
            DummyFileTask(input_path=f"dummy_file_{idx}", output_path="dummy_output_file") for idx in range(task_count)
        ]
        capture_done = asyncio.Event()
        filesync_done = asyncio.Event()
        manager = FileManager(0, 0, 1, capture_done=capture_done, filesync_done=filesync_done)
        manager.put_tasks(tasks)
        capture_done.set()

        for _ in range(task_count):
            await manager._process_task()

        await manager._process_task()
        self.assertTrue(filesync_done.is_set())

    async def test_capture_complete_delay(self):
        """Validate that all tasks are processed at the end and notify completion event"""
        task_count = 3
        tasks = [
            DummyFileTask(input_path=f"dummy_file_{idx}", output_path="dummy_output_file") for idx in range(task_count)
        ]
        capture_done = asyncio.Event()
        filesync_done = asyncio.Event()
        manager = FileManager(0, 0, concurrency=1, capture_done=capture_done, filesync_done=filesync_done)
        manager.put_tasks(tasks)

        manager.start()

        capture_done.set()
        await filesync_done.wait()
        self.assertEqual(len(manager.processed_frames), 3)

    async def test_process_incomplete_timeout(self):
        """Validate that all tasks are not processed at the end and timeout hit"""
        task_count = 3
        tasks = [
            DummyFileTask(input_path=f"dummy_file_{idx}", output_path="dummy_output_file") for idx in range(task_count)
        ]
        capture_done = asyncio.Event()
        filesync_done = asyncio.Event()
        manager = FileManager(0, 0, concurrency=1, capture_done=capture_done, filesync_done=filesync_done)
        manager.put_tasks(tasks)

        manager.start()

        # if the capture_done is not set, we don't set the filesync_done and timeout
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(manager._filesync_done.wait(), timeout=1)

    async def test_worker_lifecycle(self):
        manager = FileManager(0, 0, concurrency=3)
        manager.start()
        self.assertEqual(len(manager._active_workers), 3)

        await manager.shutdown()
        for worker in manager._active_workers:
            self.assertTrue(worker.done())

    async def test_is_empty(self):
        task_count = 2
        tasks = [
            DummyFileTask(input_path=f"dummy_file_{idx}", output_path="dummy_output_file") for idx in range(task_count)
        ]
        manager = FileManager(0, 0)
        manager.put_tasks(tasks)

        self.assertFalse(manager.is_empty)

        for _ in range(task_count):
            await manager._process_task()

        self.assertTrue(manager.is_empty)

    async def test_enqueuing_same_file(self):
        task_count = 2
        tasks = [DummyFileTask(input_path="dummy_file", output_path="dummy_output_file") for idx in range(task_count)]
        manager = FileManager(0, 0)
        manager.put_tasks(tasks)

        for _ in range(task_count):
            await manager._process_task()

        expected_files = ["dummy_file"]

        self.assertEqual(expected_files, manager._processed_frames)

    async def test_enqueuing_same_file_after_reset(self):
        manager = FileManager(0, 0)
        manager.put_tasks([DummyFileTask(input_path="dummy_file", output_path="dummy_output_file")])

        await manager._process_task()
        expected_files = ["dummy_file"]
        self.assertEqual(expected_files, manager._processed_frames)

        manager.reset_frames(expected_files)
        self.assertEqual([], manager._processed_frames)

        manager.put_tasks([DummyFileTask(input_path="dummy_file", output_path="dummy_output_file")])
        await manager._process_task()
        self.assertEqual(expected_files, manager._processed_frames)

    async def test_getting_new_files(self):
        with TemporaryDirectory() as directory:
            manager = FileManager(0, 0)

            files = [f"file_{idx}.txt" for idx in range(3)]
            for file in files:
                Path(os.path.join(directory, file)).touch()

            listed_files = manager.list_new_frames(directory)
            self.assertEqual(sorted(files), sorted(listed_files))

    @unittest.skipUnless(platform.system().lower() == "linux", "Touch does not seem to work properly on Windows")
    async def test_getting_new_files_with_changes(self):
        with TemporaryDirectory() as directory:
            manager = FileManager(0, 0)

            files = [f"file_{idx}.txt" for idx in range(3)]
            for file in files:
                Path(os.path.join(directory, file)).touch()

            manager._processed_frames.extend(files)

            listed_files = manager.list_new_frames(directory)
            self.assertEqual(listed_files, [])

            await asyncio.sleep(0.1)
            Path(os.path.join(directory, files[0])).touch()

            listed_files = manager.list_new_frames(directory)
            self.assertEqual(listed_files, [files[0]])
