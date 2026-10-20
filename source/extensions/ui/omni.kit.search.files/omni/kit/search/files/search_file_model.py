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

import carb
import omni.client
from omni.kit.search_core import AbstractSearchItem, AbstractSearchModel


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


class SearchItem(AbstractSearchItem):
    def __init__(self, dir_path, file_entry):
        super().__init__()
        self._dir_path = dir_path
        self._file_entry = file_entry

    @property
    def path(self):
        return f"{self._dir_path}/{self._file_entry.relative_path}"

    @property
    def name(self):
        return str(self._file_entry.relative_path)

    @property
    def date(self):
        # TODO: Grid View needs datatime, but Tree View needs a string. We need to make them the same.
        return self._file_entry.modified_time

    @property
    def size(self):
        # TODO: Grid View needs int, but Tree View needs a string. We need to make them the same.
        return self._file_entry.size

    @property
    def is_folder(self):
        return (self._file_entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN) > 0


class SearchFileModel(AbstractSearchModel):
    def __init__(self, **kwargs):
        super().__init__()
        self._search_text: str = kwargs.get("search_text", None).lower()
        self._current_dir = kwargs.get("current_dir", None)
        # make the recursive search false for nucleus search. NGSearch service can be used for better search on nucleus
        self._search_recursive = False

        # omni.client doesn't understand my-computer
        if self._current_dir.startswith("my-computer://"):
            self._current_dir = self._current_dir[len("my-computer://") :]

        # make the search recursively for local files
        if "omniverse://" not in self._current_dir:
            self._search_recursive = True

        self.__list_task = asyncio.ensure_future(self.__list())
        self.__items = []

    def destroy(self):
        if not self.__list_task.done():
            self.__list_task.cancel()

    @property
    def items(self):
        return self.__items

    async def _get_matches(self, directory: str, recursive: bool):
        result, entries = await omni.client.list_async(directory)
        if result != omni.client.Result.OK:
            return
        else:
            need_update = False
            for entry in entries:
                if self._search_text in entry.relative_path.lower():
                    self.__items.append(SearchItem(directory, entry))
                    need_update = True

            if need_update:
                self._item_changed()

            if recursive:
                for entry in entries:
                    if entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
                        sub_folder = f"{directory}/{entry.relative_path}"
                        await self._get_matches(sub_folder, recursive)

    @handle_exception
    async def __list(self):
        self.__items = []

        # prevent empty searches as they can be quite costly
        if self._search_text and self._search_text.strip() and self._current_dir:
            await self._get_matches(self._current_dir, self._search_recursive)
