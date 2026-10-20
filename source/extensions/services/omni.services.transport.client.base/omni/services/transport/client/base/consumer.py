# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any, Dict, Optional, Tuple
from urllib.parse import ParseResult


class BaseConsumer:
    """Base Transport consumer."""

    def __init__(
        self,
        parsed_uri: ParseResult,
        app: Optional[Any],
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
        self._parsed_uri = parsed_uri
        self._app = app
        self._version = version
        self._persist_connections = persist_connections
        self._raise_for_status = raise_for_status

    def __getattr__(self, name: str):
        raise NotImplementedError

    async def __call__(
        self,
        uri: str,
        *args,
        __method__: Optional[str] = None,
        __headers__: Optional[Dict[str, Any]] = None,
        __raw__: bool = False,
        **kwargs,
    ):
        raise NotImplementedError

    def close(self):
        pass

    async def close_async(self):
        pass


class BaseStandin:
    """Base standing for a Transport consumer."""

    def __init__(self, uri: str, transport: BaseConsumer):
        self._root_uri = uri
        self._transport = transport

    async def __call__(self, *args, __method__: Optional[str] = None, **kwargs):
        """
        Perform a call to the server endpoint using the given method.

        Args:
            __method__ (Optional[str]): Method to use to perform the call.

        Returns:
            Any: The response emitted by the server after processing the given request.

        """
        uri = self._root_uri
        if __method__ is None:
            __method__, uri = self._get_method(uri)
        return await self._transport(uri, *args, __method__=__method__, **kwargs)

    def _get_method(self, uri: str) -> Tuple[Optional[str], str]:
        """
        Return the method to use for a call to be performed against the given URI.

        Args:
            uri (str): URI of the server endpoint targeted by the given candidate call.

        Returns:
            Tuple[Optional[str], str]: A tuple containing the method to use for a call against the given URI.

        """
        potential_method = uri.split("/")[-1]
        method = None
        if potential_method in ["post", "get", "delete", "put"]:
            method = potential_method
            uri = "/".join(uri.split("/")[:-1])
        return method, uri

    def __getattr__(self, name: str):
        self._root_uri = "/".join((self._root_uri, name))
        return self
