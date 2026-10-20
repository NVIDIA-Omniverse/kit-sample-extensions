# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MenubarButton"]

from omni.kit.viewport.menubar.core import IconMenuDelegate, ViewportMenuItem


class MenubarButton(ViewportMenuItem):
    """The button for test"""

    def __init__(self, name, settings_order_path, icon_path):
        style = {f"Menu.Item.Icon::{name}": {"image_url": f"{icon_path}"}}

        print(f"Creating button {name}, icon = {icon_path}")
        self._delegate = IconMenuDelegate(name=name, text=False, has_triangle=False)

        super().__init__(name=name, delegate=self._delegate, order_setting_path=settings_order_path, style=style)

    def destroy(self):
        self._delegate = None
        super().destroy()
