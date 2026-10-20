# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Progress monitoring facility."""

import asyncio
from typing import Optional

import carb
from omni.kit.async_engine import run_coroutine
from omni.services import client
from omni.services.core import main
from omni.services.facilities import base


class ProgressFacility(base.Facility):
    """Progress monitoring facility."""

    def __init__(self):
        super().__init__()

        self._current_step_index: int = 0
        self._total_step_count: int = 0
        self._progress: float = 0.0
        self._status_message: str = ""
        self._time_remaining: float = 0.0

        self._client = client.AsyncClient("local://", app=main.get_app())

        self._commit_data_future: Optional[asyncio.Task] = None

    def stop(self) -> None:
        if self._commit_data_future:
            self._commit_data_future.cancel()
            self._commit_data_future = None

    def set_progress(
        self,
        current_step_index: int,
        total_step_count: int,
        progress: Optional[float] = None,
        status_message: Optional[str] = None,
        time_remaining: Optional[float] = None,
    ) -> None:
        """
        Set the progress information.

        Args:
            current_step_index (int): Index of the current step in the overall progress.
            total_step_count (int): Overall number of steps in the progress.
            progress (Optional[float]): Overall progress completion of the task (between 0.0 and 1.0). If no value is
                provided, the progress information will be computed based on the ratio of the current step index over
                the total number of steps.
            status_message (Optional[str]): Status message providing additional information about the current progress
                of the task.
            time_remaining (Optional[float]): Estimated time remaining in seconds until task completed.

        Returns:
            None

        """
        if progress is None:
            if self._total_step_count == 0:
                progress = 0.0
            else:
                progress = float(current_step_index) / float(total_step_count)

        self._current_step_index = current_step_index
        self._total_step_count = total_step_count
        self._progress = progress
        self._status_message = status_message
        self._time_remaining = time_remaining or 0.0

        # asset conversion code is done in a thread with no event loop which does not work with asyncio.ensure_future
        # here we use async_engine's run_coroutine function to run the coroutine in the main event loop
        # Commit the data to the internal persistence layer:
        run_coroutine(self._commit_data())

    async def _commit_data(self) -> None:
        """
        Commit the given progress information, effectively making it available to the store.

        Args:
            current_step_index (int): Index of the current step in the overall progress.
            total_step_count (int): Overall number of steps in the progress.
            progress (Optional[float]): Overall progress completion of the task (between 0.0 and 1.0). If no value is
                provided, the progress information will be computed based on the ratio of the current step index over
                the total number of steps.
            status_message (Optional[str]): Status message providing additional information about the current progress
                of the task.

        Returns:
            None

        """
        try:
            await self._client.progress.notify(
                current_step_index=self._current_step_index,
                total_step_count=self._total_step_count,
                progress=self._progress,
                status_message=self._status_message,
                time_remaining=self._time_remaining,
                __method__="post",
            )
        except Exception as exc:
            carb.log_warn(f"Failed to report progress: {str(type(exc))}, {str(exc)}")
