# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Main extension module for the In-App Guide.

This module implements the extension entry point and manages the lifecycle of the
In-App Guide feature, including initialization, menu registration, and cleanup.
"""

import asyncio
import os
from typing import Optional

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
from omni.kit.menu.utils import MenuHelperExtension

from .model import GuideModel
from .overlay_ui import OverlayWindow
from .step_ui import GuideStepWindow


class InAppGuideExtension(omni.ext.IExt, MenuHelperExtension):
    """Main extension class for the In-App Guide feature.

    This extension provides an interactive guide system that helps users navigate through
    the application's features. It consists of a step-by-step guide UI and an overlay
    that highlights relevant UI elements.
    """

    WINDOW_NAME = "In-App Guide"

    def on_startup(self, ext_id):
        """Initialize the extension when it is activated.

        Args:
            ext_id: The unique identifier for this extension instance.
        """
        self._model: Optional[GuideModel] = None
        self._overlay_ui: Optional[OverlayWindow] = None
        self._step_ui: Optional[GuideStepWindow] = None

        # Add a menuitem for bringing up the guide
        ui.Workspace.set_show_window_fn(InAppGuideExtension.WINDOW_NAME, self._show_step_ui)
        self.menu_startup(InAppGuideExtension.WINDOW_NAME, InAppGuideExtension.WINDOW_NAME, "Help")
        ui.Workspace.show_window(InAppGuideExtension.WINDOW_NAME, False)

    def _get_model(self) -> GuideModel:
        """Get or create the guide model instance.

        Returns:
            GuideModel: The guide model instance.
        """
        if self._model is None:
            app = omni.kit.app.get_app()
            kit_version = app.get_kit_version_short()

            tokens = carb.tokens.get_tokens_interface()
            candidate = tokens.resolve(f"${{omni.sample.in_app_guide}}/data/guide_data_{kit_version}.json")
            if not os.path.exists(candidate):
                carb.log_warn(f"In-App Guide: guide file for Kit {kit_version} not found, falling back to latest.")
                candidate = tokens.resolve("${omni.sample.in_app_guide}/data/guide_data_latest.json")
            self._model = GuideModel(candidate)
            self._model.add_active_changed_function(self._on_active_changed)
        return self._model

    def _on_active_changed(self, active: bool):
        """Handle changes to the guide's active state.

        Args:
            active: Whether the guide should be active or not.
        """
        if active:
            self._overlay_ui = OverlayWindow(name="In-App Guide Overlay", step_ui_window_name="In-App Guide")
            self._step_ui = GuideStepWindow(
                name="In-App Guide", model=self._get_model(), overlay_window=self._overlay_ui
            )
        else:
            if self._model:
                self._model.remove_active_changed_function(self._on_active_changed)
                self._model = None
            asyncio.ensure_future(self._close_ui())
        self.menu_refresh()

    async def _close_ui(self):
        """Close and clean up the guide UI components."""
        app = omni.kit.app.get_app()
        await app.next_update_async()

        if self._overlay_ui:
            self._overlay_ui.destroy()
            self._overlay_ui = None
        if self._step_ui:
            self._step_ui.destroy()
            self._step_ui = None

    def _show_step_ui(self, visible: bool):
        """Show the guide UI by activating the model."""
        if visible:
            self._get_model().active = True
        else:
            self._get_model().active = False

    def on_shutdown(self):
        """Clean up the extension when it is deactivated."""
        if self._model:
            self._model.remove_active_changed_function(self._on_active_changed)
            self._model = None

        if self._overlay_ui is not None:
            self._overlay_ui.destroy()
            self._overlay_ui = None

        if self._step_ui is not None:
            self._step_ui.destroy()
            self._step_ui = None

        # Remove menu items
        self.menu_shutdown()
        ui.Workspace.set_show_window_fn(InAppGuideExtension.WINDOW_NAME, None)
