# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import typing
from collections import deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import carb
import omni.client
import omni.kit.asset_converter
import pydantic
from fastapi import Depends, Header, Request, status
from fastapi.responses import JSONResponse
from omni.kit.converter.common.common import (
    extract_zip_archive,
    is_asset_supported,
    validate_file_path,
)
from omni.services.core import exceptions, routers
from pxr import Usd

from .. import _utils
from .progress_facility import ProgressFacility

__all__ = [
    "CustomBaseModel",
    "RequestRunModel",
    "ConversionState",
    "JobState",
    "ConversionStateManager",
    "HealthResponseModel",
    "ReadinessResponseModel",
    "StatusResponseModel",
    "JobStatusResponseModel",
    "HistoryResponseModel",
    "ConverterResponseModel",
    "router",
]

# asset converter supported formats
SUPPORTED_FORMATS = [
    "(.*\\.fbx$)",
    "(.*\\.obj$)",
    "(.*\\.gltf$)",
    "(.*\\.*glb$)",
    "(.*\\.lxo$)",
    "(.*\\.md5$)",
    "(.*\\.stl$)",
    "(.*\\.bvh$)",
]

router = routers.ServiceAPIRouter()


class ConversionState(str, Enum):
    """Enum representing the current state of the conversion service."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"


class JobState(str, Enum):
    """Enum representing the state of an individual conversion job."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ConversionJob:
    """Represents a single conversion job."""

    def __init__(
        self,
        job_id: str,
        file_path: str,
        output_path: str = "",
        progress_facility: typing.Optional[ProgressFacility] = None,
    ):
        self.job_id = job_id
        self.file_path = file_path
        self.output_path = output_path
        self.state = JobState.RUNNING
        self.error_message = ""
        self.progress_facility = progress_facility
        self.start_time = datetime.now()
        self.end_time: typing.Optional[datetime] = None

    def get_progress(self) -> float:
        """Get the current progress of the conversion job (0.0 to 1.0)."""
        if self.progress_facility is not None:
            return self.progress_facility._progress
        return 0.0


