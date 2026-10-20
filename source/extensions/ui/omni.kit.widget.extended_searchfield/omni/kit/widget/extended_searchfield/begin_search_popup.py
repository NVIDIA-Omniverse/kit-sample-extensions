# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Any, Dict, Optional

import omni.ui as ui

from .style import UI_STYLE


class BeginSearchPopup:
    """This popup just shows a single START SEARCH button. It should be clickable to start a search but should hide
    if clicking elsewhere.
    """

    WINDOW_FLAGS = ui.WINDOW_FLAGS_NO_TITLE_BAR
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_SCROLLBAR
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_BACKGROUND
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_DOCKING
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_CLOSE
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_RESIZE
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_MOVE
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_FOCUS_ON_APPEARING

    def __init__(self, ok_handler: callable):
        super().__init__()

        self._window: Optional[ui.Window] = None
        self._style: Dict[str, Any] = UI_STYLE
        self._should_hide = True
        self._ok_handler = ok_handler
        self._mouse_over = False
        self._build_ui()

    def __del__(self):
        self.destroy()

    @property
    def visible(self) -> bool:
        return self._window.visible

    def show(self, parent: ui.Widget, offset_x: int = 0, offset_y: int = 0):
        """
        Shows this dialog with an offset from the parent widget.

        Args:
            parent (ui.Widget): parent used for positioning
            offset_x (int): X offset. Default 0.
            offset_y (int): Y offset. Default 0.
        """
        width = parent.computed_width
        self._window.position_x = parent.screen_position_x + parent.computed_width - width + offset_x
        self._window.position_y = parent.screen_position_y + offset_y
        self._window.width = width

        self._previous_position_x, self._previous_position_y = self._window.position_x, self._window.position_y
        self._window.visible = True
        self._should_hide = False
        self._mouse_down = False

    def hide(self) -> None:
        self._window.visible = False

    def hide_if_not_hovered(self) -> None:
        """Hides this dialog."""
        if not self._mouse_over:
            self._window.visible = False
            self._should_hide = True

    def _hovered_fn(self, enter: bool) -> None:
        self._mouse_over = enter
        if not enter and self._should_hide:
            self._window.visible = False

    def _mouse_pressed(self, *_) -> None:
        self._mouse_down = True

    def _mouse_released(self, *_) -> None:
        """Only call the ok_handler if the mouse is released while over the button."""
        if self._mouse_down and self._mouse_over:
            if self._ok_handler:
                self._ok_handler()
            self._window.visible = False
        elif self._mouse_down or self._should_hide:
            self._window.visible = False
        self._mouse_down = False

    def _clicked_fn(self) -> None:
        if self._ok_handler:
            self._ok_handler()
        self._window.visible = False

    def _build_ui(self):
        self._window = ui.Window("BeginSearch", width=400, height=0, flags=BeginSearchPopup.WINDOW_FLAGS)
        with self._window.frame:
            with ui.ZStack(height=0, style=UI_STYLE.copy()):
                ui.Rectangle(style_type_name_override="Background")
                with ui.VStack(padding=15):
                    ui.Spacer(height=6)
                    with ui.HStack(padding=0):
                        ui.Spacer(width=6)
                        with ui.HStack():
                            # Create a clickable zone without a button so the label can be centered with an image to
                            # the left.
                            self._button = ui.ZStack()
                            with self._button:
                                ui.Rectangle(style_type_name_override="SearchButton.Background")
                                with ui.VStack():
                                    ui.Spacer(height=3)
                                    with ui.HStack(padding=0):
                                        ui.Image(style_type_name_override="SearchButton.Image")
                                        ui.Label("Start Search", style_type_name_override="SearchButton.Label")
                                        ui.Spacer()
                                    ui.Spacer(height=3)

                            self._button.set_mouse_hovered_fn(self._hovered_fn)
                            self._button.set_mouse_pressed_fn(self._mouse_pressed)
                            self._button.set_mouse_released_fn(self._mouse_released)

                        ui.Spacer(width=6)
                    ui.Spacer(height=6)

        self._window.visible = False

    def destroy(self):
        """Destructor"""
        self._button = None
        self._window = None
        self._ok_handler = None
