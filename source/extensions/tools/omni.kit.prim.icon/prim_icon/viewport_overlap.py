# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui import scene as sc

from .scene import IconScene

PRIMICON_VIEWPORT_FRAME = "omni.kit.prim.icon.overlay.VP1"


class ViewportOverlapsManager:
    def __init__(self):
        self._scene_view = None
        self._viewport_window = None

    def setup(self, title: str, vp1_only: bool):
        self._viewport_window = get_active_viewport_window(window_name=title)
        if not self._viewport_window:
            return False

        viewport_api = self._viewport_window.viewport_api
        is_legacy_viewport = hasattr(viewport_api, "legacy_window")
        if vp1_only and (not is_legacy_viewport):
            return False

        self.__build_window(self._viewport_window, viewport_api)
        return True

    def destroy(self):
        # Remove any SceneView we've told the Viepwort to update
        if self._viewport_window and self._scene_view:
            viewport_api = self._viewport_window.viewport_api
            viewport_api.remove_scene_view(self._scene_view)

        if self._scene_view:
            self._scene_view.destroy()
            self._scene_view = None

        self._viewport_window = None

    def __build_window(self, viewport_window, viewport_api):
        with viewport_window.get_frame(PRIMICON_VIEWPORT_FRAME):
            self._scene_view = sc.SceneView()
            with self._scene_view.scene:
                IconScene({"viewport_api": viewport_api})

            # Tell the Viepwort to update our SceneView
            viewport_api.add_scene_view(self._scene_view)
