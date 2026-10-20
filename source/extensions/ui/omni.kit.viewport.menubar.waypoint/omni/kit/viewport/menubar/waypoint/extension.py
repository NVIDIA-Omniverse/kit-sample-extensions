# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["ViewportWaypointMenuBarExtension"]

import omni.ext

from .waypoint_menu_container import WaypointMenuContainer


class ViewportWaypointMenuBarExtension(omni.ext.IExt):
    """The Entry Point for the Waypoint Settings in Viewport Menu Bar"""

    def on_startup(self, ext_id):
        self._menu = WaypointMenuContainer()

    def on_shutdown(self):  # pragma: no cover
        self._menu.destroy()
        self._menu = None
