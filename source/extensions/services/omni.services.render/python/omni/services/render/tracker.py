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
import math
import os
import socket
import time
from typing import List, Optional

import carb
import carb.settings
import carb.tokens
from omni.kit.capture.viewport.capture_progress import CaptureProgress, CaptureStatus
from omni.kit.capture.viewport.extension import CaptureExtension
from omni.resourcemonitor import _resourceMonitor as rm
from omni.services.facilities.monitoring.metrics.facilities import MetricsFacility
from omni.services.facilities.monitoring.progress.facilities import ProgressFacility

from .file_manager import FileManager, MaxBadFilesError
from .file_tasks import FSFileTask, NucleusFileTask, S3FileTask

_agent_host = socket.getfqdn()

_render_buckets = (
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1,
    5,
    10,
    15,
    20,
    25,
    30,
    40,
    50,
    60,
    90,
    2 * 60,
    3 * 60,
    4 * 60,
    5 * 60,
    6 * 60,
    7 * 60,
    8 * 60,
    9 * 60,
    10 * 60,
    15 * 60,
    20 * 60,
    25 * 60,
    30 * 60,
    45 * 60,
    60 * 60,
    75 * 60,
    90 * 60,
    120 * 60,
    150 * 60,
    180 * 60,
    float("inf"),
)


class MissingUploadFramesError(Exception):
    """Raised when not all frames were uploaded"""


