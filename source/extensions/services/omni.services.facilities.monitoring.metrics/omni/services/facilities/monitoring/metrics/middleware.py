# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import socket
import time

import fastapi
import prometheus_client as prometheus
from prometheus_client import multiprocess
from starlette import routing
from starlette.middleware import base

_REQUESTS = prometheus.Counter(
    "kit_services_requests_total",
    "Total amount of requests by method and route",
    ["method", "route", "instance"],
)

_ACTIVE_REQUESTS = prometheus.Gauge(
    "kit_services_requests_active",
    "Current active requests by method and route",
    ["method", "route", "instance"],
)

_RESPONSES = prometheus.Counter(
    "kit_services_requests_responses",
    "Total amount of responses by method, route, return code and exception_type",
    ["method", "route", "status_code", "exception_type", "instance"],
)

_REQUEST_PROCESSING_TIME = prometheus.Histogram(
    "kit_services_request_processing_time",
    "Histogram of request processing time per route in seconds",
    ["method", "route", "instance"],
)

_UNMATCHED_ROUTE = prometheus.Counter(
    "kit_services_unmatched_routes",
    "Total amount of requests that have no route.",
    ["method", "route", "instance"],
)

instance_name = f"{socket.getfqdn()}-{os.getpid()}"


class MetricsMiddleware(base.BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        method = request.method
        route = self.get_route(request)

        if not route:
            _UNMATCHED_ROUTE.labels(method=method, route=request.url.path, instance=instance_name).inc()
            return await call_next(request)

        _ACTIVE_REQUESTS.labels(method=method, route=route, instance=instance_name).inc()
        start = time.perf_counter()
        try:
            _REQUESTS.labels(method=method, route=route, instance=instance_name).inc()
            response = await call_next(request)
            _RESPONSES.labels(
                method=method,
                route=route,
                status_code=response.status_code,
                exception_type="no-error",
                instance=instance_name,
            ).inc()
            return response
        except Exception as exc:
            _RESPONSES.labels(
                method=method, route=route, status_code=500, exception_type=str(type(exc)), instance=instance_name
            ).inc()
            raise exc
        finally:
            end = time.perf_counter()
            _ACTIVE_REQUESTS.labels(method=method, route=route, instance=instance_name).dec()
            _REQUEST_PROCESSING_TIME.labels(method=method, route=route, instance=instance_name).observe(end - start)

    def get_route(self, request):
        for registered_route in request.app.routes:
            # FastAPI 0.137+ keeps included routers as route containers. Older FastAPI
            # versions expose the effective routes directly, so retain that behavior as
            # the fallback for backwards compatibility.
            get_route_contexts = getattr(registered_route, "effective_route_contexts", None)
            routes = get_route_contexts() if callable(get_route_contexts) else (registered_route,)
            for route in routes:
                match, _ = route.matches(request.scope)
                if match == routing.Match.FULL:
                    return route.path

        return None


def metrics():
    """Retrieve runtime metrics.

    Returned metrics will be in the Prometheus format.
    """
    if "prometheus_multiproc_dir" in os.environ:
        registry = prometheus.CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = prometheus.REGISTRY

    return fastapi.Response(content=prometheus.generate_latest(registry), media_type=prometheus.CONTENT_TYPE_LATEST)
