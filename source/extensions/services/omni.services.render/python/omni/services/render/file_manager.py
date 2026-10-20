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
import time
from typing import List, Optional

import carb

from .file_tasks import BaseFileTask


class MaxBadFilesError(Exception):
    """Raised when a maximum of bad files has been found"""


class FileManager(object):
    """Manages the processing of file tasks asynchroniously"""

    def __init__(
        self,
        bad_file_size_threshold: float,
        max_bad_files: int,
        concurrency: int = 1,
        capture_done: Optional[asyncio.Event] = None,
        filesync_done: Optional[asyncio.Event] = None,
    ) -> None:
        """
        Args:
            bad_file_size_threshold (float): Minimum size of a file for it to be considered valid.
            max_bad_files (int): Maximum amount of bad files before triggering an error.

        Kwargs:
            concurrency (int): Amount of workers to spawn.
        """
        super().__init__()
        self._concurrency = concurrency
        self._finished = asyncio.Event()
        self._task_queue = asyncio.Queue()
        self._last_check_time = time.time()
        self._capture_done = capture_done
        self._filesync_done = filesync_done

        self._bad_frames = []
        self._bad_file_size_threshold = bad_file_size_threshold
        self._max_bad_files = max_bad_files

        self._active_workers = []
        self._processed_frames = []

    @property
    def processed_frames(self) -> List[str]:
        return self._processed_frames

    @property
    def is_empty(self) -> bool:
        """Check if all tasks have finished processing"""
        return self._task_queue.empty()

    def reset_frames(self, frames: List[str]) -> None:
        """
        Remove a list of frames from the list of processed frames so they can be resubmitted.

        Args:
            frames (List[str]): List of frames to remove
        """
        for frame in frames:
            self._processed_frames.remove(frame)

    def list_new_frames(self, input_path: str) -> List[str]:
        """
        List new frames for a given input path

        Args:
            input_path (str): Source path
        """
        new_frames = list(set(os.listdir(input_path)) - set(self.processed_frames))

        resubmitted_paths = []
        for path in self.processed_frames:
            if os.path.getmtime(os.path.join(input_path, path)) > self._last_check_time:
                resubmitted_paths.append(path)

        self.reset_frames(resubmitted_paths)
        new_frames.extend(resubmitted_paths)

        self._last_check_time = time.time()

        return new_frames

    def start(self):
        """Start the workers."""
        for _ in range(self._concurrency):
            self._active_workers.append(asyncio.ensure_future(self._run()))

    def _check_for_bad_frames(self, files: List[str]):
        """
        Check a list of files against the minimum file size threshold.

        Args:
            files (List[str]): List of files to check

        Raises:
            MaxBadFilesError: Raised when too many bad files have been found.
        """
        for filename in files:
            if filename in self._bad_frames:
                continue

            if os.path.exists(filename) and os.stat(filename).st_size < self._bad_file_size_threshold:
                self._bad_frames.append(filename)

        if len(self._bad_frames) > self._max_bad_files:
            carb.log_error(
                f"Too many frames detected under the {self._bad_file_size_threshold} bytes file threshold. Aborting render. f{self._bad_frames}"
            )
            raise MaxBadFilesError()

    def put_tasks(self, tasks: List[BaseFileTask]):
        """
        Queue up tasks for processing

        Args:
            tasks (List[BaseFileTask]): List of tasks to enqueue.

        Raises:
            MaxBadFilesError: Raised when too many bad files have been found.
        """
        files = [task.input_path for task in tasks]
        self._check_for_bad_frames(files)

        for task in tasks:
            self._task_queue.put_nowait(task)

    async def _run(self):
        while not self._finished.is_set():
            await self._process_task()

    async def _process_task(self):
        """Process a task from the task queue"""
        try:
            task: BaseFileTask = await asyncio.wait_for(self._task_queue.get(), timeout=1)

            # Handle any potential race condition and avoid processing frames twice.
            if task.input_path in self._processed_frames:
                try:
                    self._task_queue.task_done()
                except ValueError:
                    pass
                return

            success = False
            try:
                await task.run()
                self._processed_frames.append(task.input_path)
                success = True
            finally:
                carb.log_info(f"Processed {task.input_path}. Was task successful: {success}")
                self._task_queue.task_done()
        except asyncio.TimeoutError:
            # check if capturing is complete, then notify tracker that all files are processed.
            if self._capture_done and self._capture_done.is_set():
                carb.log_info(f"Processing complete. {len(self._processed_frames)} tasks successfull")
                if self._filesync_done:
                    self._filesync_done.set()
        except Exception as exc:
            carb.log_warn(f"Failed to process task: {str(type(exc))}, {str(exc)}")

    async def shutdown(self):
        """
        Shutdown all workers.

        Args:
            timeout (int): Time after which all tasks will be forced cancelled.
        """
        self._finished.set()
        # Give workers time to shutdown by spinning the loop
        await asyncio.sleep(2)

        for worker in self._active_workers:
            try:
                worker.cancel()
            except Exception as exc:
                carb.log_warn(f"Failed to cancel worker cleanly {worker}: {str(exc)}")

        carb.log_info(f"File manager was shutdown. The following frames were processed: {str(self._processed_frames)} ")
        if not self.is_empty:
            carb.log_warn(f"File manager was shutdown. Some frames were not processed: {str(self._task_queue)}")

    async def join(self):
        """
        Wait for all tasks to complete
        """
        await self._task_queue.join()