class ConversionStateManager:
    """
    Thread-safe singleton class to manage the conversion state.
    Allows up to MAX_JOB_COUNT conversions to run simultaneously
    and provides state information for health/readiness checks.
    """

    MAX_JOB_COUNT = int(os.environ.get("ASSET_SERVICE_MAX_JOB_COUNT", "5"))
    MAX_SESSION_HISTORY_COUNT = int(os.environ.get("ASSET_SERVICE_MAX_SESSION_HISTORY_COUNT", "5"))

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConversionStateManager, cls).__new__(cls)
            cls._instance._semaphore = asyncio.Semaphore(cls.MAX_JOB_COUNT)
            cls._instance._active_jobs = {}  # job_id -> ConversionJob
            cls._instance._job_history = deque(
                maxlen=cls.MAX_SESSION_HISTORY_COUNT
            )  # Bounded history of completed jobs
            cls._instance._job_counter = 0
        return cls._instance

    async def acquire_conversion_slot(
        self, file_path: str, output_path: str = "", progress_facility: typing.Optional[ProgressFacility] = None
    ) -> typing.Optional[str]:
        """
        Try to acquire a conversion slot.
        Returns job_id if acquired, None if all slots are full.
        """
        # Check if we have available slots before trying to acquire
        async with self._lock:
            if len(self._active_jobs) >= self.MAX_JOB_COUNT:
                carb.log_warn(
                    f"All {self.MAX_JOB_COUNT} conversion slots are full. " f"Rejecting new request for {file_path}"
                )
                return None

        # Try to acquire semaphore with a short timeout
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.1)
        except asyncio.TimeoutError:
            carb.log_warn(f"Timeout acquiring conversion slot for {file_path}. All slots are busy.")
            return None

        # Create a new job
        async with self._lock:
            self._job_counter += 1
            job_id = f"job_{self._job_counter}_{datetime.now().timestamp()}"
            job = ConversionJob(job_id, file_path, output_path, progress_facility)
            self._active_jobs[job_id] = job
            carb.log_info(
                f"Conversion slot acquired for {file_path} (job_id: {job_id}). "
                f"Active jobs: {len(self._active_jobs)}/{self.MAX_JOB_COUNT}"
            )
            return job_id

    async def release_conversion_slot(self, job_id: str, final_state: JobState, error_message: str = ""):
        """Release a conversion slot and update job state."""
        job_found = False
        async with self._lock:
            if job_id in self._active_jobs:
                job = self._active_jobs[job_id]
                job.state = final_state
                job.error_message = error_message
                job.end_time = datetime.now()

                # Add to history before removing from active jobs
                self._job_history.append(job)

                # Remove from active jobs
                del self._active_jobs[job_id]
                job_found = True

                carb.log_info(
                    f"Conversion slot released for job {job_id}. "
                    f"Final state: {final_state}. "
                    f"Active jobs: {len(self._active_jobs)}/{self.MAX_JOB_COUNT}"
                )
            else:
                carb.log_warn(f"Attempted to release unknown job_id: {job_id}")

        if job_found:
            self._semaphore.release()

    async def get_state(self) -> dict:
        """Get the current state information."""
        async with self._lock:
            active_count = len(self._active_jobs)

            # Determine overall service state: IDLE or RUNNING
            if active_count == 0:
                overall_state = ConversionState.IDLE.value
                current_jobs = []
            else:
                overall_state = ConversionState.RUNNING.value
                current_jobs = [
                    {
                        "job_id": job.job_id,
                        "file_path": job.file_path,
                        "progress": round(job.get_progress() * 100.0 if job.get_progress() < 1.0 else 1.0, 2),
                        "start_time": job.start_time.isoformat() if job.start_time else None,
                    }
                    for job in self._active_jobs.values()
                ]

            return {
                "state": overall_state,
                "active_jobs": active_count,
                "max_job_count": self.MAX_JOB_COUNT,
                "available_slots": self.MAX_JOB_COUNT - active_count,
                "current_jobs": current_jobs,
            }

    async def is_ready(self) -> bool:
        """Check if the service is ready to accept new conversion requests."""
        async with self._lock:
            return len(self._active_jobs) < self.MAX_JOB_COUNT

    async def get_job_status(self, job_id: str) -> typing.Optional[dict]:
        """
        Get the status of a specific job.
        Returns None if job_id is not found.
        """
        async with self._lock:
            if job_id in self._active_jobs:
                job = self._active_jobs[job_id]
                progress = round(job.get_progress() * 100.0 if job.get_progress() < 1.0 else 1.0, 2)
                return {
                    "job_id": job.job_id,
                    "file_path": job.file_path,
                    "state": job.state.value,
                    "progress": progress,
                    "error_message": job.error_message,
                    "start_time": job.start_time.isoformat() if job.start_time else None,
                }
            return None

    async def get_history(self) -> typing.List[dict]:
        """
        Get the history of completed/failed jobs.
        Returns a list of job dictionaries, most recent first.
        """
        async with self._lock:
            # Return history in reverse order (most recent first)
            return [
                {
                    "job_id": job.job_id,
                    "file_path": job.file_path,
                    "output_path": job.output_path,
                    "state": job.state.value,
                    "progress": round(job.get_progress() * 100.0 if job.get_progress() < 1.0 else 1.0, 2),
                    "error_message": job.error_message,
                    "start_time": job.start_time.isoformat() if job.start_time else None,
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                }
                for job in reversed(self._job_history)
            ]


# Global state manager instance
state_manager = ConversionStateManager()

ConverterContext = _utils.create_dynamic_model("ConverterContext", omni.kit.asset_converter.AssetConverterContext)


class CustomBaseModel(pydantic.BaseModel):
    @classmethod
    def validate(cls, value):
        """overwrite classmethod validate to log error and notify user when the payload is incorrect."""
        try:
            return super().validate(value)
        except pydantic.ValidationError as e:
            carb.log_error(f"Validation error in model {cls.__name__}: {e}")
            sample_input = '{ "import_path": "", "output_path": "", "converter_settings": {} }'
            raise exceptions.KitServicesBaseException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Validation error in model, payload: {sample_input}",
            )


class RequestRunModel(CustomBaseModel):
    """Request Model for Asset Converter task

    Args:
        import_path (str): Full path to source asset (CAD File).
        output_path (str): Full path to the output file.
        converter_settings (dict): Converter context object, settings.
        archive_path (str): Archived input asset.
    """

    import_path: str = pydantic.Field(
        ..., title="The source asset.", description="Full path to source asset (CAD File)."
    )
    output_path: str = pydantic.Field(
        ..., title="The target asset.", description="Asset format is decided by the output path's extension."
    )
    converter_settings: ConverterContext
    archive_path: Optional[str] = pydantic.Field(
        "",
        title="Archive path",
        description="Optional path to `.zip`, `.tar`, or `.tar.gz` archive that contains the input file(s)",
    )


class HealthResponseModel(pydantic.BaseModel):
    """Response model for health check endpoint."""

    status: str = pydantic.Field(..., title="Health Status", description="Health status of the service.")


class ReadinessResponseModel(pydantic.BaseModel):
    """Response model for readiness check endpoint."""

    ready: bool = pydantic.Field(..., title="Ready", description="Whether the service is ready to accept requests.")


