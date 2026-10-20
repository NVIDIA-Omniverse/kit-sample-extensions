# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, List

from omni import ui
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem
from omni.kit.markup.core import MarkupChangeCallbacks, ViewportMarkup
from omni.kit.markup.core import get_instance as get_markup_instance


class MarkupItem(DetailItem):
    """
    Represent a detail item for a markup in a stage.
    Args:
        markup (ViewportMarkup): Waypoint object.
    """

    def __init__(self, markup: ViewportMarkup):
        thumbnail_data = markup.thumbnail_data
        if thumbnail_data:
            self.thumbnail_provider = ui.ByteImageProvider()
            byte_data, width, height = thumbnail_data
            self.thumbnail_provider.set_bytes_data(bytearray(byte_data), [width, height])
        else:
            self.thumbnail_provider = None

        super().__init__(markup.name, markup.path, None)

    @property
    def markup(self) -> "ViewportMarkup|None":
        inst = get_markup_instance()
        if inst:
            return inst.get_markup(self.name)


class MarkupModel(AbstractBrowserModel):
    """
    Represent markups in opened stage.

    Args:
        on_markup_changed_fn: Callback when markup created/deleted/changed.
    """

    def __init__(self, on_markup_changed_fn: "Callable[..., None]|None" = None):
        self._on_markup_changed_fn = on_markup_changed_fn
        self._markup_instance = get_markup_instance()
        self._collection_item = CollectionItem("Stage", "stage")

        self._markup_callback = MarkupChangeCallbacks(
            self.on_markup_changed, self.on_markup_changed, self.on_markup_changed, self.on_markup_changed
        )
        if self._markup_instance:
            self._markup_instance.register_callback(self._markup_callback)
        super().__init__()

    def destroy(self) -> None:  # pragma: no cover
        if self._markup_instance:
            self._markup_instance.deregister_callback(self._markup_callback)
            self._markup_instance = None

    def execute(self, item: MarkupItem) -> None:
        """
        Recall a markup
        """
        if self._markup_instance:
            self._markup_instance.recall_markup(self._markup_instance.get_markup(item.name))

    def get_collection_items(self) -> List[CollectionItem]:
        return [self._collection_item]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        count = 0
        if self._markup_instance:
            _markups = self._markup_instance.get_markups()
            count = len(_markups)
        return [CategoryItem("Stage", count)]

    def get_detail_items(self, item: CategoryItem) -> List[MarkupItem]:
        detail_items = []
        if self._markup_instance:
            _markups = self._markup_instance.get_markups()
            if _markups:
                for markup in _markups:
                    detail_items.append(MarkupItem(markup))
                detail_items.sort(key=lambda item: item.name)

        return detail_items

    def on_markup_changed(self, *_) -> None:
        self._item_changed(self._collection_item)
        if self._on_markup_changed_fn is not None:
            self._on_markup_changed_fn()
