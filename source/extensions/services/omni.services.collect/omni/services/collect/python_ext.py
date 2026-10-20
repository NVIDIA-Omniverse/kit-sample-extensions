# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ext
from omni.services.core import main
from omni.services.facilities.monitoring.metrics import facilities as _metrics_facilities
from omni.services.facilities.monitoring.progress import facilities as _progress_facilities

from .services import collect


class ServiceConvertAssetExtension(omni.ext.IExt):

    def on_startup(self):
        metrics_facility = _metrics_facilities.MetricsFacility("stage_collect")
        progress_facility = _progress_facilities.ProgressFacility()
        collect.router.register_facility("metrics", metrics_facility)
        collect.router.register_facility("progress", progress_facility)

        main.register_router(collect.router, prefix="/collect", tags=["collect"])

    def on_shutdown(self):
        main.deregister_router(collect.router, prefix="/collect")
