# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.kit.markup.core import MarkupCard, MarkupChangeCallbacks, ViewportMarkup
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.playlist.core import SystemPlaylistModel


class AllMarkupPlaylistModel(SystemPlaylistModel):
    def __init__(self):
        super().__init__("All Markups", MarkupCard.PLAYLIST_CARD_TYPE_MARKUP)

        self._markup_instance = get_markup_instance()
        self._ext_callback = MarkupChangeCallbacks(
            on_markup_created=self._on_markup_changed,
            on_markup_deleted=self._on_markup_changed,
            on_markup_changed=self._on_markup_changed,
        )
        self._markup_instance.register_callback(self._ext_callback)

        self.check_update()

    def destroy(self):
        self._markup_instance.deregister_callback(self._ext_callback)
        self._markup_instance = None

    def check_update(self):
        old_index = self.index_model.as_int
        self.clear()

        # Get all markups
        self._children = []
        self._markups = self._markup_instance.get_markups()
        for markup in self._markups:
            if markup.camera_prim is not None:
                card = MarkupCard(MarkupCard.PLAYLIST_CARD_TYPE_MARKUP, markup.camera_prim.GetPath().pathString)
                self.insert_item(card, notify=False)

        # Clamp stale index to the new valid range to avoid IndexError
        # in subscribers, but don't reset unnecessarily (which would
        # fire spurious index-changed events during async updates like
        # thumbnail capture).
        if len(self._children) == 0:
            if old_index != -1:
                self.index_model.set_value(-1)
        elif old_index >= len(self._children):
            self.index_model.set_value(len(self._children) - 1)

    def _on_markup_changed(self, markup: ViewportMarkup) -> None:
        if markup:
            self.check_update()
            self._item_changed(None)
