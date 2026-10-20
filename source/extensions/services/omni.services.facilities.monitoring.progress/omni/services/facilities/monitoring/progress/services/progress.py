# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

import pydantic
from omni.services.core import routers

from ..store import ProgressStore

router = routers.ServiceAPIRouter()


class NotifyRequestModel(pydantic.BaseModel):
    """Request metadata when receiving a notification about a task's progress."""

    current_step_index: int = pydantic.Field(
        None,
        title="Current step index",
        description="Index of the current step in the overall progress",
        ge=0,
    )
    total_step_count: int = pydantic.Field(
        None,
        title="Total steps count",
        description="Overall number of steps in the progress",
        ge=0,
    )
    progress: float = pydantic.Field(
        None,
        title="Progress completion",
        description="Overall progress completion of the task (between 0.0 and 1.0)",
        ge=0.0,
        le=1.0,
    )
    status_message: str = pydantic.Field(
        None,
        title="Progress status message",
        description="Status message providing additional information about the current progress of the task",
    )
    time_remaining: Optional[float] = pydantic.Field(
        None, title="Time remaining", description="Estimated time remaining until completion of the task"
    )


@router.post("/notify")
async def notify(
    data: NotifyRequestModel,
    progress_store: ProgressStore = router.get_facility("progress_store"),
):
    progress_store.update_progress(
        current_step_index=data.current_step_index,
        total_step_count=data.total_step_count,
        progress=data.progress,
        status_message=data.status_message,
        time_remaining=data.time_remaining,
    )


@router.get("/retrieve")
async def retrieve(
    progress_store: ProgressStore = router.get_facility("progress_store"),
):
    return progress_store.get_progress()
