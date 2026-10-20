# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["HttpAsyncConsumer", "HttpsAsyncConsumer"]

import asyncio
import ssl
from typing import Any, Dict, Optional
from urllib.parse import ParseResult, urlunparse

import carb
from omni.services.transport.client.base import consumer as _consumer
from omni.services.transport.client.base import exceptions as _exceptions
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND


class HttpAsyncConsumer(_consumer.BaseConsumer):
    """Asynchronous HTTP Consumer."""

    def __init__(
        self,
        parsed_url: ParseResult,
        app: Optional[Any] = None,
        api_version: Optional[Any] = None,
        spec_url: str = "openapi.json",
        persist_connections: bool = False,
        raise_for_status: bool = True,
    ):
        """
        Constructor.

        Args:
            parsed_url (ParseResult): Parsed URI of the server.
            app (Optional[Any]): Reference to the application running on the server.
            api_version (Optional[Any]): Version of the application running on the server.
            spec_url (str): URL of the OpenAPI specification file.
            persist_connections (bool): Flag indicating whether to persist connections to the server.
            raise_for_status (bool): Flag indicating whether to raise exceptions for errors.

        Returns:
            None

        """
        super().__init__(
            parsed_url, app, api_version, persist_connections=persist_connections, raise_for_status=raise_for_status
        )

        # Local imports for performance.
        import aiohttp
        from aiohttp import helpers

        class _CloseableTCPConnector(aiohttp.TCPConnector):
            """
            A TCP connector that does not need an asyncio eventloop to be running in order to shutdown the connections.
            """

            def close_sync(self):
                self._close()

        self._ssl_context = None
        self._session = None
        if self._persist_connections:
            connector = _CloseableTCPConnector(loop=asyncio.get_running_loop())
            self._session = aiohttp.ClientSession(connector=connector, raise_for_status=self._raise_for_status)

        self._url = urlunparse(parsed_url)

        self._spec_url = spec_url
        self._openapi_spec = None

        self._methods = {
            "get": self._get,
            "post": self._post,
            "put": self._put,
            "delete": self._delete,
            "patch": self._patch,
        }

    async def close_async(self):
        """Close the Consumer, in an asynchronous manner."""
        if self._session:
            await self._session.close()

    def close(self):
        """Close the Consumer, in a synchronous manner."""
        if self._session:
            connector = self._session.connector
            self._session.detach()
            connector.close_sync()

    async def _get_spec(self) -> Dict[str, Any]:
        """
        Return the OpenAPI specification for the given server URI.

        Args:
            None

        Returns:
            Dict[str, Any]: A dictionary representing the OpenAPI specification for the given server URI.

        """
        import aiohttp

        try:
            if self._openapi_spec is None:
                spec_api = "/".join((self._url, self._spec_url))
                async with aiohttp.ClientSession() as session:
                    async with session.get(spec_api) as response:
                        if response.status == HTTP_200_OK:
                            self._openapi_spec = await response.json()
                        else:
                            self._openapi_spec = {}
        except Exception as exc:
            carb.log_warn(f"Unable to get API spec. {exc}")
            self._openapi_spec = {}

        return self._openapi_spec

    def __getattr__(self, name):
        return _consumer.BaseStandin(name, self)

    def _create_full_uri(self, uri: str) -> str:
        """
        Create the full URI of the call based on the nomenclature used by the Client.

        Args:
            uri (str): URI of the server endpoint to call.

        Returns:
            str: The full URI of the call to the server.

        """
        full_uri = "/".join((self._url, uri))
        return full_uri.replace("_", "-")

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
        import aiohttp

        full_uri = self._create_full_uri(uri)

        headers = __headers__ or {}
        method = __method__ or await self._get_method_for_uri(uri, args)
        raw = __raw__

        # Sanitize parameters to ensure that various ways of providing a method for the request are appropriately
        # resolved:
        method = method.lower()
        if method not in self._methods.keys():
            available_transport_methods = list(self._methods.keys())
            raise KeyError(
                f'Method "{method}" not found amongst the supported HTTP Transport methods {available_transport_methods} to reach URI "{full_uri}".'
            )

        try:
            if self._session:
                resp = await self._methods[method](
                    self._session, full_uri, *args, headers=headers, ssl_context=self._ssl_context, raw=raw, **kwargs
                )
            else:
                async with aiohttp.ClientSession(raise_for_status=self._raise_for_status) as session:
                    resp = await self._methods[method](
                        session, full_uri, *args, headers=headers, raw=raw, ssl_context=self._ssl_context, **kwargs
                    )
        except aiohttp.ClientResponseError as exc:
            if self._raise_for_status:
                if exc.code == HTTP_404_NOT_FOUND:
                    url = exc.request_info.url
                    raise _exceptions.ServiceNotFoundError(f'"{url}" not found.') from exc
                raise _exceptions.BaseServiceError(str(exc)) from exc
            else:
                return resp
        except (aiohttp.ClientConnectorError, Exception) as e:
            raise

        return resp

    async def _get(self, session, uri, *args, headers=None, raw=False, ssl_context=None, **kwargs):
        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        async with session.get(uri, ssl_context=ssl_context, headers=headers, params=kwargs) as response:
            return await self._handle_response(response)

    # TODO: generalise these functions
    async def _delete(self, session, uri, *args, headers=None, raw=False, ssl_context=None, **kwargs):
        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        data_dict = {"json": kwargs} if not raw else kwargs
        if ssl_context is not None and not ssl_context in data_dict:
            data_dict["ssl_context"] = ssl_context
        async with session.delete(uri, headers=headers, **data_dict) as response:
            return await self._handle_response(response)

    async def _patch(self, session, uri, *args, headers=None, raw=False, ssl_context=None, **kwargs):
        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        data_dict = {"json": kwargs} if not raw else kwargs
        if ssl_context is not None and not ssl_context in data_dict:
            data_dict["ssl_context"] = ssl_context
        async with session.patch(uri, headers=headers, **data_dict) as response:
            return await self._handle_response(response)

    async def _put(self, session, uri, *args, headers=None, raw=False, ssl_context=None, **kwargs):
        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        data_dict = {"json": kwargs} if not raw else kwargs
        if ssl_context is not None and not ssl_context in data_dict:
            data_dict["ssl_context"] = ssl_context
        async with session.put(uri, headers=headers, **data_dict) as response:
            return await self._handle_response(response)

    async def _post(self, session, uri, *args, headers=None, raw=False, ssl_context=None, **kwargs):
        if args:
            path_args = "/".join([str(arg) for arg in args])
            uri = "/".join((uri, path_args))

        data_dict = {"json": kwargs} if not raw else kwargs
        if ssl_context is not None and not ssl_context in data_dict:
            data_dict["ssl_context"] = ssl_context
        async with session.post(uri, headers=headers, **data_dict) as response:
            return await self._handle_response(response)

    # TODO: Can be re-used across transports.
    async def _get_method_for_uri(self, uri: str, args: Any) -> str:
        """
        Return the method to use in order to query the given URI.

        Args:
            uri (str): Server URI to query.
            args (Any): Arguments to include in the query.

        Returns:
            str: Method to use in order to query the given URI.

        """
        try:
            spec = await self._get_spec()
            paths = spec.get("paths", {})

            candidates = [path for path in paths.keys() if path.startswith(f"/{uri}")]

            if len(candidates) == 1 and len(paths[candidates[0]].keys()) == 1:
                verbs = paths[candidates[0]].keys()
                return list(verbs)[0]
        except Exception as exc:
            carb.log_error(f"Failed to retrieve API spec: {exc}")

        return "post"

    async def _handle_response(self, response):
        """
        Process the body of the response from the server, attempting to parse its body if it is encoded as JSON.

        Args:
            response (aiohttp.Response): Response from the server.

        Returns:
            Union[Dict[Any, Any], Any]: Reponse from the server.

        """
        try:
            if response.content_type == "application/json":
                resp = await response.json()
                if isinstance(resp, dict) and not self._raise_for_status:
                    # Skip if List type
                    resp["__http_status__"] = response.status
                return resp
            elif response.content_type == "application/octet-stream":
                return await response.content.read()
            return await response.text()
        except Exception:
            return await response.text()


