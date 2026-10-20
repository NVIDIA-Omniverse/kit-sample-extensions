# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import functools
import traceback
from datetime import datetime
from typing import List, Optional

import carb
import omni.client
import omni.kit.ngsearch
from omni.kit.search_core import AbstractSearchModel

from .searchservice_client import SearchServiceClient
from .searchservice_item import SearchServiceItem


def handle_exception(func):
    """
    Decorator to print exception in async functions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


class NGSearchServiceModel(AbstractSearchModel):
    __current_model = None

    def __init__(self, **kwargs) -> None:
        super().__init__()

        self.__items: List[SearchServiceItem] = []
        self._search_text = kwargs.get("search_text", None)
        self._current_dir: Optional[str] = kwargs.get("current_dir", None)
        self._search_lifetime = kwargs.get("search_lifetime", None)

        self._list_task = None
        if not self._current_dir or not self._search_text or self._current_dir == "omniverse://":
            return

        broken_url = omni.client.break_url(self._current_dir)
        if broken_url.scheme != "omniverse":
            return

        if not self._current_dir.endswith("/"):
            self._current_dir += "/"

        if NGSearchServiceModel.__current_model and NGSearchServiceModel.__current_model._list_task:
            if not NGSearchServiceModel.__current_model._list_task.done():
                NGSearchServiceModel.__current_model._list_task.cancel()
        NGSearchServiceModel.__current_model = self

        self._list_task = asyncio.ensure_future(self.__list())

    def destroy(self) -> None:
        # Called to cancel search
        if self._list_task and not self._list_task.done():
            self._list_task.cancel()
        self.__items = []
        if NGSearchServiceModel.__current_model == self:
            NGSearchServiceModel.__current_model = None
        self._search_lifetime = None

    @property
    def items(self) -> List[SearchServiceItem]:
        return self.__items

    async def get_prefixes(self, url: str) -> List[str]:
        try:
            from omni.kit.ngsearch.api import get_prefixes, is_available

            if await is_available(self._current_dir):
                return await get_prefixes(url)
        except Exception as exc_info:
            carb.log_warn(exc_info)
        # Fall back to normal search - no prefixes.
        client = SearchServiceClient.get_instance()
        return await client.get_prefixes(url)

    async def __list(self) -> None:
        """We want to display results as fast as possible, so as soon as the results are received
        from the search client we immediately allow them to be displayed, even before calling stat.
        Then we asynchronously stat them to update their metadata (size, date, is_folder).
        """
        # adding DeepSearch specific import to this function to Optimize startup time
        from omni.kit.ngsearch.api import is_available

        try:
            available = await is_available(self._current_dir)
            # is_available() returns False when cancelled (destroy(), a newer search or app shutdown); don't start
            # the fallback search.
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            if available:
                await self._ngsearch()
            else:
                await self._search()
        finally:
            # Release the lifetime object (signals the search ended) on every exit path, including cancellation.
            self._search_lifetime = None

    @handle_exception
    async def _ngsearch(self) -> None:
        """Performs ngsearch async_search."""
        # adding DeepSearch specific import to this function to Optimize startup time
        from omni.kit.ngsearch.api import async_search
        from omni.ngsearch.data import StatusType

        host = omni.client.break_url(self._current_dir).host
        response = await async_search(self._search_text, self._current_dir)
        if response.status != StatusType.OK:
            carb.log_error(f"NGSearch Error: {response.status}")
            return

        for path in response.paths:
            result_path = "omniverse://" + host + str(path.uri)
            rel_path = omni.client.make_relative_url(self._current_dir, result_path)
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]
            # modified is in ctime format, eg 'Wed Jan 19 01:08:10 2022'
            item = SearchServiceItem(
                self._current_dir,
                rel_path,
                date=datetime.strptime(path.modified, "%c"),
                size=int(path.size) if path.size else 0,
                is_folder=path.type == "folder",
            )
            self.__items.append(item)
            self._item_changed()

    @handle_exception
    async def _search(self) -> None:
        """Fallback search when ngsearch is not available"""
        host = omni.client.break_url(self._current_dir).host

        client = SearchServiceClient.get_instance()
        carb.log_info(client)
        # exit directly is search directory is not set
        if self._current_dir is None:
            return
        # perform search
        response = await client.async_search(self._search_text, self._current_dir)
        if response:
            for path in response.paths:
                result_path = "omniverse://" + host + str(path.uri)
                rel_path = omni.client.make_relative_url(self._current_dir, result_path)
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                # modified is in ctime format, eg 'Wed Jan 19 01:08:10 2022'
                item = SearchServiceItem(
                    self._current_dir,
                    rel_path,
                    date=datetime.strptime(path.modified, "%c"),
                    size=int(path.size) if path.size else 0,
                    is_folder=path.type == "folder",
                )
                self.__items.append(item)
            self._item_changed()
