# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["NavigationIconMenuDelegate"]

from typing import Callable, Optional

import carb.settings
import omni.ui as ui

from ..constant import NAVIGATION_IS_LARGE
from .toolbar_icon_menu_delegate import ToolBarIconMenuDelegate


class NavigationIconMenuDelegate(ToolBarIconMenuDelegate):
    """
    The menu delegate that draws in the navigation bar the given icon .
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__label = None

    def build_item(self, item: ui.MenuItem):
        self.icon = self._build_icon()

    def _build_icon(self):
        size = self._icon_width
        return ui.ImageWithProvider(
            style_type_name_override="Menu.Item.Icon",
            name=self._name,
            width=size - 5,
            height=size - 5,
        )