class RenderTracker(object):
    """Track and handle rendering progress"""

    def __init__(
        self,
        tmp_path: str,
        output_path: str,
        metrics: MetricsFacility,
        progress_facility: ProgressFacility,
        usd_file: str,
        capture_nth_frame: int,
        render_camera: str,
        capture_progress: CaptureProgress,
        interval: int = 60,
        max_bad_frame_threshold: int = 0,
        bad_frame_size_threshold: float = 0.0,
        capture_instance: CaptureExtension = None,
        error_on_missing_upload_frames: bool = True,
        capture_done: Optional[asyncio.Event] = None,
        filesync_done: Optional[asyncio.Event] = None,
    ):
        self._tmp_path = tmp_path
        self._output_path = output_path
        self._metrics = metrics
        self._progress_facility = progress_facility
        self._usd_file = usd_file
        self._frame_count = -1
        self._capture_nth_frame = capture_nth_frame
        self._render_camera = render_camera
        self._capture_progress = capture_progress
        self._capture_instance = capture_instance
        self._capture_done = capture_done
        self._filesync_done = filesync_done

        self._file_manager = FileManager(
            bad_frame_size_threshold,
            max_bad_frame_threshold,
            concurrency=1,
            capture_done=capture_done,
            filesync_done=filesync_done,
        )
        self._file_manager.start()
        self._aborted = False

        self._resource_monitor = rm.acquire_resource_monitor_interface()
        self._interval = interval
        self._last_check_time = time.time()
        self._memory_gauge = metrics.gauge("mem_available", "Available memory", labelnames=("stage",), unit="bytes")
        self._error_on_missing_upload_frames = error_on_missing_upload_frames

        gpu_count = 0
        # TODO: See if there is a more official way to get the GPU count.
        while self._resource_monitor.get_total_device_memory(gpu_count) > 0:
            gpu_count += 1

        # TODO: refactor this to be a single GPU but BCP does not support labels at the moment so creating a gauge per GPU.
        self._gpu_gauges = [
            metrics.gauge(
                f"gpu_memory_available_{index}",
                f"Available memory for GPU {index}",
                labelnames=("stage",),
                unit="bytes",
            )
            for index in range(gpu_count)
        ]

    @property
    def aborted(self) -> bool:
        """Indicates if rendering has been aborted"""
        return self._aborted

    def _upload_frames(self, files):
        if self._output_path.startswith("s3://"):
            task_cls = S3FileTask
        elif self._output_path.startswith("omniverse://"):
            task_cls = NucleusFileTask
        else:
            task_cls = FSFileTask

        tasks = []
        for filename in files:
            input_path = os.path.join(self._tmp_path, filename)
            tasks.append(task_cls(input_path, self._output_path))

        try:
            self._file_manager.put_tasks(tasks)
        except MaxBadFilesError:
            self._aborted = True

    def _calculate_frame_count(self, total_frame_count: int) -> None:
        if self._capture_nth_frame <= 1:
            self._frame_count = total_frame_count
        else:
            self._frame_count = math.floor(total_frame_count / self._capture_nth_frame)

    def on_capture_progress(
        self,
        capture_status: int,
        progress: Optional[float],
        elapsed_time: str,
        estimated_time_remaining: str,
        current_frame_time: str,
        average_frame_time: str,
        encoding_time: str,
        frame_counter: Optional[int] = None,
        total_frame_count: Optional[int] = None,
    ) -> None:
        # get the frame count from the first progress callback
        # we take the advantage of the callback to get the total number of frames to calculate the numbers to capture
        if -1 == self._frame_count:
            self._calculate_frame_count(total_frame_count)

        new_files = self._file_manager.list_new_frames(self._tmp_path)
        # Upload frames resulting from the rendering:
        if new_files:
            self._upload_frames(new_files)

        # Record updated metrics information from the new rendering data available:
        if time.time() > self._last_check_time + self._interval:
            self._last_check_time = time.time()
            self._record_metrics(current_frame_time)
            self._log_update(frame_counter)

        # Record updated progress information from the new rendering data available:
        if capture_status == CaptureStatus.CAPTURING and frame_counter is not None and total_frame_count is not None:
            self._record_progress(
                frame_counter=frame_counter,
                total_frame_count=total_frame_count,
                progress=progress,
            )
        elif capture_status == CaptureStatus.NONE and frame_counter == 0:
            self._record_progress(
                frame_counter=total_frame_count,
                total_frame_count=total_frame_count,
                progress=1.0,
            )

    def _log_update(self, current_frame_count: int):
        """
        Update logs with an update on the rendering status.

        Args:
            current_frame_count (int): Index of the frame currently being rendered.

        Returns:
            None

        """
        # TODO: re-enable after OM-43301 is fixed.
        spp_iter = self._capture_progress.path_trace_iteration_num

        if self._capture_instance:
            spp_iter = self._capture_instance._sample_count

        frame_time = self._capture_progress.current_frame_time
        avg_time = self._capture_progress.average_frame_time
        carb.log_info(
            f"Processed samples {spp_iter} for frame {current_frame_count}. Elapsed frame time: {frame_time}, Average frame time: {avg_time}. Estimated time remaining: {self._capture_progress.estimated_time_remaining}"
        )

    def _record_metrics(self, frame_time: str) -> None:
        """
        Update metrics about the progress of the rendering task.

        Args:
            frame_time (int): Time elapsed for current frame.

        Returns:
            None

        """
        # TODO: we dig into protected methods of CaptureProgress to get floats instead of time strings. omni.kit.capture.viewport needs to be updated.
        try:
            frame_histo = self._metrics.histogram(
                "time_per_frame",
                "Time per frame for a given USD stage",
                labelnames=("stage", "agent", "camera"),
                buckets=_render_buckets,
                unit="seconds",
            )
            frame_histo.labels(stage=self._usd_file, agent=_agent_host, camera=self._render_camera).observe(
                self._capture_progress._current_frame_time
            )
        except Exception as exc:
            carb.log_warn(f"Error updating timing metrics: {str(exc)}")

        try:
            subframe_histo = self._metrics.histogram(
                "avg_time_per_subframe",
                "Average time per subframe for a given USD stage",
                labelnames=("stage", "agent", "camera"),
                buckets=_render_buckets,
                unit="seconds",
            )
            subframe_histo.labels(stage=self._usd_file, agent=_agent_host, camera=self._render_camera).observe(
                self._capture_progress._average_time_per_subframe
            )
        except Exception as exc:
            carb.log_warn(f"Error updating subframe timing metrics: {str(exc)}")

        try:
            iter_histo = self._metrics.histogram(
                "avg_time_per_iteration",
                "Average time per iteration for a given USD stage",
                labelnames=("stage", "agent", "camera"),
                buckets=_render_buckets,
                unit="seconds",
            )
            iter_histo.labels(stage=self._usd_file, agent=_agent_host, camera=self._render_camera).observe(
                self._capture_progress._average_time_per_subframe
            )
        except Exception as exc:
            carb.log_warn(f"Error updating subframe timing metrics: {str(exc)}")

        try:
            frame_count = self._metrics.counter(
                "rendered_frames",
                "Number of frames rendered for a given USD stage",
                labelnames=("stage", "agent", "camera"),
                unit="frames",
            )
            frame_count.labels(stage=self._usd_file, agent=_agent_host, camera=self._render_camera).inc()
        except Exception as exc:
            carb.log_warn(f"Error updating frame metrics: {str(exc)}")

        try:
            self._memory_gauge.labels(stage=self._usd_file).set(self._resource_monitor.get_available_host_memory())
        except Exception as exc:
            carb.log_warn(f"Error updating host memory metrics: {str(exc)}")

        for index, gauge in enumerate(self._gpu_gauges):
            try:
                gauge.labels(stage=self._usd_file).set(self._resource_monitor.get_available_device_memory(index))
            except Exception as exc:
                carb.log_warn(f"Error updating GPU memory metrics for GPU {index}: {str(exc)}")

    def _record_progress(self, frame_counter: int, total_frame_count: int, progress: Optional[float] = None) -> None:
        """
        Record information about the progress of the rendering task.

        .. note::

            It is possible for the ``progress`` value not to match the ratio of ``frame_counter`` over
            ``total_frame_count``. This could be the case for progressive rendering tasks, where the overall progress
            could increase over time, despite the same frame still being rendered through 2 successive calls. An example
            of such cases can happen for progressive renderers, where the image progressively converges while the same
            frame is being rendered.

        Args:
            frame_counter (int): Index of the frame currently being rendered.
            total_frame_count (int): Total number of frames to record during the task.
            progress (Optional[float]): Overall progress of the rendering task (between 0.0 and 1.0).

        Returns:
            None

        """
        if progress is None:
            if total_frame_count == 0:
                progress = 0.0
            else:
                progress = float(frame_counter) / float(total_frame_count)

        self._progress_facility.set_progress(
            current_step_index=frame_counter,
            total_step_count=total_frame_count,
            progress=progress,
            status_message=f"Rendering frame {frame_counter} of {total_frame_count}",
            time_remaining=self._capture_progress._estimated_time_remaining,
        )

    def _unfudge_time(self, time_stamp: str) -> float:
        time_split_hours = time_stamp.split("h")
        hours = 0
        if len(time_split_hours) > 1:
            hours = int(time_split_hours[0])
            time_stamp = time_split_hours[1]

        time_split_minutes = time_stamp.split("m")
        minutes = 0
        if len(time_split_minutes) > 1:
            minutes = int(time_split_minutes[0])
            time_stamp = time_split_minutes[1]

        seconds = float(time_stamp.replace("s", "").strip())

        return hours * 3600 + minutes * 60 + seconds

    async def finalize_frame_sync(self, timeout: int = 60):
        new_files = self._file_manager.list_new_frames(self._tmp_path)
        if not new_files:
            return

        carb.log_info(f"Rendering has completed. The following frames have not yet been uploaded: {new_files}")
        self._upload_frames(new_files)

        # wait until the filsync is complete
        try:
            carb.log_info(f"waiting for the filesync to complete or timeout in {timeout}")
            await asyncio.wait_for(self._filesync_done.wait(), timeout=timeout)
            carb.log_info(f"filesync is complete")
        except asyncio.TimeoutError:
            carb.log_error(f"waiting for filesync timedout")

        if len(self._file_manager.processed_frames) < self._frame_count:
            msg = f"Not all frames could be uploaded: {self._file_manager.processed_frames}, expected frame count: {self._frame_count}"
            if self._error_on_missing_upload_frames:
                raise MissingUploadFramesError(msg)
            carb.log_error(msg)

    async def shutdown(self, timeout: int = 60):
        try:
            await asyncio.wait_for(self._file_manager.join(), timeout=timeout)
        except asyncio.TimeoutError:
            carb.log_warn(f"Wasn't able to join all tasks on task queue: {str(self._file_manager._task_queue)}")
        await self._file_manager.shutdown()
