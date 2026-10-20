# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Dict, List, Optional

from omni import ui
from omni.kit.browser.folder.core import FileDetailItem

from .browser_property_delegate import BrowserPropertyDelegate
from .property_style import get_style
from .style import PROPERTY_STYLES


class BrowserPropertyView:
    """
    View to show properties of an item from the browser.
    This view represents a container (frame) into which the delegates
    registered with class BrowserPropertyDelegate will be added.
    """

    def __init__(self):
        self.__delegate_frames: Dict[BrowserPropertyDelegate, ui.Frame] = {}
        self._build_ui()

    def destroy(self):
        pass

    def _build_ui(self):
        self._property_container = ui.VStack(style=get_style())
        with self._property_container:
            with ui.ScrollingFrame(
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            ):
                self.__delegate_container = ui.ZStack()

    @property
    def visible(self) -> bool:
        return self._property_container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._property_container.visible = value

    def show_detail_item(self, detail_item: Optional[FileDetailItem]):
        """Various aspects of an item's properties can be shown by different delegates.
        The delegates that are registered with class BrowserPropertyDelegate will be
        asked to show the properties of the item. The delegates that accept the item
        will be shown, and the others will be hidden."""

        delegates = BrowserPropertyDelegate.get_instances()
        for delegate in delegates:
            if delegate.accepted(detail_item):
                # Show delegate
                if delegate not in self.__delegate_frames:
                    with self.__delegate_container:
                        self.__delegate_frames[delegate] = ui.Frame(style=PROPERTY_STYLES)
                self.__delegate_frames[delegate].visible = True
                delegate.show(detail_item, self.__delegate_frames[delegate])
            elif delegate in self.__delegate_frames:
                # Hide delegate
                self.__delegate_frames[delegate].visible = False

    def show_detail_multi_item(self, detail_item_list: List[FileDetailItem]):
        """Properties of a list of items can be shown in various ways.
        The delegates that are registered with class BrowserPropertyDelegate will be
        asked to show the properties of the items. The delegates that accept the items
        will be shown, and the others will be hidden."""

        delegates = BrowserPropertyDelegate.get_instances()
        for delegate in delegates:
            if delegate.accepted_multiple(detail_item_list):
                # Show delegate
                if delegate not in self.__delegate_frames:
                    with self.__delegate_container:
                        self.__delegate_frames[delegate] = ui.Frame(style=PROPERTY_STYLES)
                self.__delegate_frames[delegate].visible = True
                delegate.show_multiple(detail_item_list, self.__delegate_frames[delegate])
            elif delegate in self.__delegate_frames:
                # Hide delegate
                self.__delegate_frames[delegate].visible = False
