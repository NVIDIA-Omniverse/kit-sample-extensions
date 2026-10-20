# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import List, Optional

import omni.kit.app
from omni.kit.browser.core import BrowserSearchBar
from omni.kit.browser.folder.core import FolderCategoryItem
from omni.kit.widget.searchfield import SearchField

from .browser_with_property_widget import BrowserWithPropertyWidget
from .options_menu import SimReadyFolderOptionsMenu


class SimReadyBrowserWidget(BrowserWithPropertyWidget):
    def __init__(self, *args, **kwargs):
        self.__keep_search_words = False
        kwargs["options_menu"] = kwargs.pop("options_menu", SimReadyFolderOptionsMenu())
        super().__init__(*args, multiple_drag=True, **kwargs)

    @property
    def search_field(self) -> SearchField:
        return self._search_bar._search_field

    @property
    def category_all(self) -> FolderCategoryItem:
        return self._browser_model.get_item_children(self._browser_model._root_collection_item)[0]

    def _build_search_bar(self):
        # Hide gear button in search bar
        self._search_bar = BrowserSearchBar(options_menu=self._options_menu, style=self._extra_ui_style)

    def _build_browser_widget(self):
        super()._build_browser_widget()

        # Here hack the filter function to remove category labels before filter
        self._browser_widget.filter_details = self._filter_details

    def _on_category_selection_changed(self, category_item: FolderCategoryItem) -> None:
        # Set search words with labels from selected category
        if category_item is None:
            return

        if self.__keep_search_words:
            # Here selected category is changed along with search word
            self.__keep_search_words = False

            async def __delay_refresh_details_async():
                await omni.kit.app.get_app().next_update_async()
                self.__refresh_detail_view(self.search_field.search_words)

            asyncio.ensure_future(__delay_refresh_details_async())
        else:
            # Here user click category treeview and select a category
            self.search_field.search_words = self._get_search_words_from_category(category_item)
            self.search_field.suggestions = self._get_tags_from_category(category_item)

    def _filter_details(self, filter_words: Optional[List[str]]):
        """
        Filter detail items.
        Args:
            filter_words: A string list to filter detail items. None means filtering nothing.
        """

        async def __select_category_all_async() -> None:
            await omni.kit.app.get_app().next_update_async()
            self.__keep_search_words = True
            self.category_selection = [self.category_all]

        if filter_words:
            # Check if all labels of current selected category in search words
            # If yes, keep searching in selected category
            # If no, change selected category to ALL then search
            search_labels = set([w.lower() for w in filter_words])
            selected_category = self.category_selection[0] if self.category_selection else None
            if selected_category and selected_category != self.category_all:
                selected_labels = set(l.lower() for l in self._get_search_words_from_category(selected_category))
                if not selected_labels or not selected_labels.issubset(search_labels):
                    asyncio.ensure_future(__select_category_all_async())
                    return

            for category_item in self.category_selection:
                words = self._get_search_words_from_category(category_item)
                filter_words = [w for w in filter_words if w not in words]
        else:
            # No search words, always select ALL
            selected_category = self.category_selection[0] if self.category_selection else None
            if selected_category != self.category_all:
                asyncio.ensure_future(__select_category_all_async())
                return

        self.__refresh_detail_view(filter_words)

    def __refresh_detail_view(self, filter_words: Optional[List[str]]):

        if self._browser_widget._detail_view is not None:
            detail_view = self._browser_widget._detail_view
            detail_view.filter(filter_words)

            # Refresh suggestion words in search bar from results
            async def __refresh_suggestions_async():
                await omni.kit.app.get_app().next_update_async()
                tags = []
                count = 0
                for item in detail_view._delegates:
                    if detail_view._delegates[item].visible:
                        tags.extend(list(item.asset.tags))
                        count += 1
                tags = list(set(tags))
                tags.sort()
                if True:
                    self.search_field.suggestions = tags
                    # TODO: Workaround for issue in omni.kit.widget.searchfield updated.
                    if self.search_field._suggest_window:
                        self.search_field._suggest_window.suggestions = tags

            asyncio.ensure_future(__refresh_suggestions_async())

    def _get_search_words_from_category(self, category_item: FolderCategoryItem) -> List[str]:
        # Get preset search words from category
        if category_item.name == self._browser_model.SUMMARY_FOLDER_NAME:
            return []
        else:
            # Use folder name (label) as preset search words
            return category_item.folder.name.split("/")

    def _get_tags_from_category(self, category_item: FolderCategoryItem) -> List[str]:
        if category_item.name == self._browser_model.SUMMARY_FOLDER_NAME:
            tags = []
            for item in self._browser_model.get_category_items(self._browser_model._root_collection_item):
                if item.name != self._browser_model.SUMMARY_FOLDER_NAME:
                    tags.extend(list(item.folder.asset_by_tags.keys()))
            tags = list(set(tags))
        else:
            tags = list(category_item.folder.asset_by_tags.keys())
        tags.sort()
        return tags
