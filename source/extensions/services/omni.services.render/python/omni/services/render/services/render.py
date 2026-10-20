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
import random
import socket
import tempfile
from typing import Tuple, Union

import carb
import carb.settings
import carb.tokens
from omni import usd as _usd
from omni.kit import app as _app
from omni.kit.capture.viewport import CaptureExtension, CaptureOptions, CaptureStatus
from omni.services.core import routers
from omni.services.facilities.log import CarbLogFacility
from omni.services.facilities.monitoring.metrics.facilities import MetricsFacility
from omni.services.facilities.monitoring.progress.facilities import ProgressFacility
from pydantic import BaseModel, Field

from .._utils import create_dynamic_model
from ..tracker import RenderTracker

router = routers.ServiceAPIRouter()

# Generate a arguments class for OpenAPI spec.
RenderSettings = create_dynamic_model(
    "RenderSettings", CaptureOptions().to_dict() | {"texture_streaming_memory_budget": 0.1}
)

_agent_host = socket.getfqdn()


_opening_buckets = (0.1, 0.5, 1, 5, 10, 15, 20, 25, 30, 40, 50, 60, 90, 120, 150, 180, 210, 240, 270, 300, float("inf"))


class RenderAbortedError(Exception):
    """Raised when a render has been aborted"""


class RequestRunModel(BaseModel):
    usd_file: str = Field(..., title="USD file to render", description="Path to the USD stage to render.")
    render_start_delay: int = Field(
        10,
        title="Delay to wait before rendering starts",
        description="Useful to add a delay to make sure shaders etc. are compiled.",
    )
    render_stage_load_timeout: int = Field(
        0,
        title="Time to wait for a stage to load",
        description="Time to wait for an ASSETS_LOADED event, timeout disabled by default.",
    )
    render_settings: RenderSettings = Field(
        ...,
        title="Render settings",
        description="The render settings are built from `omni.kit.capture.CaptureOptions`.",
    )
    load_async: bool = Field(
        False,
        title="Async load stage",
        description="If True will use `open_stage_async` otherwise `open_stage`. open_stage, in headless mode is currently more stable.",
    )
    bad_frame_size_threshold: float = Field(
        0.0,
        title="File size, in bytes, indicating bad frames",
        description="File size threshold under which a frame will be considered bad",
    )
    max_bad_frame_threshold: int = Field(
        3, title="Threshold for bad frames", description="If max bad frames is reached render will be aborted."
    )
    capture_frame_snapshots: bool = Field(
        False,
        title="Capture intermediate frames",
        description="Capture snapshots of the frame currently in progress. Useful to check output early on long running frames.",
    )
    error_on_missing_upload_frames: bool = Field(
        True,
        title="Error on missing upload frames.",
        description="Error when there are missing frames to be uploaded. Useful when all frames are required.",
    )


