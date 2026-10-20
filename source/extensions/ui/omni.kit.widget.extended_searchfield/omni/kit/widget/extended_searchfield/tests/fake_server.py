# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime

import omni.kit.app
from omni.kit.search_core import AbstractSearchModel, SearchEngineRegistry
from omni.kit.widget.filebrowser import FileBrowserItem

FileBrowserItemFields = namedtuple("FileBrowserItemFields", "name date size permissions")


class FakeSearchService(AbstractSearchModel):
    search_history = []

    def __init__(self, **kwargs):
        super().__init__()
        self.__items = []
        self._search_text = kwargs.get("search_text", None)
        self._current_dir = kwargs.get("current_dir", None)
        self._search_lifetime = kwargs.get("search_lifetime", None)
        self.__list_task = asyncio.ensure_future(self.__list())
        assert self.__list_task is not None

    def destroy(self):
        super().destroy()
        self._search_lifetime = None
        self.__list_task = None

    @property
    def items(self):
        return self.__items

    async def get_prefixes(self, url: str) -> list:
        return []

    async def __list(self):

        self.__items = []

        await omni.kit.app.get_app().next_update_async()

        results = [
            FileBrowserItem(
                path="/path/to/file",
                fields=FileBrowserItemFields(word[::-1], datetime.now(), 0, 0),
            )
            for word in self._search_text.split(" ")
        ]

        for item in results:
            self.__items.append(item)
            self._item_changed(item)
            await omni.kit.app.get_app().next_update_async()

        if self._search_text:
            FakeSearchService.search_history.append(
                {"search_text": self._search_text, "search_dir": self._current_dir, "search_results": results}
            )

        self._search_lifetime = None


class FakeNGSearchService(FakeSearchService):
    async def get_prefixes(self, url: str) -> list:
        return [
            "created_by",
            "modified_by",
            "name",
            "tag",
            "ext",
            "larger_than",
            "smaller_than",
            "modified_before",
            "modified_after",
            "path",
            "created_before",
            "created_after",
        ]


class FakeDeepSearchService(FakeSearchService):
    @staticmethod
    async def get_prefixes(url: str) -> list:
        return [
            "created_by",
            "modified_by",
            "name",
            "tag",
            "ext",
            "larger_than",
            "smaller_than",
            "modified_before",
            "modified_after",
            "path",
            "description",
            "image",
            "created_before",
            "created_after",
        ]


ENGINES = {
    "FakeSearchService": FakeSearchService,
    "FakeNGSearchService": FakeNGSearchService,
    "FakeDeepSearchService": FakeDeepSearchService,
}


class FakeServer:
    def __init__(self):
        FakeSearchService.search_history = []

    def search_history(self) -> list:
        return FakeSearchService.search_history

    def latest_search(self) -> str:
        if FakeSearchService.search_history:
            return FakeSearchService.search_history[-1]["search_text"]
        return None


@contextmanager
def fake_server(engine_name):

    subscription = SearchEngineRegistry().register_search_model(engine_name, ENGINES[engine_name])
    yield FakeServer()

    # assert here to remove pep8 variable-not-used error
    assert subscription is not None
    subscription = None