class HttpsAsyncConsumer(HttpAsyncConsumer):
    """Asynchronous HTTPS Consumer."""

    def __init__(
        self,
        parsed_url: ParseResult,
        app: Optional[Any] = None,
        api_version: Optional[Any] = None,
        spec_url: str = "openapi.json",
        persist_connections: bool = False,
        raise_for_status: bool = True,
    ):
        """
        Constructor.

        Args:
            parsed_url (ParseResult): Parsed URI of the server.
            app (Optional[Any]): Reference to the application running on the server.
            api_version (Optional[Any]): Version of the application running on the server.
            spec_url (str): URL of the OpenAPI specification file.
            persist_connections (bool): Flag indicating whether to persist connections to the server.
            raise_for_status (bool): Flag indicating whether to raise exceptions for errors.

        Returns:
            None

        """
        super().__init__(
            parsed_url, app, api_version, persist_connections=persist_connections, raise_for_status=raise_for_status
        )

        _settings = carb.settings.get_settings_interface()
        cert_file = _settings.get("exts/omni.services.transport.client.http_async/https/cacert_file")
        pem_file = _settings.get("exts/omni.services.transport.client.http_async/https/ssl_pem")
        key_file = _settings.get("exts/omni.services.transport.client.http_async/https/ssl_key")
        skip_verify = _settings.get("exts/omni.services.transport.client.http_async/https/ssl_skip_verify")

        if not skip_verify:
            if cert_file:
                self._ssl_context = ssl.create_default_context(cafile=cert_file)

            if pem_file and key_file:
                if not self._ssl_context:
                    self._ssl_context = ssl.create_default_context()
                self._ssl_context.load_cert_chain(pem_file, key_file)
        else:
            self._ssl_context = False
