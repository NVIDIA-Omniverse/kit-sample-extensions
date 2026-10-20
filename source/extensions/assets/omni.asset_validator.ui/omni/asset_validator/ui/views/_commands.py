# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import asyncio
from functools import partial
from pathlib import Path

from omni.ui import Button, HStack, Length, SimpleBoolModel, UnitType, ZStack

from ..commands import ClearFn, FixFn, ValidateFn
from ..models._model import ApplicationModel
from ._icons import Icons
from ._style import COMMAND_STYLE

ICON_WIDTH: int = 20
CHARACTER_WIDTH: int = 8

__all__ = ["ValidatorCommandsWidget"]


class ValidatorCommandsWidget:
    """
    A widget that contains the buttons for the validator commands.
    """

    ICON_PATH = Path(__file__).parents[3].joinpath("data/icons")

    def __init__(self, model: ApplicationModel | None = None):
        """
        Args:
            model: The model to use for the widget.
        """
        self._model = model or ApplicationModel.get()
        self._task: asyncio.Task | None = None
        self._task_in_progress = SimpleBoolModel(False)
        self._subscription = self._task_in_progress.subscribe_value_changed_fn(self._in_progress_changed)
        with HStack(height=30, spacing=10, style=COMMAND_STYLE):
            with ZStack():
                self._analyze_button = Button(
                    "Analyze",
                    clicked_fn=self._validate,
                    image_url=Icons.ANALYZE,
                    name="action",
                    spacing=4,
                )
                self._cancel_button = Button(
                    "Cancel...",
                    clicked_fn=self._cancel,
                    image_url=Icons.ANALYZE,
                    name="action",
                    spacing=4,
                    visible=False,
                )
            self._fix_button = Button(
                "Fix Selected",
                clicked_fn=FixFn(self._model).apply,
                tooltip="Fix the selected errors based on suggestions.",
                image_url=Icons.FIX,
                name="action",
                spacing=4,
            )
            self._clear_button = Button(
                "Clear Results",
                clicked_fn=ClearFn(self._model).apply,
                tooltip="Clear Results",
            )
        self._add_resize_fn(self._analyze_button)
        self._add_resize_fn(self._cancel_button)
        self._add_resize_fn(self._fix_button)

    def _add_resize_fn(self, button: Button) -> None:
        """Add a function to resize the icon width of the given button."""
        button.set_computed_content_size_changed_fn(partial(self._resize_icon_width, button))

    def _resize_icon_width(self, button: Button) -> None:
        """Resize the icon stack width in the given button"""
        icon_base_width = button.computed_content_width / 2
        yield_width = ((len(button.text) * CHARACTER_WIDTH) - ICON_WIDTH) / 2
        button.image_width = Length(1 - (yield_width / icon_base_width), UnitType.FRACTION)

    def _validate(self) -> None:
        """Start a new validation task."""
        self._task_in_progress.set_value(True)
        self._task = ValidateFn(self._model).apply()
        self._task.add_done_callback(lambda _: self._task_in_progress.set_value(False))

    def _cancel(self) -> None:
        """Cancel the current validation task."""
        in_progress: bool = self._task_in_progress.as_bool
        if in_progress and self._task:
            self._task.cancel()
            self._task_in_progress.set_value(False)

    def _in_progress_changed(self, _) -> None:
        """When in progress, disable all buttons except the cancel button."""
        in_progress: bool = self._task_in_progress.as_bool
        self._analyze_button.visible = not in_progress
        self._cancel_button.visible = in_progress
        self._fix_button.enabled = not in_progress
        self._clear_button.enabled = not in_progress