@router.post(
    "/run",
    summary="Render the given USD stage using the provided options",
    description="Rendering the given USD stage using the configuration options provided in the incoming request.",
)
async def run(
    req: RequestRunModel,
    log: CarbLogFacility = router.get_facility("log"),
    metrics: MetricsFacility = router.get_facility("metrics"),
    progress_facility: ProgressFacility = router.get_facility("progress"),
):
    """Render the given USD Stage."""
    usd_file = req.usd_file
    render_settings = req.render_settings.dict()
    render_settings["fps"] = int(render_settings["fps"])

    staggered_start_time = random.randrange(1, 5)
    log.info(
        f"Staggering start of render by {staggered_start_time} seconds to avoid concurrency issues with omni.client."
    )
    await asyncio.sleep(staggered_start_time)

    open_file_hist = metrics.histogram(
        name="open_stage_time",
        documentation="Time taken to open the given USD stage",
        labelnames=("stage", "agent"),
        buckets=_opening_buckets,
        unit="seconds",
    )
    reopen_stage = True
    is_new_stage = True

    _settings = carb.settings.get_settings_interface()
    stage_load_timeout = _settings.get_as_int("exts/omni.services.render/stage_load_timeout") or 0
    stage_load_timeout = (
        stage_load_timeout if req.render_stage_load_timeout <= stage_load_timeout else req.render_stage_load_timeout
    )

    # apply texture streaming budget settings before opening the usd stage
    # *this can be removed after omni.kit.capture.viewport handles it
    if "texture_streaming_memory_budget" in render_settings:
        gpu_memory_budget_percentage = render_settings.pop("texture_streaming_memory_budget", 0.1)
        carb.log_info(f"texture streaming memory budget to be applied: {gpu_memory_budget_percentage}")
        _settings.set("/rtx-transient/resourcemanager/texturestreaming/memoryBudget", gpu_memory_budget_percentage)

    with open_file_hist.labels(stage=usd_file, agent=_agent_host).time():
        if not _usd.get_context().is_new_stage():
            current_stage_url = _usd.get_context().get_stage_url()
            if current_stage_url == usd_file:
                is_new_stage = False

        if is_new_stage or reopen_stage:
            await _open_stage(usd_file, log, stage_load_timeout, load_async=req.load_async)

    if req.render_start_delay > 0 and is_new_stage:
        log.info(f"Delaying start of render by configured delay of: {req.render_start_delay} seconds.")
        await asyncio.sleep(req.render_start_delay)

    temp_root_dir = _settings.get("exts/omni.services.render/temp_root_directory") or "${temp}"
    temp_root_dir = carb.tokens.get_tokens_interface().resolve(temp_root_dir)
    capture_setting_settle_delay = _settings.get_as_int("exts/omni.services.render/capture_setting_settle_delay") or 1
    finalize_frame_sync_timeout = _settings.get_as_int("exts/omni.services.render/finalize_frame_sync_timeout") or 60
    if finalize_frame_sync_timeout <= 0:
        finalize_frame_sync_timeout = 60
    flush_frame_timeout = _settings.get_as_int("exts/omni.services.render/flush_frame_timeout") or 10
    if flush_frame_timeout <= 0:
        flush_frame_timeout = 10

    try:
        with tempfile.TemporaryDirectory(dir=temp_root_dir) as tmp_path:
            capture_instance = CaptureExtension.get_instance()
            capture_done = asyncio.Event()
            filesync_done = asyncio.Event()
            if capture_setting_settle_delay > 0:
                await asyncio.sleep(capture_setting_settle_delay)
            tracker = _apply_settings(
                capture_instance=capture_instance,
                settings=render_settings,
                temp_output_folder=tmp_path,
                metrics=metrics,
                progress_facility=progress_facility,
                usd_file=usd_file,
                bad_frame_size_threshold=req.bad_frame_size_threshold,
                max_bad_frame_threshold=req.max_bad_frame_threshold,
                error_on_missing_upload_frames=req.error_on_missing_upload_frames,
                capture_done=capture_done,
                filesync_done=filesync_done,
            )

            if capture_setting_settle_delay > 0:
                await asyncio.sleep(capture_setting_settle_delay)

            capture_instance.start()
            while capture_instance.progress.capture_status == CaptureStatus.CAPTURING and not tracker.aborted:
                await _app.get_app_interface().next_update_async()

            if tracker.aborted:
                raise RenderAbortedError("Rendering has been aborted as the bad frame threshold has been exceeded")

            # Give the renderer some time to write out all the frames
            for _ in range(flush_frame_timeout):
                await _app.get_app_interface().next_update_async()
                await asyncio.sleep(1)

            # At this time the capture is complete, set the event to notify filemanager.
            capture_done.set()
            # Upload any final missing frames.
            await tracker.finalize_frame_sync(timeout=finalize_frame_sync_timeout)
            await tracker.shutdown(timeout=finalize_frame_sync_timeout)

    except Exception as exc:
        log.error(f"Failed to process render: {str(type(exc))} {str(exc)}")
        raise


