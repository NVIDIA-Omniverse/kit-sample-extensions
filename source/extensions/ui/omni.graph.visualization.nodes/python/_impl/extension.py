# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb
import omni.ext
from omni.kit.viewport.utility import get_active_viewport_window

from .viewport_manager import ViewportManager
from .viewport_scene import ViewportScene

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.


# It should not be removed, even though its startup / shutdown are currently just passthroughs.
class PublicExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self._viewport_manager = None
        self._viewport_scene = None

    def on_startup(self, ext_id):
        self._viewport_manager = ViewportManager()
        self._viewport_manager.startup()

        # Get the active Viewport (which at startup is the default Viewport)
        viewport_window = get_active_viewport_window()

        # Issue an error if there is no Viewport
        if not viewport_window:
            carb.log_warn(f"No Viewport Window to add {ext_id} scene to")
            return

        # Build out the scene
        self._viewport_scene = ViewportScene(viewport_window, ext_id)

    def on_shutdown(self):
        if self._viewport_manager:
            self._viewport_manager.shutdown()
            self._viewport_manager = None

        if self._viewport_scene:
            self._viewport_scene.destroy()
            del self._viewport_scene
            self._viewport_scene = None
