# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import json
from contextlib import AsyncExitStack
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import ParseResult, urlencode

from fastapi import FastAPI
from omni.services.transport.client.base.consumer import BaseConsumer, BaseStandin
from omni.services.transport.client.base.exceptions import ServiceNotFoundError
from starlette.types import Message


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class Transport(BaseConsumer):
    """Transport for the `local://` scheme."""

    def __init__(
        self,
        parsed_uri: ParseResult,
        app: Optional[FastAPI],
        version: Optional[Any],
        persist_connections: bool = False,
        raise_for_status: bool = True,
    ):
        """
        Constructor.

        Args:
            parsed_uri (ParseResult): Parsed URI of the server.
            app (Optional[FastAPI]): Reference to the application running on the server.
            version (Optional[Any]): Version of the application running on the server.
            persist_connections (bool): Flag indicating whether to persist connections to the server.
            raise_for_status (bool): Flag indicating whether to raise exceptions for errors.

        Returns:
            None

        """
        if app is None:
            try:
                from omni.services.core import main

                app = main.get_app()
            except ImportError:
                raise Exception(
                    "The local transport needs a FastAPI app to function. Either pass it through in the constructor or make sure the omni.services.core extension is enabled"
                )

        self._base_uri = parsed_uri.path
        super().__init__(
            parsed_uri, app, version, persist_connections=persist_connections, raise_for_status=raise_for_status
        )

    def __getattr__(self, name: str):
        return BaseStandin(name, self)

    def _create_full_uri(self, uri: str) -> str:
        """
        Create the full URI of the call based on the nomenclature used by the Client.

        Args:
            uri (str): URI of the server endpoint to call.

        Returns:
            str: The full URI of the call to the server.

        """
        full_uri = "/".join((self._base_uri, uri))
        return full_uri.replace("_", "-")

    @staticmethod
    def _iter_effective_candidates(candidates: Iterable[Any]) -> Iterator[Tuple[Any, Any]]:
        """Yield each routable candidate together with its owning route handler."""
        for handler in candidates:
            # FastAPI 0.137+ groups included routes behind effective_candidates();
            # earlier versions expose each route directly.
            effective_candidates = getattr(handler, "effective_candidates", None)
            if callable(effective_candidates):
                # Candidates can themselves be included-router containers.
                for candidate, _ in Transport._iter_effective_candidates(effective_candidates()):
                    yield candidate, handler
            else:
                yield handler, handler

    async def __call__(
        self,
        uri: str,
        *args,
        __method__: Optional[str] = None,
        __headers__: Optional[Dict[str, str]] = None,
        __raw__: bool = False,
        **kwargs,
    ):
        """
        Perform a call to the server endpoint identified by the Client's attribute nomenclature.

        Args:
            uri (str): URI of the server to connect to.
            __method__ (Optional[str]): Method to use to perform the call.
            __headers__ (Optional[Dict[str, str]]): Headers to send along with the request.
            __raw__ (bool): Flag indicating whether the request should be sent in raw mode.

        Returns:
            Any: The response emitted by the server after processing the given request.

        """
        candidates = self._iter_effective_candidates(self._app.routes)
        uri = self._create_full_uri(uri)

        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        async def _receive():
            return {"type": "http.request", "body": bytes(json.dumps(kwargs), "ascii")}

        headers = __headers__ or {}
        encoded_headers = []
        has_content_type = False
        for header, value in headers.items():
            normalized_header = header.lower()
            has_content_type = has_content_type or normalized_header == "content-type"
            encoded_headers.append((normalized_header.encode("ascii"), value.encode("ascii")))
        if not has_content_type:
            encoded_headers.append((b"content-type", b"application/json"))

        scope = {"type": "http", "path": uri, "query_string": b"", "headers": encoded_headers}

        for route, handler in candidates:
            if not hasattr(route, "methods"):
                # No methods available so not a path we'd want to call
                continue

            scope["method"] = __method__.upper() if __method__ else self._get_route_method(route.methods)
            match, child_scope = route.matches(scope)
            if match.value != Match.FULL.value:
                continue

            if scope["method"] == "GET":
                scope["query_string"] = urlencode(kwargs, doseq=True).encode("utf-8")

            scope.update(child_scope)

            async with AsyncExitStack() as middleware_astack:
                scope["fastapi_middleware_astack"] = middleware_astack
                await handler.handle(scope, _receive, self._send)
                return self._result
        else:
            raise ServiceNotFoundError(
                f"{uri} cannot be found. Make sure the URL is correct and the correct arguments are provided."
            )

    def _get_route_method(self, route_methods: List[str]) -> Optional[str]:
        """
        Return the method to use to perform a request, from the given candidate route methods.

        Args:
            route_method (List[str]): List of methods supported by the candidate route.

        Returns:
            Optional[str]: The method to use to perform a request to the route supporting the given methods.

        """
        methods = ["POST", "GET", "UPDATE", "DELETE", "PATCH"]
        for method in methods:
            if method in route_methods:
                return method

    async def _send(self, data: Message) -> None:
        if data["type"] == "http.response.body":
            try:
                self._result = json.loads(data["body"])
            except Exception:
                self._result = data["body"]
