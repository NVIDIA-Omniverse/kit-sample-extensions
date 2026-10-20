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

import carb
import carb.settings
import pydantic
from omni.kit.usd.collect import Collector
from omni.services.core import routers
from omni.services.facilities.monitoring.metrics.facilities import MetricsFacility
from omni.services.facilities.monitoring.progress.facilities import ProgressFacility

from ..collectors.aws import S3Collector

router = routers.ServiceAPIRouter()


class RequestCollectModel(pydantic.BaseModel):
    usd_path: str = pydantic.Field(..., title="USD path to collect.")
    collect_dir: str = pydantic.Field(..., title="The target dir to collect the usd stage to.")
    usd_only: bool = pydantic.Field(False, title="Collects usd files only or not. It will ignore all asset types.")
    flat_collection: bool = pydantic.Field(False, title="Collects stage without keeping the original dir structure.")
    material_only: bool = pydantic.Field(
        False, title="Collects material and textures only or not. It will ignore all other asset types."
    )


class S3RequestCollectModel(RequestCollectModel):
    aws_region: str = pydantic.Field(None, title="Region of the S3 bucket.")
    aws_profile: str = pydantic.Field(None, title="AWS profile to use.")
    s3_bucket: str = pydantic.Field(..., title="S3 bucket to upload to")
    ignore_missing_assets: bool = pydantic.Field(True, title="Ignore missing assets.")


async def _collect_assets(
    collector: Collector, metrics: MetricsFacility, progress_facility: ProgressFacility, usd_path: str, collect_dir: str
):

    collector.MAX_CONCURRENT_TASKS = (
        carb.settings.get_settings_interface().get("exts/omni.services.collect/concurrency") or 8
    )
    process_time = metrics.summaries(
        "collect_usd_time", "Time taken to collect USD file", labelnames=("usd_file", "collect_dir")
    )
    progress_callback = ProgressMonitor(progress_facility)

    file_name = os.path.basename(usd_path)
    file_name, _ = os.path.splitext(file_name)
    collect_dir = "/".join((collect_dir, file_name))

    def _finished():
        print("Finished asset collection")

    with process_time.labels(usd_file=usd_path, collect_dir=collect_dir).time():
        await collector.collect(progress_callback.progress, _finished)

    return {"status": "finished"}


@router.post("/process")
async def asset_collect(
    req: RequestCollectModel,
    metrics: MetricsFacility = router.get_facility("metrics"),
    progress_facility: ProgressFacility = router.get_facility("progress"),
):
    _collector = Collector(req.usd_path, req.collect_dir, req.usd_only, req.flat_collection, req.material_only)
    return await _collect_assets(_collector, metrics, progress_facility, req.usd_path, req.collect_dir)


@router.post("/process/s3")
async def asset_collect_s3(
    req: S3RequestCollectModel,
    metrics: MetricsFacility = router.get_facility("metrics"),
    progress_facility: ProgressFacility = router.get_facility("progress"),
):

    aws_region = req.aws_region
    if not aws_region:
        aws_region = carb.settings.get_settings().get("exts/omni.services.collect/collectors/aws/region") or None

    aws_profile = req.aws_profile
    if not aws_profile:
        aws_profile = carb.settings.get_settings().get("exts/omni.services.collect/collectors/aws/profile") or None

    verify_ssl = carb.settings.get_settings().get("exts/omni.services.collect/collectors/aws/verify_ssl")

    _collector = S3Collector(
        req.usd_path,
        req.collect_dir,
        req.usd_only,
        req.flat_collection,
        req.material_only,
        s3_bucket=req.s3_bucket,
        aws_profile=aws_profile,
        aws_region=aws_region,
        aws_verify_ssl=verify_ssl,
        ignore_missing_assets=req.ignore_missing_assets,
    )
    return await _collect_assets(_collector, metrics, progress_facility, req.usd_path, req.collect_dir)


class ProgressMonitor(object):

    def __init__(self, progress_facility: ProgressFacility) -> None:
        super().__init__()
        self._progress_facility = progress_facility

    def progress(self, step, total_steps):
        carb.log_info(f"step {step} of {total_steps} finished.")
        try:
            self._progress_facility.set_progress(current_step_index=step, total_step_count=total_steps)
        except Exception as exc:
            carb.log_error(f"Failed to update progress of task: {exc}")

    def finished(self):
        carb.log_info("Finished collecting stage")
