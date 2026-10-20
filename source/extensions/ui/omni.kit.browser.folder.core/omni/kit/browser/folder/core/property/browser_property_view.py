# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Dict, List, Optional

from omni import ui

from ..models import FileDetailItem
from .browser_property_delegate import BrowserPropertyDelegate


class BrowserPropertyView:
    """
    View to show properties of an item from the browser.
    This view represents a container (frame) into which the delegates
    registered with class BrowserPropertyDelegate will be added.
    """

    def __init__(self, property_delegates: List[BrowserPropertyDelegate] = [], style: Optional[dict] = None):
        self._property_delegates = property_delegates
        self.__delegate_frames: Dict[BrowserPropertyDelegate, ui.Frame] = {}
        self.__style = style if style else {}
        self._build_ui()

    def destroy(self):
        for delegate in self._property_delegates:
            delegate.destroy()

    def _build_ui(self):
        self._property_container = ui.VStack(style=self.__style)
        with self._property_container:
            with ui.ScrollingFrame(
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                style_type_name_override="PropertyView.Frame",
            ):
                self.__delegate_container = ui.VStack(spacing=8)

    @property
    def visible(self) -> bool:
        return self._property_container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._property_container.visible = value

    def show(self, detail_items: List[FileDetailItem]):
        """Various aspects of an item's properties can be shown by different delegates.
        The delegates that accept the item will be shown, and the others will be hidden."""
        for delegate in self._property_delegates:
            if delegate.accepted(detail_items):
                # Show delegate
                if delegate not in self.__delegate_frames:
                    with self.__delegate_container:
                        self.__delegate_frames[delegate] = ui.Frame()
                else:
                    self.__delegate_frames[delegate].clear()
                    self.__delegate_frames[delegate].visible = True
                with self.__delegate_frames[delegate]:
                    delegate.build_widgets(detail_items)
            elif delegate in self.__delegate_frames:
                # Hide delegate
                self.__delegate_frames[delegate].visible = False
