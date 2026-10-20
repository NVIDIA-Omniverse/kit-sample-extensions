# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import List

import carb
import omni.client


class EngineSelection:
    """This class separates the search engine access from the search field. Inherit from this class
    to control the available/default search engines.
    """

    def __init__(self, engines: List[str] = []):
        self._current_engine: str = ""
        self._engines = engines

    @property
    def current_engine(self) -> str:
        if self.engines:
            if not self._current_engine or self._current_engine not in self.engines:
                self._current_engine = self._engines[0]
        return self._current_engine

    @current_engine.setter
    def current_engine(self, engine: str) -> None:
        self._current_engine = engine

    @property
    def engines(self) -> List[str]:
        return self._engines

    async def prefixes_for_dir(self, search_dir: str) -> List[str]:
        try:
            from omni.kit.search_core import SearchEngineRegistry
        except ImportError as e:
            return []

        if self._current_engine:
            SearchModel = SearchEngineRegistry().get_search_model(self._current_engine)
            if SearchModel:
                model = SearchModel(search_text="", current_dir=search_dir)
                if hasattr(model, "get_prefixes"):
                    return await model.get_prefixes(search_dir)
        return []


class PersistentEngineSelection(EngineSelection):
    """This class separates the search engine access from the search field. Inherit from this class
    to control the available/default search engines.
    """

    def __init__(self):
        self._current_engine: str = ""
        self._current_server: str = ""
        self._search_dir: str = ""
        # map to store the search engine for current server
        self._engine_cache = {}
        settings = carb.settings.get_settings()
        if settings:
            settings.set_default_string("/persistent/exts/omni.kit.widget.extended_searchfield/engine", "")
            self._current_engine = settings.get("/persistent/exts/omni.kit.widget.extended_searchfield/engine")

    def _extract_server_from_dir(self, dir: str) -> str:
        client_url = omni.client.break_url(dir)
        server_url = omni.client.make_url(scheme=client_url.scheme, host=client_url.host, port=client_url.port)
        return server_url

    def _update_current_engine(self):
        engines = self.engines
        if engines:
            if not self._current_engine or self._current_engine not in engines:
                self._current_engine = engines[0]
                current_server = self._extract_server_from_dir(self._current_server)
                self._engine_cache[current_server] = self._current_engine

    @property
    def current_engine(self) -> str:
        self._update_current_engine()
        return self._current_engine

    @current_engine.setter
    def current_engine(self, engine: str) -> None:
        self._current_engine = engine
        current_server = self._extract_server_from_dir(self._current_server)
        self._engine_cache[current_server] = self._current_engine
        settings = carb.settings.get_settings()
        if settings:
            settings.set("/persistent/exts/omni.kit.widget.extended_searchfield/engine", engine)

    @property
    def search_dir(self) -> str:
        return self._search_dir

    @search_dir.setter
    def search_dir(self, dir: str) -> None:
        # refresh the current engine when change the search dir
        if not dir:
            return
        self._search_dir = dir
        self._current_server = self._extract_server_from_dir(dir)
        self._current_engine = self._engine_cache.get(self._current_server, "")
        if not self._current_engine:
            self._update_current_engine()

    @property
    def engines(self) -> List[str]:
        try:
            from omni.kit.search_core import SearchEngineRegistry
        except ImportError as e:
            return []

        # remove any empty strings or None values
        registry = SearchEngineRegistry()
        if hasattr(registry, "get_available_search_names"):
            return list(filter(lambda x: x, SearchEngineRegistry().get_available_search_names(self._current_server)))
        else:
            return list(filter(lambda x: x, SearchEngineRegistry().get_search_names()))