async def _open_stage(usd_file: str, log: CarbLogFacility, stage_load_timeout: int, load_async: bool = True) -> bool:
    """
    Open the given USD stage.

    Args:
        usd_file (str): Path to the USD stage to open.
        log (CarbLogFacility): Facility to log information about the operation.
        stage_load_timeout (int): Maximum time to wait for the stage to load (in seconds).
        load_async (bool): Flag indicating whether to load the given USD stage asynchronously.

    Returns:
        bool: A flag indicating whether the operation completed successfully.

    """
    log.info(f"Opening: {usd_file}")

    if load_async:
        success, error = await _usd.get_context().open_stage_async(usd_file)
    else:
        success, error = _open_stage_sync(usd_file)

    if not success:
        log.error(f"Unable to open {usd_file}: {str(error)}")
        raise Exception(f"Could not open {usd_file}")

    log.info(f"Stage opened: {usd_file}. Waiting for ASSETS_LOADED event.")

    kwargs = {"timeout": None}
    if stage_load_timeout > 0:
        kwargs["timeout"] = stage_load_timeout

    usd_context = _usd.get_context()
    if usd_context.get_stage_state() != _usd.StageState.OPENED:
        while True:
            try:
                event, _ = await asyncio.wait_for(usd_context.next_stage_event_async(), **kwargs)
                if event == int(_usd.StageEventType.ASSETS_LOADED):
                    log.info(f"Assets for {usd_file} loaded")
                    return True
            except asyncio.TimeoutError:
                _, files_loaded, total_files = usd_context.get_stage_loading_status()
                if files_loaded == total_files:
                    log.warn(
                        "Timed out waiting for ASSETS_LOADED event but all files seem to have loaded. Attempting render."
                    )
                    return False

                raise Exception(f"Timed out waiting for ASSETS_LOADED event for {usd_file}. Aborting")


def _open_stage_sync(usd_file: str) -> Tuple[bool, Union[str, None]]:
    """
    Open the given USD stage synchronously.

    Args:
        usd_file (str): Path to the USD stage to open synchronously.

    Returns:
        Tuple[bool, Union[str, None]]: A Tuple containing a flag indicating whether the operation completed successfully,
            along with an optional error message in case of failure.

    """
    success = True
    error = None
    try:
        success = _usd.get_context().open_stage(usd_file)
        if not success:
            error = f"Open USD error: {usd_file}"
    except Exception as exc:
        raise Exception(f"Could not open {usd_file}: {str(exc)}")

    return success, error


def _apply_settings(
    capture_instance: CaptureExtension,
    settings: dict,
    temp_output_folder: str,
    metrics: MetricsFacility,
    progress_facility: ProgressFacility,
    usd_file: str,
    bad_frame_size_threshold: int,
    max_bad_frame_threshold: int,
    error_on_missing_upload_frames: bool,
    capture_done: asyncio.Event,
    filesync_done: asyncio.Event,
):
    options = CaptureOptions.from_dict(settings)
    options.output_folder = temp_output_folder
    capture_instance.options = options

    nth_frame = options.capture_every_Nth_frames
    if nth_frame == 1:
        subdir = f"{options.file_name}_frames"
        temp_output_folder = os.path.join(temp_output_folder, subdir)
    elif isinstance(nth_frame, int) and nth_frame > 1:
        subdir = f"{options.file_name}_{str(options.capture_every_Nth_frames)}th_frames"
        temp_output_folder = os.path.join(temp_output_folder, subdir)

    tracker = RenderTracker(
        tmp_path=temp_output_folder,
        output_path=settings["output_folder"],
        metrics=metrics,
        progress_facility=progress_facility,
        usd_file=usd_file,
        capture_nth_frame=nth_frame,
        render_camera=options.camera,
        capture_progress=capture_instance.progress,
        max_bad_frame_threshold=max_bad_frame_threshold,
        bad_frame_size_threshold=bad_frame_size_threshold,
        interval=5,
        error_on_missing_upload_frames=error_on_missing_upload_frames,
        # TODO, remove after #OM-43301 is fixed.
        capture_instance=capture_instance,
        capture_done=capture_done,
        filesync_done=filesync_done,
    )

    capture_instance.show_default_progress_window = False
    capture_instance.progress_update_fn = tracker.on_capture_progress
    return tracker
