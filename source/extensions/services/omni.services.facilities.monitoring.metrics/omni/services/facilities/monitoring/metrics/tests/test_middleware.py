# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import fastapi
import omni.kit.test
from omni.services.client import AsyncClient
from omni.services.core import main
from omni.services.facilities.monitoring.metrics.middleware import MetricsMiddleware, metrics
from starlette.requests import Request


class TestMetricsMiddleware(omni.kit.test.AsyncTestCase):

    async def setUp(self):
        main.register_endpoint("get", "/metrics", metrics, tags=["metrics"])
        main.get_app().add_middleware(MetricsMiddleware)

        async def ping():
            return "pong"

        main.register_endpoint("get", "/ping", ping)
        self._client = AsyncClient("local://")

    async def tearDown(self):
        main.deregister_endpoint("get", "/ping")
        main.deregister_endpoint("get", "/metrics")
        main.get_app().user_middleware.pop(0)

    async def test_metrics_middleware(self):
        for _ in range(10):
            await self._client.ping()

        metrics = await self._client.metrics()
        self.assertTrue(b"TYPE kit_services_requests_total counter" in metrics)
        self.assertTrue(b"TYPE kit_services_requests_active gauge" in metrics)

    async def test_metrics_middleware_with_nested_included_router(self):
        inner_router = fastapi.APIRouter(prefix="/inner")

        @inner_router.get("/ping")
        async def ping():
            return "pong"

        outer_router = fastapi.APIRouter(prefix="/outer")
        outer_router.include_router(inner_router)
        main.register_router(outer_router)

        try:
            request = Request(
                {
                    "type": "http",
                    "app": main.get_app(),
                    "method": "GET",
                    "path": "/outer/inner/ping",
                    "root_path": "",
                    "headers": [],
                    "query_string": b"",
                    "scheme": "http",
                    "server": ("testserver", 80),
                    "client": ("testclient", 50000),
                }
            )
            middleware = MetricsMiddleware(main.get_app())

            self.assertEqual(middleware.get_route(request), "/outer/inner/ping")
        finally:
            main.deregister_router(outer_router)
