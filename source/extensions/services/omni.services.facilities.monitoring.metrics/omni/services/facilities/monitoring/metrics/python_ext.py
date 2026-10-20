# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

import carb
import carb.settings
import omni.ext
import prometheus_client as prometheus
from omni.services.core import main


class MetricsExtension(omni.ext.IExt):

    def __init__(self) -> None:
        super().__init__()
        self._future = None

    def on_startup(self):
        from . import middleware

        show_metrics_endpoint = carb.settings.get_settings_interface().get_as_bool(
            "exts/services.monitoring.metrics/show_metrics_endpoint"
        )

        main.register_endpoint(
            "get",
            "/metrics",
            middleware.metrics,
            tags=["metrics"],
            include_in_schema=show_metrics_endpoint,
            summary="Returns metrics related to the use of the service.",
        )
        main.get_app().add_middleware(middleware.MetricsMiddleware)

        push_enabled = carb.settings.get_settings_interface().get_as_bool(
            "exts/services.monitoring.metrics/push_metrics"
        )
        push_gateway = carb.settings.get_settings_interface().get("exts/services.monitoring.metrics/push_gateway")
        interval = carb.settings.get_settings_interface().get_as_int("exts/services.monitoring.metrics/push_interval")
        job = carb.settings.get_settings_interface().get("exts/services.monitoring.metrics/job_name")

        self._should_stop = asyncio.Event()
        if push_enabled:
            self._future = asyncio.ensure_future(self.push_metrics(push_gateway, job, prometheus.REGISTRY, interval))

    def on_shutdown(self):
        self._should_stop.set()
        if self._future:
            self._future.cancel()
            self._future = None

        main.deregister_endpoint("get", "/metrics")

    async def push_metrics(self, gateway, job, registry, interval):
        while not self._should_stop.is_set():
            try:
                prometheus.push_to_gateway(gateway, job, registry, timeout=10)
            except Exception as exc:
                carb.log_error(f"Failed pushing metrics: {exc}")
            finally:
                await asyncio.sleep(interval)
