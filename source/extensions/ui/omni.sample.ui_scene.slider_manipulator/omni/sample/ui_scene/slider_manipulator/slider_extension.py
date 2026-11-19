# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["SliderExtension"]

import omni.ext
from omni.kit.viewport.registry import RegisterScene

from .slider_registry import SliderRegistry


class SliderExtension(omni.ext.IExt):
    """The entry point to the extension"""

    def on_startup(self, ext_id):
        self._slider_registry = RegisterScene(SliderRegistry, "omni.example.ui_scene.slider_manipulator")

    def on_shutdown(self):
        self._slider_registry.destroy()
        self._slider_registry = None
