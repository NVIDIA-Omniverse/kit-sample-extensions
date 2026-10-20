# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
from datetime import datetime
from typing import List

import carb
from omni import ui
from omni.kit.search_core import AbstractSearchModel, SearchEngineRegistry
from omni.kit.widget.examples import ExamplePage
from omni.kit.widget.extended_searchfield import ExtendedSearchField, PersistentEngineSelection
from omni.kit.widget.filebrowser import FileBrowserItem

FileBrowserItemFields = namedtuple("FileBrowserItemFields", "name date size permissions")


class DummySearchEngine(AbstractSearchModel):
    def __init__(self, **kwargs):
        super().__init__()
        self._search_text = kwargs.get("search_text", None)
        self._current_dir = kwargs.get("current_dir", None)
        self._items = []
        if self._search_text:
            words = [
                FileBrowserItem(
                    path="/path/to/file",
                    fields=FileBrowserItemFields(word, datetime.now(), 0, 0),
                )
                for word in self._search_text.split(" ")
            ]
            for word in words:
                self._items.append(word)
                self._item_changed(word)

    def items(self):
        return self._items

    def destroy(self):
        self._items = None

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
            "description",
            "image",
        ]


class DummyAsyncSearchEngine(DummySearchEngine):
    def __init__(self, **kwargs):
        super().__init__()
        self._search_text = kwargs.get("search_text", None)
        self._current_dir = kwargs.get("current_dir", None)
        self._search_lifetime = kwargs.get("search_lifetime", None)
        self._items = []
        self._task = asyncio.ensure_future(self._do_task())

    async def _do_task(self):
        if self._search_text:
            words = [
                FileBrowserItem(
                    path="/path/to/file",
                    fields=FileBrowserItemFields(word, datetime.now(), 0, 0),
                )
                for word in self._search_text.split(" ")
            ]
            for word in words:
                self._items.append(word)
                self._item_changed(word)
                await asyncio.sleep(0.1)
        self._search_lifetime = None

    def destroy(self):
        self._items = None
        self._search_lifetime = None


class ExtendedSearchFieldPage(ExamplePage):
    def __init__(self):
        super().__init__("ExtendedSearchPage")
        self._subscription = SearchEngineRegistry().register_search_model("Dummy Search", DummySearchEngine)
        self._async_subscription = SearchEngineRegistry().register_search_model(
            "Dummy Async Search", DummyAsyncSearchEngine
        )
        self._fields = []

    def destroy(self):
        for field in self._fields:
            field.destroy()
        self._subscription = None
        self._async_subscription = None
        self._dirty_item_subscription = None
        self._search_model = None

    def build_page(self):
        with ui.VStack(spacing=5):
            with ui.VStack(spacing=5, width=400):
                ui.Label("Width 400:", height=20)
                search_field_small = ExtendedSearchField(
                    on_search_fn=self._on_search, engine_delegate=PersistentEngineSelection
                )
                search_field_small.build_ui()
                self._fields.append(search_field_small)

            ui.Label("Default:", height=20)
            search_field = ExtendedSearchField(on_search_fn=self._on_search, engine_delegate=PersistentEngineSelection)
            search_field.build_ui()
            self._fields.append(search_field)

            ui.Label("Keep popups op top:", height=20)
            search_field_on_top = ExtendedSearchField(
                on_search_fn=self._on_search, auto_close_popups=False, engine_delegate=PersistentEngineSelection
            )
            search_field_on_top.build_ui()
            self._fields.append(search_field_on_top)

            ui.Label("Subscribe input:", height=20)
            search_field_sub_input = ExtendedSearchField(
                on_search_fn=self._on_search, subscribe_edit_changed=True, engine_delegate=PersistentEngineSelection
            )
            search_field_sub_input.build_ui()
            self._fields.append(search_field_sub_input)

            ui.Label("No tokens:", height=20)
            search_field_no_tokens = ExtendedSearchField(
                on_search_fn=self._on_search, show_tokens=False, engine_delegate=PersistentEngineSelection
            )
            search_field_no_tokens.build_ui()
            self._fields.append(search_field_no_tokens)

            ui.Label("Disabled:", height=20)
            search_field_disable = ExtendedSearchField(on_search_fn=self._on_search)
            search_field_disable.build_ui()
            search_field_disable.enabled = False
            self._fields.append(search_field_disable)

            ui.Label("Search words:", height=20)
            self._result_field = ui.StringField()

        for field in self._fields:
            field.search_dir = "omniverse://test.ov.nvidia.com"

        self._result_field.enabled = False

    def _on_search(self, query: List[str], search_dir: str, callback: callable = None):
        carb.log_warn("on search")
        if not query:
            query = []
        self._result_field.model.set_value(" ".join(query))
        if callback:
            callback()
