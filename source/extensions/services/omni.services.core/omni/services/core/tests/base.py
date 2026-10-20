# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Base class for the Omniverse microservices framework test cases, enhancing `AsyncTestCase` tests suites with
asynchronous utilities.
"""

import asyncio
import json
import urllib
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional, Tuple

import carb
from omni.kit.test import AsyncTestCase
from omni.services.core import main


class BaseServiceTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        # Record the intial list of routes before executing a test, in order to later compare it with the list of tests
        # at the end of a test.
        #
        # This is to ensure that no temporary route survives the test, in order to avoid inadvertently "leaking" a route
        # from one test to another and result in erroneous results when running asynchronous test procedures.
        #
        # Instances where this can happen by design is when testing the addition of routes or mount points.
        self._initial_route_paths = [
            route.path for route in main.get_app().routes if getattr(route, "path", None) is not None
        ]

    def tearDown(self):
        super().tearDown()

        if not hasattr(self, "_initial_route_paths"):
            return

        # Compare the list of routes with the one gathered before running a test:
        final_route_paths = [route.path for route in main.get_app().routes if getattr(route, "path", None) is not None]
        added_routes = list(set(final_route_paths) - set(self._initial_route_paths))
        if added_routes:
            # Warn about routes "leaked" while testing, which may influence the results of other tests:
            carb.log_warn(f"The following routes were added during a test, and remain accessible: {added_routes}.")

    def _remove_route_patterns(self, route_patterns: List[str]) -> None:
        """
        Remove the given route patterns from the list of application routes.

        Args:
            route_patterns (List[str]): List of route patterns to remove (supporting `fnmatch`-type wildcard searches).

        Returns:
            None

        """

        def _iter_route_paths(route):
            route_path = getattr(route, "path", None)
            if route_path is not None:
                yield route_path

            effective_candidates = getattr(route, "effective_candidates", None)
            if effective_candidates is not None:
                for candidate in effective_candidates():
                    yield from _iter_route_paths(candidate)

        routes_to_remove = []
        for route in main.get_app().routes:
            if any(
                fnmatch(route_path, route_pattern)
                for route_path in _iter_route_paths(route)
                for route_pattern in route_patterns
            ):
                routes_to_remove.append(route)

        for route in routes_to_remove:
            main.get_app().routes.remove(route)

    async def _post_request_async(
        self, url: str, data: Any, headers: Optional[List[Tuple[str, str]]] = None, app: Optional[Any] = None
    ) -> Tuple[str, int]:
        result = []
        scope = {
            "type": "http",  # Change this so it can be amqp etc. as well, will require Router change.
            "method": "POST",
            "path": url,
            "query_string": b"",
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in (headers if headers is not None else [("Content-Type", "application/json")])
            ],
            "body": json.dumps(data),
        }

        async def _receive():
            return {"type": "http.request", "body": bytes(scope["body"], "ascii")}

        async def _send(result_data):
            result.append(result_data)

        await (app or main.get_app())(scope, _receive, _send)

        return_value = None
        return_code = 503
        for entry in result:
            if entry["type"] == "http.response.body":
                return_value = json.loads(entry["body"].decode("utf-8"))
            elif entry["type"] == "http.response.start":
                return_code = entry["status"]

        return return_value, return_code

    async def _get_request_async(
        self,
        url: str,
        headers: List[Tuple[str, str]] = [("Content-Type", "application/json")],
        query_params: Dict[str, Any] = None,
    ) -> Tuple[str, int]:
        result = []
        query_string = urllib.parse.urlencode(query_params, True) if query_params else ""
        scope = {
            "type": "http",  # Change this so it can be amqp etc. as well, will require Router change.
            "method": "GET",
            "path": url,
            "query_string": bytes(query_string, "ascii"),
            "headers": headers,
        }

        # A valid ASGI receive: one http.request message, then wait like a server until the response is done and the
        # app cancels the wait. Starlette 1.x FileResponse (StaticFiles mounts) listens for "http.disconnect" in a loop
        # beside the file stream, so `{}` raises KeyError: 'type', and a receive that always returns at once would spin.
        request_sent = False

        async def _receive():
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.Event().wait()
            return {"type": "http.disconnect"}

        async def _send(data):
            result.append(data)

        await main.get_app()(scope, _receive, _send)

        return_value = None
        is_json_response = False
        for entry in result:
            if (
                entry["type"] == "http.response.start"
                and "headers" in entry
                and list(filter(lambda x: x[0] == b"content-type" and x[1] == b"application/json", entry["headers"]))
            ):
                is_json_response = True

            if entry["type"] == "http.response.body":
                return_value = entry["body"].decode("utf-8")
                if is_json_response:
                    # In case the response contains the "content-type: application/json" Header, provide the response
                    # under its parsed representation for convenience (assuming it is well-formed JSON):
                    return_value = json.loads(return_value)
            elif entry["type"] == "http.response.start":
                return_code = entry["status"]

        return return_value, return_code
