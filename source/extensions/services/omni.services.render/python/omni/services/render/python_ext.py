# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Rendering service Extension."""

import omni.ext
from omni.services.core.main import deregister_router, register_router
from omni.services.facilities.log import CarbLogFacility
from omni.services.facilities.monitoring.metrics.facilities import MetricsFacility
from omni.services.facilities.monitoring.progress.facilities import ProgressFacility

from .services.render import router


class ServiceRenderExtension(omni.ext.IExt):
    """Rendering service Extension."""

    def on_startup(self, ext_id: str) -> None:
        logger_facility = CarbLogFacility()
        metrics_facility = MetricsFacility(service="render")
        progress_facility = ProgressFacility()

        router.register_facility(name="log", facility_inst=logger_facility)
        router.register_facility(name="metrics", facility_inst=metrics_facility)
        router.register_facility(name="progress", facility_inst=progress_facility)

        register_router(router=router, prefix="/render", tags=["render"])

    def on_shutdown(self) -> None:
        deregister_router(router=router, prefix="/render")
