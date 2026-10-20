# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import os
from typing import Dict, Optional

import carb
import omni.client
import omni.discovery
from omni.search.client import Search as SearchInterface
from omni.search.data import SearchResult


class SearchServiceClient:
    __instance = None

    def __init__(self) -> None:
        if SearchServiceClient.__instance is not None:
            raise Exception("SearchServiceClient is a singleton!")
        else:
            SearchServiceClient.__instance = self

        self._connection: Optional[SearchInterface] = None
        self._current_server: Optional[str] = None
        self._connection_future: Optional[asyncio.Task] = None
        self._auth_tokens: Dict[str, str] = {}
        self._warned: Dict[str, bool] = {}
        # prevent client from connecting in two spots at once (prefixes and search)
        self._transport_lock = asyncio.Lock()

    def __del__(self) -> None:
        self._connection = None
        if self._connection_future and not self._connection_future.done():
            self._connection_future.cancel()
        self._auth_tokens = {}
        self._warned = {}
        self._current_server = None
        SearchServiceClient.__instance = None

    async def establish_connection(self, host: str) -> bool:
        try:
            async with omni.discovery.DiscoverySearch(host) as discovery:
                deployment = os.getenv("OMNI_DEPLOYMENT", "external")
                if deployment != "external":
                    carb.log_info(f"Discovering {deployment} deployment of the Search Service")

                # NOTE: In order to be able to work with the earlier version of Nucleus Search
                # it is required to adjust capability setting that is requested to be present
                # on the server side
                #
                # Below we require the following methods and their respective versions to be
                # available on the server side:
                #       * find2 at version 2
                #       * get_prefixes at version 0

                entry: SearchInterface = await discovery.find(
                    SearchInterface,
                    meta={"deployment": deployment},
                    capabilities=dict(find2=2, get_prefixes=0),
                )
                if entry and entry.transport:
                    self._connection = entry
                    # remove the warning label if the discovery was successful
                    self.clear_warned_label(host=host)
                    return True
                else:
                    if not self.warned_host(host=host, mark_warned=False):
                        carb.log_warn(f"Unable to discover the Search Service on {host}.")
                    return False
        except ConnectionError as e:
            if not self.warned_host(host=host, mark_warned=False):
                carb.log_warn(f"Error discovering Search Service on {host}: {str(e)}")
        except asyncio.CancelledError:
            return False

        return False

    async def _get_auth_token(self, path: str) -> None:
        try:
            result: omni.client.Result
            server_info: omni.client.ServerInfo
            result, server_info = await omni.client.get_server_info_async(path)
        except Exception as e:
            raise RuntimeWarning(str(e))
        if result != omni.client.Result.OK:
            raise RuntimeWarning(str(result))
        host = path.replace("omniverse://", "").split("/")[0]
        self._auth_tokens[host] = server_info.auth_token

    async def get_prefixes(self, url: str) -> list:
        broken_url = omni.client.break_url(url)
        if broken_url.scheme != "omniverse":
            carb.log_error("The Search Service only works on omniverse servers.")
            return []
        host = broken_url.host
        if host != self._current_server:
            if await self.establish_connection(host):
                self._current_server = host
            else:
                if not self._warned.get(host, False):
                    carb.log_warn(f"Failed to establish connection to {host}")
                    self._warned[host] = True
                return []

        try:
            entry = self._connection
            if entry and entry.transport:
                async with self._transport_lock:
                    async with SearchInterface(entry.transport) as service:
                        if not service:
                            carb.log_error("Search Service was not found")
                            return []
                        prefixes = await service.get_prefixes()
                        if "prefixes" in prefixes:
                            return prefixes["prefixes"]
                        return []
            else:
                if not self._warned.get(host, False):
                    carb.log_warn("Connection error with Search Service")
                self._connection = None
                self._current_server = None
        except asyncio.CancelledError:
            raise asyncio.CancelledError
        except OSError:
            carb.log_warn("OS Error: Search Service not found")
        return []

    async def async_search(self, query: str, parent: str) -> Optional[SearchResult]:
        """Search called by the search model in content browser 2.0
        Returns a list of results.
        """
        if len(query) == 0 or not parent:
            return None

        # parent should be of the form omniverse://hostname:port/path/to/folder
        broken_url = omni.client.break_url(parent)
        if broken_url.scheme != "omniverse":
            if not self.warned_host(host=broken_url.host):
                carb.log_error("The Search Service only works on omniverse servers.")
            return None

        host = broken_url.host
        path = broken_url.path if broken_url.path else "/"

        if host != self._current_server:
            if await self.establish_connection(host):
                self._current_server = host
            else:
                if not self.warned_host(host=host):
                    carb.log_warn(f"Failed to establish connection to {host}")
                return None
        if host not in self._auth_tokens:
            await self._get_auth_token(parent)

        try:
            auth_token = self._auth_tokens[host]
            entry = self._connection
            if entry and entry.transport:
                async with self._transport_lock:
                    async with SearchInterface(entry.transport) as service:
                        if not service:
                            carb.log_error("Search Service was not found")
                            return None
                        return await service.find2(
                            {"name": query, "parent": path, "tags": [query]},
                            token=auth_token,
                        )
            else:
                carb.log_warn("Connection error with Search Service")
                self._connection = None
                self._current_server = None
        except asyncio.CancelledError:
            raise asyncio.CancelledError
        except OSError:
            carb.log_warn("OS Error: Search Service not found")

        return None

    def warned_host(self, host: str, mark_warned: bool = True) -> bool:
        warned = self._warned.get(host, False)

        if mark_warned:
            self._warned[host] = True

        return warned

    def clear_warned_label(self, host: str) -> None:
        if host in self._warned:
            del self._warned[host]

    @staticmethod
    def get_instance() -> "SearchServiceClient":
        if SearchServiceClient.__instance is None:
            return SearchServiceClient()
        return SearchServiceClient.__instance
