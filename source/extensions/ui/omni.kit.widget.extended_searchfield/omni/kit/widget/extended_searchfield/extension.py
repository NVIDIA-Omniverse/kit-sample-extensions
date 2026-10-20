# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import List, Optional

import carb
import omni.ext
from omni.kit.widget.search_delegate import SearchResultsModel

from .browser_delegate import ContentBrowserDelegate
from .engine_selection import PersistentEngineSelection
from .extended_search_field import ExtendedSearchField


class ExtendedSearchFieldExtension(omni.ext.IExt):
    def on_startup(self):
        self._field = None
        window = self._get_content_window()
        if window:
            self._replace_searchfield(window)

    def _get_content_window(self):
        try:
            import omni.kit.window.content_browser as content

            return content.get_content_window()
        except ImportError:
            carb.log_warn("Unable to get content window.")
            return None

    def _replace_searchfield(self, window):
        # OM-47519: In order to reliably detect the ENTER or BACKSPACE key in the search field, we need to use the
        # parent window's set_key_pressed_fn. This is because the StringField's set_key_pressed_fn only works when the
        # mouse is over the field.
        try:
            parent_window = window.window._window
        except AttributeError:
            parent_window = None

        self._engine_selection = PersistentEngineSelection()
        self._field = ExtendedSearchField(
            on_search_fn=self.search,
            browser_delegate=ContentBrowserDelegate(),
            engine_delegate=self._engine_selection,
            parent_window=parent_window,
        )
        window.set_search_delegate(self._field)
        self._menu_id = window.add_context_menu(
            "Find Similar",
            "menu_search.svg",
            lambda _, p, f=self._field: f._on_select_image(dialog=None, path=p),
            lambda p, f=self._field: f._has_valid_image(path=p),
        )

    def search(self, search_words: Optional[List[str]], seach_dir: str, callback: callable = None):
        try:
            from omni.kit.search_core import SearchEngineRegistry, SearchLifetimeObject
        except ImportError as e:
            carb.log_error(str(e))
            return

        if search_words is None:
            results_model = None
        else:
            # Search engine selection should be removed from extended search engine
            search_engine = self._engine_selection.current_engine
            SearchModel = SearchEngineRegistry().get_search_model(search_engine)
            if not SearchModel:
                carb.log_warn(f"Search engine '{search_engine}' not found.")
                return
            search_model = SearchModel(
                search_text=" ".join(search_words),
                current_dir=seach_dir,
                search_lifetime=SearchLifetimeObject(callback),
            )
            results_model = SearchResultsModel(search_model)

        window = self._get_content_window()
        if window:
            window.show_model(results_model)

    def on_shutdown(self):
        window = self._get_content_window()
        if window:
            window.set_search_delegate(None)
        if self._field:
            self._field.destroy()
            self._field = None
        self._menu_id = None
