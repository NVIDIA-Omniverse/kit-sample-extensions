# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Any, Dict, Optional, Type
from urllib.parse import urlparse

from omni.services.transport.client.base.consumer import BaseConsumer

_transport_registry: Dict[str, Dict[str, Type[BaseConsumer]]] = {"sync": {}, "async": {}}


def register(scheme: str, cls: Type[BaseConsumer], is_async: bool = False):
    """
    Register the given Transport for the given scheme to the registry.

    Args:
        scheme (str): Scheme supported by the given Transport.
        cls (Type[BaseConsumer]): Constructor of the given Transport.
        is_async (bool): Flag indicating whether the given Transport supports asynchronous operations.

    Returns:
        None

    """
    registry = _transport_registry["async"] if is_async else _transport_registry["sync"]
    registry[scheme] = cls


def unregister(scheme: str, is_async: bool = False):
    """
    Unregister the given Transport for the given scheme to the registry.

    Args:
        scheme (str): Scheme supported by the given Transport.
        is_async (bool): Flag indicating whether the given Transport supports asynchronous operations.

    Returns:
        None

    """
    registry = _transport_registry["async"] if is_async else _transport_registry["sync"]
    try:
        registry.pop(scheme)
    except KeyError:
        # The scheme has most likely already been unregistered.
        # This happens when multiple versions of a transport are loaded.
        pass


def get_available_transports(is_async: bool = False) -> Dict[str, Type[BaseConsumer]]:
    """
    Return the list of available transports.

    Args:
        is_async (bool): Flag indicating whether to filter transports for their support of asynchronous operations.

    Returns:
        Dict[str, Type[BaseConsumer]]: The list of available transports.

    """
    return _transport_registry["async"] if is_async else _transport_registry["sync"]


try:
    from .transports import local

    register(scheme="local", cls=local.Transport, is_async=True)
except Exception as exc:
    print("failed to register local async transport")


class TransportNotFoundError(Exception):
    """Raised when a requested Transport has not been registered and cannot be found."""


class Client(object):
    """
    Omniverse Service Client, used as a base class for client-side communication, and extendable to be useable across
    multiple protocols and transports.

    By default, it supports a `local://` version, as well as an HTTP-based version.
    """

    _transport_type = "sync"
    """Type of the transport used by the Client."""

    def __init__(
        self,
        uri: str,
        app: Optional[Any] = None,
        api_version: Optional[Any] = None,
        persist_connections: bool = False,
        raise_for_status: bool = True,
    ):
        """
        Constructor.

        Args:
            uri (str): URI of the server to connect to.
            app (Optional[Any]): Reference to the application running on the server.
            api_version (Optional[Any]): Version of the application running on the server.
            persist_connections (bool): Flag indicating whether to persist connections to the server.
            raise_for_status (bool): Flag indicating whether to raise exceptions for errors.

        Returns:
            None

        """
        super().__init__()

        parsed_uri = urlparse(uri)
        if not parsed_uri.scheme:
            raise ValueError(
                f'The URI provided to the Client ("{uri}") did not contain a scheme fulfilling the pattern "<scheme>://<netloc>/<path>".'
            )

        available_transports = _transport_registry[self._transport_type]
        try:
            self._transport = available_transports[parsed_uri.scheme](
                parsed_uri, app, api_version, persist_connections=persist_connections, raise_for_status=raise_for_status
            )
        except KeyError:
            raise TransportNotFoundError(
                f'No suitable transport for the scheme "{parsed_uri.scheme}" can be found when attempting to fulfill the pattern "<scheme>://<netloc>/<path>". Ensure the right client transport extensions are enabled.'
            )

    def __getattr__(self, name: str):
        return getattr(self._transport, name)

    def stop(self):
        """Stop the Client, and close the underlying transport in a synchronous manner."""
        self._transport.close()


class AsyncClient(Client):
    """Asynchronous Client for Omniverse Services."""

    _transport_type = "async"

    async def stop_async(self):
        """Stop the Client, and close the underlying transport in an asynchronous manner."""
        await self._transport.close_async()
