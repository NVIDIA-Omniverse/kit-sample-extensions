# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Extension that provides viewport reticle and composition guidelines for camera visualization."""

import omni.ext
from omni.kit.viewport.registry import RegisterViewportLayer

from .views import ReticleScene


class SampleViewportReticleExtension(omni.ext.IExt):
    """Extension that adds a reticle overlay to the viewport for camera composition guidelines.

    This extension provides visual guides for camera composition including:
    - Rule of thirds grid
    - Quad composition grid
    - Crosshair
    - Action safe area
    - Title safe area
    - Custom safe area
    - Letterboxing

    Uses RegisterViewportLayer to automatically create reticle overlays for all viewports.
    Each viewport gets its own independent reticle with its own settings.
    """

    def on_startup(self, ext_id):
        """Initialize the extension and register the reticle layer.

        Args:
            ext_id: The extension ID provided by the extension system.
        """
        # Use RegisterViewportLayer to automatically create reticle overlays for all viewports
        # When the callback is invoked, a ui.Frame is already in scope for adding UI elements
        # This allows mixing omni.ui and omni.ui.scene elements
        self._vp_layer = RegisterViewportLayer(ReticleScene, ext_id)

    def on_shutdown(self):
        """Clean up resources when the extension is disabled."""
        # Registry handles cleanup automatically when we release the reference
        self._vp_layer = None
