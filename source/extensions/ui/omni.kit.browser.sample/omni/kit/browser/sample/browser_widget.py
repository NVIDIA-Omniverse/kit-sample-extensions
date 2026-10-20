# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.kit.browser.core import TreeBrowserWidget
from omni.kit.browser.folder.core import TreeFolderBrowserWidget

DEFAULT_THUMBNAIL_PADDING = 5


class SampleTreeBrowserWidget(TreeBrowserWidget):
    def _on_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        self._detail_kwargs["delegate"].on_thumbnail_size_changed(thumbnail_size)
        thumbnail_padding = self._get_thumbnail_padding(thumbnail_size)
        if thumbnail_padding != self._thumbnail_padding:
            self._thumbnail_padding = thumbnail_padding
            self._detail_view.thumbnail_padding_height = thumbnail_padding
            self._detail_view.thumbnail_padding_width = thumbnail_padding

    def _get_thumbnail_padding(self, thumbnail_size):
        if thumbnail_size > 384:
            return 3 * DEFAULT_THUMBNAIL_PADDING
        elif thumbnail_size > 192:
            return 2 * DEFAULT_THUMBNAIL_PADDING
        else:
            return DEFAULT_THUMBNAIL_PADDING

    def _build_detail_view_internal(self):
        self._thumbnail_padding = self._get_thumbnail_padding(self._detail_kwargs["thumbnail_size"])
        self._detail_kwargs["thumbnail_padding_width"] = self._thumbnail_padding
        self._detail_kwargs["thumbnail_padding_height"] = self._thumbnail_padding

        super()._build_detail_view_internal()


class SampleTreeFolderBrowserWidget(TreeFolderBrowserWidget):
    def _build_browser_widget_internal(self, *args, **kwargs):
        browser_widget = SampleTreeBrowserWidget(*args, **kwargs)
        browser_widget._on_category_selection_changed_fn = self._on_category_selection_changed
        return browser_widget
