# Copyright (c) 2021-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["ViewportFramerateMenuBarExtension"]

import omni.ext


class ViewportFramerateMenuBarExtension(omni.ext.IExt):
    """The entry point for the frame rate item in the viewport menu bar"""

    def __init__(self):
        """Initializes the ViewportFramerateMenuBarExtension instance."""
        super().__init__()
        self.__registered_items = []

    def on_startup(self, ext_id, *args, **kwargs):
        """Handles startup procedures for the extension and registers its menu container with Omni UI.

        Args:
            ext_id (Any): Unique identifier for the extension.
            args (tuple): Additional positional arguments for startup.
        """
        ext_name = omni.ext.get_extension_name(ext_id)

        from .menu_container import MenuContainer

        self.__registered_items.append(MenuContainer(ext_name))

    def on_shutdown(self):
        """Handles shutdown procedures by destroying all registered menu containers."""
        if self.__registered_items:
            for item in self.__registered_items:
                item.destroy()
            self.__registered_items = None
