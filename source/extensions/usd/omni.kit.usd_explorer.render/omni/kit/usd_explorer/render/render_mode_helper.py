"""
Module for handling render mode settings in USD Explorer.

This module provides functionality to manage render mode settings, especially when stage events occur.
"""

import asyncio
from typing import Any, Optional

import carb
import carb.settings
import omni.kit.app
import omni.usd
from carb.eventdispatcher import get_eventdispatcher

from .preset import get_render_preset_instance


class RenderModeHelper:
    """
    A helper class for managing render mode settings based on stage events.

    This class subscribes to stage events and updates render mode settings accordingly,
    particularly setting the render mode to draft after a new file is opened.
    """

    def __init__(self) -> None:
        """Initialize the RenderModeHelper with settings and subscriptions."""
        self._settings: carb.settings.ISettings = carb.settings.get_settings()
        self._render_preset: Any = get_render_preset_instance()  # RenderPreset()
        self._current_render_type: str = self._render_preset.get_current_render()

        self._stage_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.render:RenderModeHelper",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage,
        )

    def destroy(self) -> None:
        """Cleanup resources used by the RenderModeHelper."""
        self._stage_sub = None
        self._render_preset = None
        self._current_render_type = None
        self._settings = None

    def _on_stage(self, stage_event: Any) -> None:
        """
        Handle stage events, particularly when a stage is opened.

        Args:
            stage_event: The stage event that triggered this callback.
        """
        # OM-53187 set to draft mode after new file
        if self._render_preset is not None:
            self._current_render_type = self._render_preset.get_current_render()

            asyncio.ensure_future(self.set_render_to_draft())

    async def set_render_to_draft(self, reset: bool = True) -> None:
        """
        Set the render mode to draft.

        Args:
            reset: Whether to reset all render values. Defaults to True.
        """
        # waiting the content window invisible
        app = omni.kit.app.get_app()
        for _ in range(4):
            await app.next_update_async()
        self._render_preset.set(self._current_render_type)
        # OM-53187 force to reset all values
        if reset:
            self._render_preset.reset()
        # this is a workaround to avoid crash caused by reset when first startup USD Explorer
        elif self._current_render_type == "Draft":
            self._settings.set("/rtx/post/dof/overrideEnabled", True)
            self._settings.set("/rtx/post/dof/enabled", False)
        await app.next_update_async()
