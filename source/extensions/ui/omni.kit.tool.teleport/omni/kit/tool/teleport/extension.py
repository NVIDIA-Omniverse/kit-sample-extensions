# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.events
import omni.ext
from omni.kit.window.preferences import register_page, unregister_page

from .teleport_page import TeleportPage
from .teleport_scene import TeleportScene
from .viewport_overlap import ViewportOverlapsManager

_extension = None


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class TeleportToolExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        global _extension
        _extension = self
        self._page = TeleportPage()
        register_page(self._page)
        self._vp1_manager = ViewportOverlapsManager()
        self._teleport_sub = None
        # Setup for legacy Viewport only
        if not self._vp1_manager.setup("Viewport", vp1_only=True):
            self._vp1_manager.destroy()
            self._vp1_manager = None

        if not self._vp1_manager:
            # Since legacy Viewport failed, register our scene for all new Viewport instances
            try:
                from omni.kit.viewport.registry import RegisterScene

                self._vp2_scene = RegisterScene(TeleportScene, ext_id)
            except ImportError:
                import carb

                carb.log_error("Could not register Paint for any Viewport backend")

    def on_shutdown(self):
        global _extension
        _extension = None
        self._vp2_scene = None
        self._teleport_sub = None

        self._page.destroy()
        unregister_page(self._page)
        self._page = None

        if self._vp1_manager:
            self._vp1_manager.destroy()
            self._vp1_manager = None


def get_instance():
    """Return the global TeleportToolExtension extension instance.

    Returns:
        TeleportToolExtension: The global extension instance or None if not initialized.
    """
    return _extension
