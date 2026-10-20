"""
USD Explorer Render Extension module.

This module provides the main extension class for the USD Explorer render extension, which sets up
render settings, presets, and navigation modes.
"""

from typing import Any

import omni.ext

from .fast_navigation import FastNavigation
from .preset import get_render_preset_instance
from .render_mode_helper import RenderModeHelper
from .settings import get_render_settings_instance


class usd_explorerRenderExtension(omni.ext.IExt):
    """
    The main extension class for the USD Explorer render functionality.

    This extension sets up render settings, presets, and navigation modes for the USD Explorer application.
    """

    def on_startup(self, _ext_id: str) -> None:
        """
        Initialize the extension when it is started.

        Args:
            ext_id: The extension identifier.
        """
        # Render setting
        self._render_settings: Any = get_render_settings_instance()
        self._render_settings.set_ui_style("NvidiaDark")

        self._render_preset: Any = get_render_preset_instance()
        self._fast_navigation: FastNavigation = FastNavigation()

        # Handles render mode settings on stage events
        self._render_mode_helper: RenderModeHelper = RenderModeHelper()

    def on_shutdown(self) -> None:
        """Clean up resources when the extension is shut down."""
        self._render_settings.destroy()
        self._render_settings = None

        self._fast_navigation.destroy()
        self._fast_navigation = None

        self._render_mode_helper.destroy()
        self._render_mode_helper = None

        self._render_preset.destroy()
        self._render_preset = None
