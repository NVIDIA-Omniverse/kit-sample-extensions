# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, Optional


class ProgressStore(object):
    """Progress store."""

    def __init__(self):
        super().__init__()

        self._current_step_index: int = 0
        self._total_step_count: int = 0
        self._progress: Optional[float] = None
        self._status_message: Optional[str] = None
        self._time_remaining: Optional[float] = None

    def update_progress(
        self,
        current_step_index: int,
        total_step_count: int,
        progress: Optional[float] = None,
        status_message: Optional[str] = None,
        time_remaining: Optional[float] = None,
    ) -> None:
        """
        Update the progress information.

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
            if total_step_count == 0:
                progress = 0.0
            else:
                progress = float(current_step_index) / float(total_step_count)

        self._current_step_index = current_step_index
        self._total_step_count = total_step_count
        self._progress = progress
        self._status_message = status_message
        self._time_remaining = time_remaining

    def get_progress(self) -> Dict:
        """
        Return progress metadata about the progress, formatted in a JSON-friendly serializable manner.

        Args:
            None

        Returns:
            Dict: Progress metadata about the progress, formatted in a JSON-friendly serializable manner.

        """
        return {
            "current_step_index": self._current_step_index,
            "total_step_count": self._total_step_count,
            "progress": self._progress,
            "status_message": self._status_message,
            "time_remaining": self._time_remaining,
        }