class StatusResponseModel(pydantic.BaseModel):
    """Response model for status endpoint."""

    state: str = pydantic.Field(
        ..., title="Conversion State", description="Current state of the conversion service (IDLE or RUNNING)."
    )
    active_jobs: int = pydantic.Field(..., title="Active Jobs", description="Number of jobs currently running.")
    max_job_count: int = pydantic.Field(
        ..., title="Max Jobs Count", description="Maximum number of concurrent jobs allowed."
    )
    available_slots: int = pydantic.Field(
        ..., title="Available Slots", description="Number of available conversion slots."
    )
    current_jobs: typing.List[dict] = pydantic.Field(
        [], title="Current Jobs", description="List of jobs currently running with their progress and states."
    )


class JobStatusResponseModel(pydantic.BaseModel):
    """Response model for individual job status endpoint."""

    job_id: str = pydantic.Field(..., title="Job ID", description="Unique identifier for the conversion job.")
    file_path: str = pydantic.Field(..., title="File Path", description="Path to the file being converted.")
    state: str = pydantic.Field(..., title="Job State", description="Current state of the conversion job.")
    progress: float = pydantic.Field(
        ..., title="Progress", description="Progress percentage of the conversion (0.0 to 1.0)."
    )
    error_message: str = pydantic.Field(
        "", title="Error Message", description="Error message if the job encountered an error."
    )
    start_time: typing.Optional[str] = pydantic.Field(
        None, title="Start Time", description="ISO format timestamp when the job started."
    )


class HistoryResponseModel(pydantic.BaseModel):
    """Response model for job history endpoint."""

    max_session_history_count: int = pydantic.Field(
        ..., title="Max Session History Count", description="Maximum number of jobs kept in session history."
    )
    jobs: typing.List[dict] = pydantic.Field(
        ..., title="Job History", description="List of completed/failed jobs, most recent first."
    )


class ConverterResponseModel(pydantic.BaseModel):
    status: int = pydantic.Field(..., title="Converter status", description="Converter status response message.")
    comment: str = pydantic.Field(..., title="Comment", description="Additional information on the converter status.")


@router.get(
    path="/health",
    summary="Health Check Endpoint",
    description="Check if the service is alive and responding.",
    response_model=HealthResponseModel,
)
async def health_check() -> HealthResponseModel:
    """
    Health check endpoint that always returns OK if the service is running.
    This is used by Kubernetes liveness probes.
    """
    return HealthResponseModel(status="OK")


@router.get(
    path="/ready",
    summary="Readiness Check Endpoint",
    description="Check if the service is ready to accept new conversion requests.",
    response_model=ReadinessResponseModel,
)
async def readiness_check() -> ReadinessResponseModel:
    """
    Readiness check endpoint that returns OK only when the service can accept new requests.
    Returns NOT_READY if a conversion is currently running.
    This is used by Kubernetes readiness probes to control traffic routing.
    """
    is_ready = await state_manager.is_ready()
    return ReadinessResponseModel(ready=is_ready)


@router.get(
    path="/status",
    summary="Conversion Status Endpoint",
    description="Get the current state of the conversion service.",
    response_model=StatusResponseModel,
)
async def status_check() -> StatusResponseModel:
    """
    Status endpoint that returns the current conversion state.
    States: IDLE (no jobs running), RUNNING (jobs in progress)
    Shows active jobs and available slots. For individual job errors, query /status/{job_id}.
    """
    state_info = await state_manager.get_state()

    return StatusResponseModel(
        state=state_info["state"],
        active_jobs=state_info["active_jobs"],
        max_job_count=state_info["max_job_count"],
        available_slots=state_info["available_slots"],
        current_jobs=state_info["current_jobs"],
    )


@router.get(
    path="/status/{job_id}",
    summary="Job Status Endpoint",
    description="Get the status of a specific conversion job by job_id.",
    response_model=JobStatusResponseModel,
)
async def job_status_check(job_id: str) -> JobStatusResponseModel:
    """
    Job status endpoint that returns the status of a specific conversion job.
    Returns job details including state, progress, and error message if any.
    Raises 404 if job_id is not found.
    """
    job_info = await state_manager.get_job_status(job_id)

    if job_info is None:
        raise exceptions.KitServicesBaseException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found. It may have already completed or never existed.",
        )

    return JobStatusResponseModel(
        job_id=job_info["job_id"],
        file_path=job_info["file_path"],
        state=job_info["state"],
        progress=job_info["progress"],
        error_message=job_info["error_message"],
        start_time=job_info["start_time"],
    )


@router.get(
    path="/history",
    summary="Job History Endpoint",
    description="Get the history of completed and failed conversion jobs.",
    response_model=HistoryResponseModel,
)
async def history_check() -> HistoryResponseModel:
    """
    History endpoint that returns completed and failed conversion jobs.
    Shows up to MAX_SESSION_HISTORY_COUNT jobs, most recent first.
    Includes job_id, file_path, output_path, state, progress, error_message, and timestamps.
    """
    history = await state_manager.get_history()

    return HistoryResponseModel(
        max_session_history_count=state_manager.MAX_SESSION_HISTORY_COUNT,
        jobs=history,
    )


@router.post(
    path="/process",
    summary="Asset Converter Service.",
    description="Convert between supported CAD formats.",
    response_model=ConverterResponseModel,
)
async def asset_convert(
    req: RequestRunModel,
    progress_facility: ProgressFacility = router.get_facility("progress"),
) -> ConverterResponseModel:

    # Try to acquire a conversion slot
    job_id = await state_manager.acquire_conversion_slot(req.import_path, req.output_path, progress_facility)
    if job_id is None:
        raise exceptions.KitServicesBaseException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service is busy: All {state_manager.MAX_JOB_COUNT} conversion slots are full. Please try again later.",
        )

    try:
        carb.log_info("Validating inputs.")
        # Validate input path exists.
        if validate_file_path(req.import_path) is None:
            error_msg = f"Input file path does not exist! Recieved: {req.import_path}"
            carb.log_error(error_msg)
            raise exceptions.KitServicesBaseException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error_msg
            )

        # Validate input file format is supported by converter.
        if not is_asset_supported(req.import_path, SUPPORTED_FORMATS):
            error_msg = f"Input file format is not supported! Recieved: {req.import_path}"
            carb.log_error(error_msg)
            raise exceptions.KitServicesBaseException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=error_msg
            )

        # Unsupported output format.
        if not Usd.Stage.IsSupportedFile(req.output_path):
            error_msg = f"Output file is not supported! Supported formats: `.usd`, `.usda`, '.usdc'"
            carb.log_error(error_msg)
            raise exceptions.KitServicesBaseException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=error_msg
            )

        # Extract archive to get unmanged import_path in order to work with NVCF asset management
        if req.archive_path:
            if _utils.unpack_archive(req.archive_path):
                carb.log_info(f"Archive {req.archive_path} extracted!")
            else:
                error_msg = (
                    f"Failed to extract from archive {req.archive_path}! Supported formats: `.zip`, `.tar`, `.tar.gz`"
                )
                carb.log_error(error_msg)
                raise exceptions.KitServicesBaseException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=error_msg
                )

        carb.log_info(f"Starting asset conversion, path: {req.import_path}")

        # Set initial progress
        progress_facility.set_progress(0, 1, progress=0.0, status_message=f"Starting conversion of {req.import_path}")

        # Create progress callback that directly updates the progress facility
        def progress_callback(step, total_steps):
            """Progress callback for asset converter that updates the progress facility."""
            if total_steps > 0:
                progress = float(step) / float(total_steps)
                progress = round(progress / 100.0, 2)
                progress_facility.set_progress(
                    step, total_steps, progress=progress, status_message=f"Processing step {step} of {total_steps}"
                )
            carb.log_info(f"step {step} of {total_steps} finished.")

        task = omni.kit.asset_converter.get_instance().create_converter_task(
            req.import_path, req.output_path, progress_callback, req.converter_settings
        )

        success = await task.wait_until_finished()
        if not success:
            detailed_status_code = task.get_status()
            detailed_status_error_string = task.get_detailed_error()
            error_msg = (
                f"Failed to convert {req.import_path}. Error: {detailed_status_code}, {detailed_status_error_string}"
            )
            raise exceptions.KitServicesBaseException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        # Conversion successful
        progress_facility.set_progress(1, 1, progress=1.0, status_message=f"Successfully converted {req.import_path}")
        await state_manager.release_conversion_slot(job_id, JobState.COMPLETED)
        carb.log_info(f"Asset {req.import_path} is converterted!")
        return ConverterResponseModel(
            status=status.HTTP_200_OK,
            comment=f"File {req.import_path} was successfully converted to {req.output_path}.",
        )

    except Exception as e:
        # Make sure we release the slot on any exception
        error_detail = str(e) if not isinstance(e, exceptions.KitServicesBaseException) else e.detail
        carb.log_error(f"Failed to convert {req.import_path}. Error: {str(type(e))} {error_detail}")
        await state_manager.release_conversion_slot(job_id, JobState.ERROR, error_detail)
        raise
